# Routers Subsystem

Routers receive events from the Event Broker or Discord client and dispatch them to the appropriate Action wrappers, command handlers, or agent tools.

## Router Architecture
- **Two-Level Router Hierarchy**:
  - **Global Guild Routers (`DiscordGuildRouter`, e.g., `DiscordCLIGuildRouter`, `DiscordAgentGuildRouter`)**: Manage lifecycle across all joined guilds. They listen for guild-join events and instantiate/start local guild routers dynamically.
  - **Local Server Routers (`Router`, e.g., `DiscordCLIRouter`, `DiscordAgentRouter`)**: Created per guild server. They handle guild-specific event routing, command execution, agent LLM sessions, and state synchronization.
- **`base.py`**: Defines abstract `Router` and `DiscordGuildRouter`.
- **`state_manager.py`**: Hierarchical, thread/async-safe state management (`GroupState` and `StateManager`) with RWLocks and periodic JSON serialization.
- **`discord_cli/`**: Router for CLI slash commands, message prefix commands, and interaction callbacks.
- **`discord_agent/`**: Router for LLM agent interaction, converting LLM tool-use calls into action invocations.
