# Events Subsystem

The Events subsystem provides an in-memory event broker (`EVENT_BROKER`) and event models to decouple producers from consumers.

## Architecture & Principles
- **Explicit Broker Injection**: Although `EVENT_BROKER` is provided as a default singleton instance in `event_broker.py`, `EventBroker` instances are passed explicitly as parameters throughout actions, commands, tools, and routers. This design choice ensures modularity, explicit dependency flow, and easy testability without relying on implicit global state in handlers.
- **`event_broker.py`**: Pub/sub engine (`EventBroker`) managing event queues and callbacks.
- **`event_models/`**: Event schemas (`DiscordMessageEvent`, `DiscordInteractionEvent`, `DiscordGuildJoinEvent`, `DiscordCallabackEvent`, `AgentToolEvent`).
- **`producers/`**: Event sources (e.g. `DiscrordEventProducer` listening on Discord client events and publishing into `EventBroker`).
