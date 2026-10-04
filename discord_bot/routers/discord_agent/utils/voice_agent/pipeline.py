from __future__ import annotations
from asyncio import Condition, TimeoutError, get_running_loop, wait_for
from dataclasses import dataclass
from multiprocessing import Queue
from pathlib import Path

from typing import Any

from pydantic import BaseModel
from ...config import GATEKEEPER_QUESTIONS
from ..llm_session import LLMSession
from .decision_session import ConversationTurn, DecisionAnswer, DecisionSession, GateBot
from .speech_recognizer import SpeechRecognizer
from .speech_synthesizer import SpeechSynthesizer
from .....utils.pipeline import PIPELINE_STOP, Pipeline, PipelineBlock

__all__ = ["VoiceMessage", "LockStarted", "LockEnded", "ConversationWindow",
           "GatekeeperConfig", "build_voice_pipeline"]

@dataclass(frozen=True)
class VoiceMessage:
    speaker: str
    user_id: int | None
    text: str

@dataclass(frozen=True)
class LockStarted:
    pass

@dataclass(frozen=True)
class LockEnded:
    pass

LOCK_STARTED = LockStarted()
LOCK_ENDED = LockEnded()

@dataclass(frozen=True)
class PhraseDenied:
    message: VoiceMessage

type VoicePhrase = tuple[str, int | None, bytes]
type GatedItem = VoiceMessage | LockStarted | LockEnded
type GateOutput = VoiceMessage | list[VoiceMessage] | PhraseDenied

class ConversationWindow:
    def __init__(self, bot_name: str, bot_id: int) -> None:
        self.bot_name = bot_name
        self.bot_id = bot_id
        self._anchor: list[VoiceMessage] = []
        self._prefix: list[VoiceMessage] = []
        self._playback_locked = False
        self.agent_busy = False
        self._lock_changed = Condition()

    @property
    def locked(self) -> bool:
        return self._playback_locked or self.agent_busy

    async def wait_lock(self, locked: bool, timeout: float = 5.0) -> None:
        """Waits until the gate stage has processed the pending lock markers."""
        async with self._lock_changed:
            try:
                await wait_for(self._lock_changed.wait_for(lambda: self.locked == locked), timeout)
            except TimeoutError:
                raise TimeoutError(f"gate did not reach locked={locked} within {timeout}s") from None

    async def start_lock(self) -> None:
        async with self._lock_changed:
            self._playback_locked = True
            self._lock_changed.notify_all()

    async def end_lock(self) -> None:
        async with self._lock_changed:
            self._playback_locked = False
            self._lock_changed.notify_all()

    async def set_agent_busy(self, busy: bool) -> None:
        async with self._lock_changed:
            self.agent_busy = busy
            self._lock_changed.notify_all()

    def accept(self, message: VoiceMessage) -> None:
        self._prefix.append(message)

    def flush(self) -> list[VoiceMessage] | None:
        if self.locked or not self._prefix:
            return None
        record = self._prefix.copy()
        self._prefix.clear()
        return record

    def set_anchor(self, record: list[VoiceMessage], reply: str) -> None:
        self._anchor = [*record, VoiceMessage(self.bot_name, self.bot_id, reply)]

    def turns(self) -> list[VoiceMessage]:
        return [*self._anchor, *self._prefix]

class GatekeeperConfig:
    def __init__(self, session: DecisionSession, bot_name: str, threshold: float = 0.50) -> None:
        self.session = session
        self.bot_name = bot_name
        self.threshold = threshold

    def build_state(self, window: ConversationWindow, message: VoiceMessage) -> dict[str, GateBot | list[ConversationTurn]]:
        conversation: list[ConversationTurn] = [
            {"speaker": m.speaker, "id": m.user_id, "text": m.text}
            for m in [*window.turns(), message]
        ]
        return {
            "bot": {"name": window.bot_name, "id": window.bot_id},
            "conversation": conversation,
        }

    def question(self) -> dict[str, dict[str, Any]]:
        return GATEKEEPER_QUESTIONS

def build_voice_pipeline(recognizer: SpeechRecognizer,
                         synthesizer_path: Path,
                         agent: LLMSession[BaseModel],
                         gatekeeper: GatekeeperConfig,
                         window: ConversationWindow,
                         sample_rate: int = 48000,
                         tts_threads: int = 2) -> Pipeline:
    @PipelineBlock.from_map()
    def asr_stage(item: VoicePhrase | LockStarted | LockEnded) -> GatedItem:
        if isinstance(item, (LockStarted, LockEnded)):
            return item
        return VoiceMessage(speaker=item[0], user_id=item[1],
                            text=recognizer.transcribe(item[2], sample_rate))

    @PipelineBlock.from_consumer()
    async def gate_stage(in_q: Queue[GatedItem], out_q: Queue[GateOutput]) -> None:
        loop = get_running_loop()
        while (item := await loop.run_in_executor(None, in_q.get)) != PIPELINE_STOP:
            if isinstance(item, LockStarted):
                if (record := window.flush()) is not None:
                    out_q.put(record)
                await window.start_lock()
            elif isinstance(item, LockEnded):
                await window.end_lock()
            else:
                if (record := window.flush()) is not None:
                    out_q.put(record)
                gate_state: dict[str, GateBot | list[ConversationTurn]] = gatekeeper.build_state(window, item)
                answers = await gatekeeper.session.decide_conversation(
                    gate_state["bot"], gate_state["conversation"], gatekeeper.question())
                answer: DecisionAnswer = answers["is_directed_to_bot"]
                if answer.noul is not None and answer.noul >= gatekeeper.threshold:
                    if window.locked:
                        window.accept(item)
                    else:
                        out_q.put(item)
                else:
                    out_q.put(PhraseDenied(item))
            if not window.locked and (record := window.flush()) is not None:
                out_q.put(record)
        out_q.put(PIPELINE_STOP)

    @PipelineBlock.from_consumer()
    async def agent_stage(in_q: Queue[GateOutput], out_q: Queue[str | PhraseDenied]) -> None:
        loop = get_running_loop()
        while (item := await loop.run_in_executor(None, in_q.get)) != PIPELINE_STOP:
            if isinstance(item, PhraseDenied):
                out_q.put(item)
                continue
            record: list[VoiceMessage] = item if isinstance(item, list) else [item]
            text = " ".join(m.text for m in record)
            await window.set_agent_busy(True)
            try:
                reply = await agent.send_message(record[0].speaker, record[0].user_id, text)
            finally:
                await window.set_agent_busy(False)
            window.set_anchor(record, str(reply))
            out_q.put(str(reply))
        out_q.put(PIPELINE_STOP)

    @PipelineBlock.from_consumer(separate_process=True)
    def tts_stage(in_q: Queue[str | PhraseDenied], out_q: Queue[bytes | PhraseDenied]) -> None:
        synthesizer = SpeechSynthesizer(synthesizer_path, threads=tts_threads)
        while (text := in_q.get()) != PIPELINE_STOP:
            if isinstance(text, PhraseDenied):
                out_q.put(text)
                continue
            out_q.put(synthesizer.synthesize(text))
        out_q.put(PIPELINE_STOP)

    return Pipeline(asr_stage, gate_stage, agent_stage, tts_stage)