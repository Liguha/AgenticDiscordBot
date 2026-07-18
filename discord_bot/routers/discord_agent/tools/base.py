from __future__ import annotations
import asyncio
import re
from enum import Enum
from uuid import uuid4
from inspect import signature, Parameter
from asyncio import Future
from dataclasses import dataclass
from typing import Any, Awaitable, Concatenate, ClassVar, Literal, Protocol, get_args, get_origin
from functools import partial, cached_property
from collections.abc import Callable
from discord import Client, Guild
from pydantic import BaseModel, Field
from ....events import EventBroker, AgentToolEvent, AgentToolPayload
from ....state_types import BaseState

__all__ = ["ToolResult", "ToolError", "ToolErrorCodes", "Tool", "Toolset"]

PRIMITIVE_TYPE_MAP: dict[Any, dict[str, Any]] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    dict: {"type": "object"},
    list: {"type": "array", "items": {}},
}

def map_type(t: Any) -> dict[str, Any] | None:
    if t in PRIMITIVE_TYPE_MAP:
        return PRIMITIVE_TYPE_MAP[t].copy()
    origin = get_origin(t)
    if origin is not None:
        args = get_args(t)
        if origin is list:
            item_schema = map_type(args[0]) if args else {}
            return {"type": "array", "items": item_schema or {}}
        if origin is dict:
            return {"type": "object"}
        if origin is Literal:
            literal_vals = list(args)
            if all(isinstance(v, str) for v in literal_vals):
                base_t = "string"
            elif all(isinstance(v, bool) for v in literal_vals):
                base_t = "boolean"
            elif all(isinstance(v, int) and not isinstance(v, bool) for v in literal_vals):
                base_t = "integer"
            elif all(isinstance(v, float) for v in literal_vals):
                base_t = "number"
            else:
                base_t = "string"
            return {"type": base_t, "enum": literal_vals}
    if isinstance(t, type):
        if issubclass(t, Enum):
            enum_vals = [e.value for e in t]
            base_t = "string" if all(isinstance(v, str) for v in enum_vals) else "integer"
            return {"type": base_t, "enum": enum_vals}
        if issubclass(t, BaseModel):
            return {"type": "object", "properties": t.model_json_schema().get("properties", {})}
    return None

class ToolResult(BaseModel):
    success: Literal[True] = Field(default=True, frozen=True)

class ToolError(BaseModel):
    success: Literal[False] = Field(default=False, frozen=True)
    error_code: str = Field(description="The class name or identifier of the error encountered.")
    message: str = Field(description="A human/LLM readable description of what went wrong.")

class ToolErrorCodes(Enum):
    TOOL_NOT_FOUND = 0

