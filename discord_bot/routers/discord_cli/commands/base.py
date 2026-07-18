from __future__ import annotations
import sys
import shlex
from inspect import signature, Parameter
from collections.abc import Callable, Awaitable
from typing import Any, Protocol, ClassVar, Concatenate, get_origin, get_args, Union
from types import ModuleType, UnionType
from functools import partial
from discord import Message, Client, Interaction, app_commands
from ....events import EventBroker
from ....state_types import BaseState

__all__ = ["MessageCommand", "InteractionCommand", "CallbackPostprocessing"]

type ContextParser = Callable[[str, Client, Message], Any]

class MessageCommand[StateType: StateType, **ExtraArgs](Protocol):
    COMMANDS: ClassVar[dict[str, MessageCommand]] = {}

    @classmethod
    def add_descriptions[T, **P](cls, **arg_descriptions: str) -> Callable[[MessageCommand[T, P]], MessageCommand[T, P]]:
        def wrapper(cmd: MessageCommand[T, P]) -> MessageCommand[T, P]:
            cmd._descs.update(arg_descriptions)
            return cmd
        return wrapper

    @classmethod
    def add_parsers[T, **P](cls, **arg_parsers: ContextParser) -> Callable[[MessageCommand[T, P]], MessageCommand[T, P]]:
        def wrapper(cmd: MessageCommand[T, P]) -> MessageCommand[T, P]:
            cmd._parsers.update(arg_parsers)
            return cmd
        return wrapper

    @classmethod
    def with_name(cls, command_name: str, group_id: str | None = None) -> Callable[
                                                                            [Callable[
                                                                                Concatenate[EventBroker, Client, StateType, ExtraArgs], 
                                                                                Awaitable[StateType]]], 
                                                                            MessageCommand[StateType]]:
        return partial(cls, command_name=command_name, group_id=group_id)

    @classmethod
    def from_name(cls, command_name: str) -> MessageCommand | None:
        return cls.COMMANDS.get(command_name)
        
    def __init__(self,
                 func: Callable[Concatenate[EventBroker, Client, Message, StateType, ExtraArgs], Awaitable[StateType]],
                 /, *, 
                 command_name: str,
                 group_id: str | None = None
                ) -> None:
        self._func = func
        self._cid = command_name
        self._gid = group_id or command_name
        self._descs: dict[str, str] = {}
        self._parsers: dict[str, ContextParser] = {}
        self.__class__.COMMANDS[command_name] = self
        self.__doc__ = sys.modules[func.__module__].__doc__
        self.__signature__ = signature(func)

    @property
    def command_name(self) -> str:
        return self._cid
    
    @property
    def group_id(self) -> str:
        return self._gid
    
    def parse_arguments(self, client: Client, message: Message, args_line: str) -> dict[str, Any]:
        tokens = shlex.split(args_line)
        target_params = list(signature(self).parameters.values())[4:]    # skip broker, client, msg and state
        kwds: dict[str, Any] = {}
        NoneType = type(None)
        for i, param in enumerate(target_params):
            if i < len(tokens):
                raw_token = tokens[i]
                if param.name in self._parsers:
                    kwds[param.name] = self._parsers[param.name](raw_token, client, message)
                    continue
                annotation = param.annotation
                origin = get_origin(annotation)
                if origin in (Union, UnionType):
                    possible_types = get_args(annotation)
                else:
                    possible_types = (annotation,)
                if raw_token.lower() in ("none", "null") and NoneType in possible_types:
                    kwds[param.name] = None
                    continue
                parsed = False
                for t in possible_types:
                    if t is NoneType:
                        continue
                    if t == bool:
                        kwds[param.name] = raw_token.lower() in ("true", "1", "yes", "y", "on")
                        parsed = True
                        break
                    elif t in (int, float, str):
                        try:
                            kwds[param.name] = t(raw_token)
                            parsed = True
                            break
                        except ValueError:
                            continue 
                if not parsed:
                    kwds[param.name] = raw_token
            elif param.default != Parameter.empty:
                kwds[param.name] = param.default
            else:
                raise ValueError(f"Missing required argument: `{param.name}`")
        return kwds
    
    @property
    def help(self) -> str:  # TODO: localization ??? 
        target_params = list(signature(self).parameters.values())[4:]
        usage_elements = []
        for param in target_params:
            if param.default == Parameter.empty:
                usage_elements.append(f"<{param.name}>")
            else:
                usage_elements.append(f"[{param.name}]")
        usage_suffix = f" {" ".join(usage_elements)}" if usage_elements else ""
        usage_line = f"Usage: {self._cid}{usage_suffix}"
        lines = [
            usage_line,
            f"\nDescription:\n  {self.__doc__.strip() if self.__doc__ else "No description provided."}\n",
            "Arguments:"
        ]
        if not target_params:
            lines.append("  None")
            return "\n".join(lines)
        for param in target_params:
            anno = param.annotation
            type_name = getattr(anno, "__name__", str(anno)) if anno != Parameter.empty else "Any"
            default_str = f" (default: {param.default!r})" if param.default != Parameter.empty else ""
            desc = self._descs.get(param.name, "No description provided.")
            lines.append(f"  {param.name} [{type_name}]{default_str}\n    └─ {desc}")
        return "\n".join(lines)
    
    def __getattr__(self, name: str) -> Any:
        # little hack
        return getattr(self._func, name)
    
    async def __call__(self, broker: EventBroker, client: Client, message: Message, state: StateType, *args: ExtraArgs.args, **kwds: ExtraArgs.kwds) -> StateType:
        async with message.channel.typing():
            return await self._func(broker, client, message, state, *args, **kwds)

