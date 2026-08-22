# Routers Subsystem Rules

## Rules for Routers
1. **Two-Level Router Hierarchy**:
   - Use top-level `DiscordGuildRouter` subclasses to manage multi-guild lifecycle and dynamic guild initialization.
   - Use inner `Router` subclasses to implement server-local event handling and routing.
2. **Group Hierarchy & State**: State is organized hierarchically by group IDs (e.g., guild ID). Access state via `self.group_state[group_id]`.
3. **Locking**: Always acquire exclusive locks before mutating state in router handlers:
   ```python
   async with node.lock():
       node[...] = await func(...)
   ```
4. **Explicit Broker Passing**: Pass `broker: EventBroker` explicitly through router constructors down to action calls and tools.
5. **Event Subscriptions**: Subscribe to events during `start()` and store subscriber tokens to cancel them in `stop()`.
6. **Context Cleanup**: Ensure clean teardown in `stop()` when guilds or sessions are removed.