class Tool[**ExtraArgs, ReturnType: ToolResult | ToolError, StateType: BaseState](Protocol):
    SERVICE_FIELDS: ClassVar[set[str]] = {"broker", "client", "guild", "state"}
    TOOLS: ClassVar[dict[str, Tool]] = {}

    @classmethod
    def with_group(cls, group_id: str) -> Callable[
                                            [Callable[
                                                Concatenate[EventBroker, Client, Guild, StateType, ExtraArgs], 
                                                Awaitable[tuple[ReturnType, StateType]]]], 
                                            Tool[ExtraArgs, ReturnType, StateType]]:
        return partial(cls, group_id=group_id) 
    
    @classmethod
    def from_name(cls, tool_name: str) -> Tool | None:
        return cls.TOOLS.get(tool_name)

    def __init__(self,
                 func: Callable[Concatenate[EventBroker, Client, StateType, ExtraArgs], Awaitable[tuple[ReturnType, StateType]]],
                 /, *, 
                 group_id: str | None = None
                ) -> None:
        self._func = func
        self._gid = group_id or self.tool_name
        self.__class__.TOOLS[self.tool_name] = self

    @property
    def tool_name(self) -> str:
        return self._func.__name__
    
    @property
    def group_id(self) -> str:
        return self._gid

    @cached_property
    def description(self) -> dict[str, Any]:    # Evil docstring parser
        doc = self._func.__doc__
        main_desc_parts: list[str] = []
        param_descs: dict[str, str] = {}
        return_parts: list[str] = []
        if doc:
            lines = [line.strip() for line in doc.splitlines()]
            in_params_section = False
            in_returns_section = False
            for line in lines:
                if not line:
                    continue
                low_line = line.lower().rstrip(":")
                if low_line in ("args", "parameters", "params"):
                    in_params_section = True
                    in_returns_section = False
                    continue
                if low_line in ("returns", "return"):
                    in_params_section = False
                    in_returns_section = True
                    continue
                sphinx_param = re.match(r"^:param\s+([\w_]+):\s*(.*)$", line)
                if sphinx_param:
                    p_name, p_desc = sphinx_param.groups()
                    param_descs[p_name] = p_desc
                    continue
                sphinx_return = re.match(r"^:return:\s*(.*)$", line)
                if sphinx_return:
                    return_parts.append(sphinx_return.group(1))
                    in_params_section = False
                    in_returns_section = True
                    continue
                if in_params_section:
                    param_match = re.match(r"^([\w_]+)(?:\s*\([^)]+\))?\s*:\s*(.*)$", line)
                    if param_match:
                        p_name, p_desc = param_match.groups()
                        param_descs[p_name] = p_desc
                elif in_returns_section:
                    return_parts.append(line)
                else:
                    main_desc_parts.append(line)
        main_desc = " ".join(main_desc_parts)
        return_desc = " ".join(return_parts) if return_parts else None
        if return_desc:
            main_desc = f"{main_desc}\n\nReturns: {return_desc}".strip()
        sig = signature(self._func)
        properties: dict[str, Any] = {}
        required: list[str] = []
        for name, param in sig.parameters.items():
            if name in self.SERVICE_FIELDS:
                continue
            anno = param.annotation
            if anno == Parameter.empty:
                raise ValueError(f"Parameter '{name}' in tool '{self.tool_name}' lacks an explicit type annotation.")
            param_schema = map_type(anno)
            if param_schema is None:
                raise ValueError(
                    f"Non-standard type annotation '{anno}' discovered on parameter '{name}' "
                    f"inside tool '{self.tool_name}'. Only standard primitives, Enums, and Pydantic models are allowed."
                )
            if name in param_descs:
                param_schema["description"] = param_descs[name]
            properties[name] = param_schema
            if param.default == Parameter.empty:
                required.append(name)
        return {
            "type": "function",
            "function": {
                "name": self.tool_name,
                "description": main_desc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def __getattr__(self, name: str) -> Any:
        # little hack to make object compatible with discord.py
        return getattr(self._func, name)
    
    async def __call__(self, 
                       broker: EventBroker, 
                       client: Client, 
                       guild: Guild, 
                       state: StateType, 
                       *args: ExtraArgs.args, 
                       **kwds: ExtraArgs.kwargs
                      ) -> tuple[ReturnType, StateType]:
        return await self._func(broker, client, guild, state, *args, **kwds)
    
@dataclass
class Toolset:
    broker: EventBroker
    client: Client
    guild: Guild
    tools_filter: set[str] | None = None

    def __post_init__(self) -> None:
        if self.tools_filter is None:
            self.tools_filter = set(Tool.TOOLS.keys())
        self._futures: dict[int, Future] = {}

    @cached_property
    def description(self) -> list[dict[str, Any]]:
        return [Tool.from_name(name).description for name in self.tools_filter]

    async def llm_call(self, tool_name: str, *args: Any, **kwds: Any) -> dict[str, Any]:
        tool = Tool.from_name(tool_name)
        if tool_name not in self.tools_filter or tool is None:
            return ToolError(error_code=ToolErrorCodes.TOOL_NOT_FOUND.name, 
                             message=f"Tool `{tool_name}` wasn't found."
                            ).model_dump()
        uid = uuid4().int
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._futures[uid] = future
        try:
            print(f"PUBLISH: {AgentToolEvent(self.guild, AgentToolPayload(uid, tool, args, kwds))}")
            await self.broker.publish(AgentToolEvent(self.guild, AgentToolPayload(uid, tool, args, kwds)))
            result: ToolResult | ToolError = await future
            return result.model_dump()
        finally:
            self._futures.pop(uid, None)
    
    async def router_call[StateType: BaseState](self, state: StateType, payload: AgentToolPayload) -> StateType:
        result, new_state = await payload.tool(self.broker, self.client, self.guild, state, *payload.args, **payload.kwds)
        future = self._futures.get(payload.call_id)
        print("ROUTER CALL")
        if future and not future.done():
            print(f"RESULT: {result}")
            future.set_result(result)
        return new_state
