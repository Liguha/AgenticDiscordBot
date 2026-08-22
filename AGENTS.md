# Agent Guidelines & Repository Rules

This document outlines core principles, coding conventions, and documentation standards for AI coding agents working on this repository.

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
