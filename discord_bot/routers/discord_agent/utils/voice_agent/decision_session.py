from __future__ import annotations
from typing import Any, Literal
from httpx import URL
from openai import AsyncOpenAI
from pydantic import BaseModel
from ...config import GATEKEEPER_IDENTITY_PROMPT, GATEKEEPER_TURN_FORMAT, PROVIDER_BASE_URL
from ..llm_session import OpenAIClientBase

__all__ = ["DecisionAnswer", "DecisionSession", "GateBot", "ConversationTurn"]

type GateBot = dict[str, Any]
type ConversationTurn = dict[str, Any]

class DecisionAnswer(BaseModel):
    type: Literal["noul", "choice", "score"]
    noul: float | None = None
    value: str | None = None
    probabilities: dict[str, float] | None = None
    confidence: float | None = None
    score: float | None = None

class DecisionSession(OpenAIClientBase):
    def __init__(self, model_id: str, base_url: str = PROVIDER_BASE_URL) -> None:
        cached = self.require_client(base_url)
        self.model_id = model_id
        self.client: AsyncOpenAI = AsyncOpenAI(
            api_key=cached.api_key,
            base_url=str(URL(base_url).copy_with(path="/")))

    def _to_span_state(self, bot: GateBot, conversation: list[ConversationTurn]) -> dict[str, Any]:
        identity = GATEKEEPER_IDENTITY_PROMPT.format(name=bot["name"], id=bot["id"])
        turns: list[dict[str, str]] = [{"role": "system", "content": identity}]
        for turn in conversation[:-1]:
            role = "assistant" if turn["speaker"] == bot["name"] else "user"
            turns.append({"role": role, "content": GATEKEEPER_TURN_FORMAT.format(**turn)})
        last = conversation[-1]
        return {
            "input": turns,
            "output": {"role": "assistant", "content": GATEKEEPER_TURN_FORMAT.format(**last)},
        }

    async def decide_conversation(self, bot: GateBot, conversation: list[ConversationTurn],
                                  questions: dict[str, dict[str, Any]]) -> dict[str, DecisionAnswer]:
        return await self.decide(self._to_span_state(bot, conversation), questions)

    async def decide(self, state: str | dict[str, Any],
                     questions: dict[str, dict[str, Any]]) -> dict[str, DecisionAnswer]:
        response: dict[str, Any] = await self.client.post("/api/alpha/decisions", cast_to=object, body={
            "model": self.model_id,
            "state": state,
            "questions": questions
        })
        answers: dict[str, Any] = response["answers"]
        return {
            name: DecisionAnswer.model_validate(answer)
            for name, answer in answers.items()
        }