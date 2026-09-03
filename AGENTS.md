# Agent Guidelines & Repository Rules

This document outlines core principles, coding conventions, and documentation standards for AI coding agents working on this repository.

## The "Decorator Class" Dialect (project-wide, read first)

This project uses a distinctive wrapper idiom for `Action`, `MessageCommand`, `InteractionCommand`, `CallbackPostprocessing`, and agent `Tool`. It is **not** the standard `@app_commands.command` pattern — understand it before editing:

- **A decorated function is immediately turned into a wrapper *instance*, not left as a function.** The `@X.with_name("name")` / `@Tool` / `@Action` decorators call a class constructor over the raw function at import time. So a module-level `message_play` name is already an `X` instance with `_func`, `_cid`, `_gid`, etc. There are no partials in the final state.
- **`@X.add_descriptions(...)` is the "param decorator" and MUST sit directly above `@X.with_name(...)`.** The idiom relies on the `add_*` decorator receiving a live instance. If you reorder them, `add_*` sees a raw function (or partial) and fails. The chain is bottom-to-top:
  ```python
  @MessageCommand.add_descriptions(**ARGS_DESC)
  @MessageCommand.with_name("name")
  async def message_cmd(broker, client, message, state, ...) -> State: ...
  ```
- **"functions named like the class" are not OS-entrypoints — they are decorated objects.** `message_*`, `interaction_*` pairs, and `*_tool` functions are registry entries; `from_name(...)`/`Tool.from_name(...)`/`Action` resolution finds them by string name at runtime. `interaction_*` functions also expose `interaction.client`.
- **`Command`/`Tool`/`Action` are `typing.Protocol`s.** They use `Concatenate` + `**ExtraArgs` to model injected args and are invoked dynamically; you can call `X.from_name(name)` then `await inst(...)` or `inst.evaluate(...)`.
- **Auto-arg convention:** the first 3 positional params are always `broker: EventBroker`, `client: Client`, `state` (or `message`/`interaction` for commands). `MessageCommand.parse_arguments` / `InteractionCommand.evaluate` map the remaining `**ExtraArgs` from user text / interaction data.
- **ClassVars are per-class registries, not inherited.** Each wrapper class declares its own `COMMANDS`/`TOOLS`/`CALLBACKS` dict. Do not "unify" them into a shared base: a shared `ClassVar` dict would cross-contaminate registries (verified) and break dynamic dispatch.
- Respect the **explicit `broker`/`client`/`state` signatures** in `AGENTS.md` per subsystem; never access the `EVENT_BROKER` singleton or global client from inside handlers.

## Core Rules

1. **Type Hints**: Use maximally explicit type hints strictly adhering to Python 3.12 syntax (e.g. `list[int]`, `dict[str, Any]`, `tuple[A, B]`). Avoid `Any` unless strictly necessary (such as generic event payloads or framework boundary types).
2. **Import Style**: Always prefer `from module import symbol` over `import module` followed by `module.symbol(...)`, unless the latter is a strong standard convention (e.g., `import asyncio`, `import re`).
3. **Explicit EventBroker Passing**: Despite the existence of a singleton `EVENT_BROKER`, functions, commands, tools, actions, and routers MUST accept `broker: EventBroker` as an explicit argument rather than accessing the singleton directly inside handlers.
4. **Stateless Functions & Annotations**:
   - If an action, command, tool, or function uses no state, set explicit `None` in type annotations (e.g., `state: None`).
   - Correspondingly, return `None` as the state component in returned tuples (e.g. `return result, None`).
5. **Flow Diagrams**: Always use `mermaid` code blocks (````mermaid ... ````) for architecture diagrams and flowcharts rather than ASCII art.
6. **Development Artifacts**: Files starting with `[dev]` (e.g., `[dev]cookie_converter.py`, `[dev]cpu_load.py`) are temporary development scripts. **NEVER** import or use `[dev]` artifacts in production bot code.
7. **Code-Doc Synchronization**: Whenever code, signature, or feature behavior changes, update the corresponding documentation files immediately to keep docs strictly synchronized with the implementation.
8. **No Useless Comments & No Bloat**:
   - Do not add commentary stating what code obviously does. Comment only critical *why* rationale when non-obvious.
   - Keep `README.md` files concise (10–100 lines) and human-friendly.

## Architecture Guidelines

- **Actions (`discord_bot/actions/`)**: Core stateless/stateful business logic wrapped with `@Action`. Features automatic ID resolution via `@id_parser`.
- **Routers (`discord_bot/routers/`)**: Two-level event routing layer (global guild routers managing lifecycle + server-local routers handling guild events).
- **State (`discord_bot/state_types.py` & `state_manager.py`)**: Hierarchical, thread/async-safe `GroupState` containers.
- **Events (`discord_bot/events/`)**: In-memory event broker (`EVENT_BROKER`) and event models.

## Nested Documentation Index

- [Actions Rules](discord_bot/actions/AGENTS.md)
- [Routers Rules](discord_bot/routers/AGENTS.md)
- [CLI Commands Rules](discord_bot/routers/discord_cli/commands/AGENTS.md)
- [Agent Tools Rules](discord_bot/routers/discord_agent/tools/AGENTS.md)
- [Events Rules](discord_bot/events/AGENTS.md)