class InteractionCommand[StateType: BaseState, **ExtraArgs](Protocol):
    COMMANDS: ClassVar[dict[str, InteractionCommand]] = {}
    _INTERACTIONS_LIST: ClassVar[list[ModuleType, str, str]] = []

    @classmethod
    def with_name(cls, command_name: str, group_id: str | None = None) -> Callable[
                                                                            [Callable[
                                                                                Concatenate[EventBroker, Client, StateType, ExtraArgs], 
                                                                                Awaitable[StateType]]], 
                                                                            InteractionCommand[StateType]]:
        return partial(cls, command_name=command_name, group_id=group_id)  

    @classmethod
    def from_name(cls, command_name: str) -> InteractionCommand | None:
        return cls.COMMANDS.get(command_name)
    
    @classmethod
    async def register_all(cls, client: Client) -> None:
        tree = app_commands.CommandTree(client)
        for mod_name, name, com_name in cls._INTERACTIONS_LIST:
            module = sys.modules[mod_name]
            command = getattr(module, name)
            tree.command(name=com_name, description=cls.from_name(com_name).__doc__)(command)
        await tree.sync()
        
    def __init__(self,
                 func: Callable[Concatenate[EventBroker, Interaction, StateType, ExtraArgs], Awaitable[StateType]],
                 /, *, 
                 command_name: str,
                 group_id: str | None = None
                ) -> None:
        self._func = func
        self._cid = command_name
        self._gid = group_id or command_name
        self.__class__.COMMANDS[command_name] = self
        self.__class__._INTERACTIONS_LIST.append((self._func.__module__, self._func.__name__, command_name))
        self.__doc__ = sys.modules[func.__module__].__doc__
        original_sig = signature(func)
        cleared_params = [p for i, p in enumerate(original_sig.parameters.values()) if i not in [0, 2]]  # neither broker nor state
        self.__signature__ = original_sig.replace(parameters=cleared_params)
    
    @property
    def command_name(self) -> str:
        return self._cid
    
    @property
    def group_id(self) -> str:
        return self._gid
    
    def __getattr__(self, name: str) -> Any:
        # little hack to make object compatible with discord.py
        return getattr(self._func, name)
    
    async def __call__(self, interaction: Interaction, *args: ExtraArgs.args, **kwds: ExtraArgs.kwds) -> None:
        await interaction.response.defer(thinking=True)
    
    async def evaluate(self, broker: EventBroker, interaction: Interaction, state: StateType, *args: ExtraArgs.args, **kwds: ExtraArgs.kwds) -> StateType:
        return await self._func(broker, interaction, state, *args, **kwds)
    
class CallbackPostprocessing[StateType, Payload](Protocol):
    CALLBACKS: ClassVar[dict[str, CallbackPostprocessing]] = {}

    @classmethod
    def with_name(cls, callback_name: str, group_id: str) -> Callable[[Callable[[StateType, Payload], StateType]], CallbackPostprocessing[StateType, Payload]]:
        return partial(cls, callback_name=callback_name, group_id=group_id)  
    
    @classmethod
    def from_name(cls, callback_name: str) -> CallbackPostprocessing | None:
        return cls.CALLBACKS.get(callback_name)

    def __init__(self,
                 func: Callable[[StateType, Payload], Awaitable[StateType]],
                 /, *, 
                 callback_name: str,
                 group_id: str
                ) -> None:
        self._func = func
        self._cid = callback_name
        self._gid = group_id
        self.__class__.CALLBACKS[callback_name] = self

    @property
    def callback_name(self) -> str:
        return self._cid
    
    @property
    def group_id(self) -> str:
        return self._gid
    
    async def __call__(self, state: StateType, payload: Payload) -> StateType:
        return await self._func(state, payload)