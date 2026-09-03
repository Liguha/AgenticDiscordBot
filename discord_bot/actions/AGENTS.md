# Actions Subsystem Rules

## Dialect: Wrapper instances, not functions
`@Action` immediately wraps the raw function into an `Action` instance at import time (the module-level name is an instance, not a function). Dispatch happens through `Action.__call__`, which binds `broker, client, state` and auto-resolves ID arguments via the id-parser registry before invoking the wrapped function. This is the same "decorator class" dialect used by `MessageCommand`/`InteractionCommand`/`Tool` — see root `AGENTS.md` → "The Decorator Class Dialect".

## Rules for Actions
1. **Decoration**: Always decorate core action functions with `@Action`.
2. **Signature Standard**:
   ```python
   @Action
   async def action_name(broker: EventBroker, client: Client, state: StateType, ...) -> tuple[ResultType, StateType]:
       ...
   ```
3. **ID Parsers**: `@Action` converts ID strings/integers into Discord objects automatically. Extend parsers using `@id_parser` in `wrapper.py` when support for new Discord object conversions is required.
4. **Explicit Broker Passing**: Always include `broker: EventBroker` as the first argument in action signatures rather than importing `EVENT_BROKER` directly inside actions.
5. **Stateless Actions**:
   - If no state is needed, annotate `state: None` in parameters.
   - Return `None` for the state element in returned tuples: `return result, None`.
6. **Reusability**: Actions MUST NOT contain UI-specific or interaction-specific assumptions (such as replying to a message or deferring an interaction). Interaction handling belongs exclusively in Routers/Commands/Tools.
7. **Types**: Use Python 3.12 explicit type annotations. Do not use `Any` unless working with raw payload dynamic dictionaries.
