from __future__ import annotations
import json
from typing import ClassVar
from pydantic import BaseModel
from openai import AsyncOpenAI
from .tools import Toolset
from .context_manager import ContextManager
from .config import PROVIDER_BASE_URL

__all__ = ["LLMSession"]

class LLMSession[Scheme: BaseModel]:
    OPENAI_CLIENTS: ClassVar[dict[str, AsyncOpenAI]] = {}   # provider->client

    @classmethod
    def set_api_key(cls, api_key: str, base_url: str) -> None:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        cls.OPENAI_CLIENTS[base_url] = client

    @classmethod
    def get_client(cls, base_url: str) -> AsyncOpenAI | None:
        return cls.OPENAI_CLIENTS.get(base_url)

    def __init__(self, 
                 context: ContextManager,
                 toolset: Toolset,
                 model_id: str, 
                 base_url: str = PROVIDER_BASE_URL, 
                 system_prompt: str | None = None, 
                 resposne_scheme: type[Scheme] | None = None
                ) -> None:
        self.client = self.get_client(base_url)
        if self.client is None:
            raise ValueError(f"API key for `{base_url}` isn't defined. Use `{self.__class__.__name__}.set_api_key`.")
        self.context = context
        self.toolset = toolset
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.resposne_scheme: type[Scheme] | None = resposne_scheme

    async def send_message(self, user: str, user_id: int, message: str) -> str | Scheme:
        formatted_message = f"[{user} (id: {user_id})]: {message}"
        self.context.add_message("user", formatted_message)
        api_messages = []
        if self.system_prompt:
            api_messages.append({"role": "system", "content": self.system_prompt})
        api_messages.extend(self.context.to_openai_messages())
        kwargs = {
            "model": self.model_id,
            "messages": api_messages,
        }
        kwargs["tools"] = self.toolset.description
        if self.resposne_scheme:
            kwargs["response_format"] = self.resposne_scheme
            api_call = self.client.beta.chat.completions.parse
        else:
            api_call = self.client.chat.completions.create
        while True:
            response = await api_call(**kwargs)
            response_message = response.choices[0].message
            if response_message.tool_calls:
                api_messages.append(response_message.model_dump(exclude_none=True))
                for tool_call in response_message.tool_calls:
                    print(f"TOOL CALL: {tool_call}")
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments) # validation ???
                    print(f"TOOL ARGS: {tool_args}")
                    tool_output = await self.toolset.llm_call(tool_name, **tool_args)
                    print(f"TOOL OUTPUT: {tool_output}")
                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps(tool_output)
                    })
                kwargs["messages"] = api_messages
            else:
                final_text = response_message.content or ""
                self.context.add_message("assistant", final_text)
                if self.resposne_scheme:
                    final_obj = getattr(response_message, "parsed", None)
                    if final_obj is None and final_text:
                        final_obj = self.resposne_scheme.model_validate_json(final_text)
                    return final_obj
                return final_text