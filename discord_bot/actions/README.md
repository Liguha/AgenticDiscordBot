# Actions Subsystem

The Actions layer contains the core business logic of the bot. Actions are designed to be flow-agnostic so that both CLI commands and Agent tools invoke the exact same underlying logic.

## Key Principles
- **Wrapper (`@Action`)**: Actions are decorated with `@Action` from `discord_bot/actions/wrapper.py`.
- **ID Parsers**: `@Action` automatically resolves text/numeric IDs (e.g. channel ID or user ID strings/integers) into native Discord objects (such as `GuildChannel` or `User`) before calling the action function.
  - Custom parsers can be added via the `@id_parser` decorator in `wrapper.py` or extended on `Action.ID_PARSERS_REGISTRY`.
- **Explicit Broker Injection**: Even though `EVENT_BROKER` exists as a global singleton, `EventBroker` is explicitly passed as a parameter (`broker: EventBroker`) to actions to maintain modular testability and explicit dependency chains.
- **State In / State Out**: Action functions accept `state` as a parameter and return `tuple[Result, State]`.
- **Stateless Actions**: If an action requires no state, annotate `state: None` and return `None` as the state component (`return result, None`).

## Directory Structure
- `wrapper.py`: `@Action` decorator, `@id_parser` registry, and ID resolution parsers.
- `actions/`: Action functions grouped by domain (`audio/`, `web_search.py`, `send_message.py`).
