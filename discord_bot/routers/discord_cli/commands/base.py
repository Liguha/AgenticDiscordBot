from __future__ import annotations
import sys
import shlex
from inspect import signature, Parameter
from collections.abc import Callable, Awaitable
from types import ModuleType, UnionType
from functools import partial
from typing import Annotated, Any, ClassVar, Concatenate, Literal, Protocol, Union, get_args, get_origin
from discord import Client, Interaction, Message
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
    def with_name[T, **P](cls, command_name: str, group_id: str | None = None) -> Callable[
                                                                                    [Callable[
                                                                                        Concatenate[EventBroker, Client, Message, T, P], 
                                                                                        Awaitable[StateType]]], 
                                                                                    MessageCommand[T, P]]:
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
    _SLASH_OPTION_TYPES: ClassVar[dict[type, int]] = {str: 3, int: 4, bool: 5, float: 10}

    class _RangeLimits:
        """Metadata marker (min/max) carried inside a :class:`~InteractionCommand.Range` annotation."""

        __slots__ = ("min_value", "max_value")

        def __init__(self, min_value: int | float | None, max_value: int | float | None) -> None:
            self.min_value = min_value
            self.max_value = max_value

    class Range:
        """Numeric range constraint for slash-command option annotations (e.g. ``InteractionCommand.Range[int, 1, 8]``)."""

        __slots__ = ()

        @classmethod
        def __class_getitem__(cls, item: Any) -> Any:
            args = item if isinstance(item, tuple) else (item,)
            base: Any = args[0]
            min_value: int | float | None = args[1] if len(args) > 1 else None
            max_value: int | float | None = args[2] if len(args) > 2 else None
            return Annotated[base, InteractionCommand._RangeLimits(min_value, max_value)]

    class Choice:
        """Named-value pair for slash-command choices and autocomplete suggestions."""

        __slots__ = ("name", "value")

        def __init__(self, *, name: str, value: str | int | float | None = None) -> None:
            self.name = name
            self.value = value if value is not None else name

        def to_dict(self) -> dict[str, str | int | float]:
            return {"name": self.name, "value": self.value}

    @classmethod
    def add_descriptions[T, **P](cls, **arg_descriptions: str) -> Callable[[InteractionCommand[T, P]], InteractionCommand[T, P]]:
        def wrapper(cmd: InteractionCommand[T, P]) -> InteractionCommand[T, P]:
            cmd._descs.update(arg_descriptions)
            return cmd
        return wrapper

    @classmethod
    def add_autocompletes[T, **P](cls, **callbacks: Callable[[Interaction, str], Awaitable[list[Choice]]]) -> Callable[[InteractionCommand[T, P]], InteractionCommand[T, P]]:
        def wrapper(cmd: InteractionCommand[T, P]) -> InteractionCommand[T, P]:
            cmd._autocompletes.update(callbacks)
            return cmd
        return wrapper

    @classmethod
    def with_name[T, **P](cls, command_name: str, group_id: str | None = None) -> Callable[
                                                                                    [Callable[
                                                                                        Concatenate[EventBroker, Interaction, T, P], 
                                                                                        Awaitable[StateType]]], 
                                                                                    InteractionCommand[T, P]]:
        return partial(cls, command_name=command_name, group_id=group_id)  

    @classmethod
    def from_name(cls, command_name: str) -> InteractionCommand | None:
        return cls.COMMANDS.get(command_name)
    
    @classmethod
    async def register_all(cls, client: Client) -> None:
        application_id: int = client.application_id or client.user.id
        payload: list[dict[str, Any]] = [
            cls.from_name(name).command_payload()
            for _, _, name in cls._INTERACTIONS_LIST
        ]
        await client.http.bulk_upsert_global_commands(application_id, payload)
        
    def __init__(self,
                 func: Callable[Concatenate[EventBroker, Interaction, StateType, ExtraArgs], Awaitable[StateType]],
                 /, *, 
                 command_name: str,
                 group_id: str | None = None
                ) -> None:
        self._func = func
        self._cid = command_name
        self._gid = group_id or command_name
        self._descs: dict[str, str] = {}
        self._autocompletes: dict[str, Callable[[Interaction, str], Awaitable[list[InteractionCommand.Choice]]]] = {}
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
        # little hack to make object compatible with the discord library
        return getattr(self._func, name)
    
    async def __call__(self, interaction: Interaction, *args: ExtraArgs.args, **kwds: ExtraArgs.kwds) -> None:
        await interaction.response.defer()
    
    async def evaluate(self, broker: EventBroker, interaction: Interaction, state: StateType, *args: ExtraArgs.args, **kwds: ExtraArgs.kwds) -> StateType:
        return await self._func(broker, interaction, state, *args, **kwds)

    @classmethod
    async def dispatch_autocomplete(cls, interaction: Interaction) -> None:
        command: InteractionCommand | None = cls.from_name((interaction.data or {}).get("name"))
        if command is None:
            return
        await command.evaluate_autocomplete(interaction)

    async def evaluate_autocomplete(self, interaction: Interaction) -> None:
        data: dict[str, Any] = interaction.data or {}
        focused = next((o for o in data.get("options", []) if o.get("focused")), None)
        if focused is None:
            return
        callback = self._autocompletes.get(str(focused.get("name")))
        if callback is None:
            return
        choices: list[InteractionCommand.Choice] = await callback(interaction, str(focused.get("value") or ""))
        await interaction.response.send_autocomplete_result(choices=choices)

    @staticmethod
    def _range_of(annotation: Any) -> InteractionCommand._RangeLimits | None:
        if get_origin(annotation) is not Annotated:
            return None
        for meta in get_args(annotation)[1:]:
            if isinstance(meta, InteractionCommand._RangeLimits):
                return meta
        return None

    @staticmethod
    def _literal_of(annotation: Any) -> list[Any] | None:
        origin = get_origin(annotation)
        return list(get_args(annotation)) if origin is Literal else None

    @staticmethod
    def _unwrapped(annotation: Any) -> Any:
        if get_origin(annotation) in (Union, UnionType):
            args = get_args(annotation)
            return next((a for a in args if a is not type(None)), annotation)
        return annotation

    def command_payload(self) -> dict[str, Any]:
        options: list[dict[str, Any]] = []
        for param in list(signature(self).parameters.values())[1:]:  # skip interaction
            option = self._option_payload(param)
            if option is not None:
                options.append(option)
        payload: dict[str, Any] = {
            "name": self._cid,
            "description": (self.__doc__ or "").strip() or "No description provided.",
        }
        if options:
            payload["options"] = options
        return payload

    def _option_payload(self, param: Parameter) -> dict[str, Any] | None:
        annotation = param.annotation
        if isinstance(annotation, str):
            return None
        limits = self._range_of(annotation)
        if limits is not None:
            annotation = get_args(annotation)[0]
        choice_values = self._literal_of(annotation)
        if choice_values is not None:
            annotation = str
        annotation = self._unwrapped(annotation)
        option_type = self._SLASH_OPTION_TYPES.get(annotation)
        if option_type is None:
            return None
        option: dict[str, Any] = {
            "name": param.name,
            "description": self._descs.get(param.name, ""),
            "type": option_type,
            "required": param.default is Parameter.empty,
        }
        if choice_values is not None:
            option["choices"] = [{"name": str(v), "value": v} for v in choice_values]
        if param.name in self._autocompletes:
            option["autocomplete"] = True
        if limits is not None:
            if limits.min_value is not None:
                option["min_value"] = limits.min_value
            if limits.max_value is not None:
                option["max_value"] = limits.max_value
        return option
    
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