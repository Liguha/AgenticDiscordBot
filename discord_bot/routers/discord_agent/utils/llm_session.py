from __future__ import annotations
import json
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar
from pydantic import BaseModel
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ParsedChatCompletion
from ..tools import Toolset
from .context_manager import ContextManager
from ..config import PROVIDER_BASE_URL

__all__ = ["OpenAIClientBase", "LLMSession"]

class OpenAIClientBase:
    """Owns the base-url -> client cache shared by every API session.

    `set_api_key` must be called once per base_url before any session is built.
    """

    OPENAI_CLIENTS: ClassVar[dict[str, AsyncOpenAI]] = {}

    @classmethod
    def set_api_key(cls, api_key: str, base_url: str) -> None:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        cls.OPENAI_CLIENTS[base_url] = client

    @classmethod
    def get_client(cls, base_url: str) -> AsyncOpenAI | None:
        return cls.OPENAI_CLIENTS.get(base_url)

    @classmethod
    def require_client(cls, base_url: str) -> AsyncOpenAI:
        client = cls.get_client(base_url)
        if client is None:
            raise ValueError(f"API key for `{base_url}` isn't defined. Use `{cls.__name__}.set_api_key`.")
        return client

class LLMSession[Scheme: BaseModel](OpenAIClientBase):
    def __init__(self,
                 context: ContextManager,
                 toolset: Toolset,
                 model_id: str,
                 base_url: str = PROVIDER_BASE_URL,
                 system_prompt: str | None = None,
                 resposne_scheme: type[Scheme] | None = None,
                 provider_routing: dict[str, Any] | None = None
                ) -> None:
        self.client: AsyncOpenAI = self.require_client(base_url)
        self.context = context
        self.toolset = toolset
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.resposne_scheme: type[Scheme] | None = resposne_scheme
        self.provider_routing: dict[str, Any] | None = provider_routing

    async def send_message(self, user: str, user_id: int, message: str) -> str | Scheme:
        formatted_message = f"[{user} (id: {user_id})]: {message}"
        self.context.add_message("user", formatted_message)
        api_messages: list[dict[str, str]] = []
        if self.system_prompt:
            api_messages.append({"role": "system", "content": self.system_prompt})
        api_messages.extend(self.context.to_openai_messages())
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": api_messages,
            "reasoning_effort": "minimal"
        }
        kwargs["tools"] = self.toolset.description
        if self.provider_routing is not None:
            kwargs["extra_body"] = {"provider": self.provider_routing}
        api_call: Callable[..., Awaitable[ChatCompletion | ParsedChatCompletion[Scheme]]]
        if self.resposne_scheme:
            kwargs["response_format"] = self.resposne_scheme
            api_call = self.client.beta.chat.completions.parse
        else:
            api_call = self.client.chat.completions.create
        while True:
            response: ChatCompletion | ParsedChatCompletion[Scheme] = await api_call(**kwargs)
            response_message = response.choices[0].message
            if response_message.tool_calls:
                api_messages.append(response_message.model_dump(exclude_none=True))
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args: dict[str, Any] = json.loads(tool_call.function.arguments) # validation ???
                    tool_output: dict[str, Any] = await self.toolset.llm_call(tool_name, **tool_args)
                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps(tool_output)
                    })
                kwargs["messages"] = api_messages
            else:
                final_text: str = response_message.content or ""
                self.context.add_message("assistant", final_text)
                if self.resposne_scheme:
                    final_obj: Scheme | None = getattr(response_message, "parsed", None)
                    if final_obj is None and final_text:
                        final_obj = self.resposne_scheme.model_validate_json(final_text)
                    return final_obj
                return final_text