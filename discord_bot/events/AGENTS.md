# Events Subsystem Rules

## Rules for Events
1. **Explicit Broker Passing**: Always pass `broker: EventBroker` explicitly into functions, commands, tools, and actions rather than accessing global `EVENT_BROKER` inside business logic.
2. **Event Models**: Inherit from `Event` base class in `event_models/base.py`.
3. **Key Generation**: Provide explicit `key_from_context(...)` class methods for pub/sub key routing.
4. **Non-blocking Publishing**: Event publication is non-blocking (`await broker.publish(event)` queues the event for background processing).
