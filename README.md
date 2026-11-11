# cqrs-kit

Typed command, query and event buses for Python.

`cqrs_kit` provides three synchronous buses for applications that separate writes from reads. Handlers and subscribers are looked up by the exact runtime type of the message, never by inheritance. Commands buffer emitted events and publish them only after the command handler and all middleware return normally. Failures use `CqrsError` with a stable, machine-readable code.

## Installation

```bash
pip install trysac-cqrs-kit
```

## Quick start

```python
from cqrs_kit import EventBus, CommandBus


class CreateUser:
    def __init__(self, name):
        self.name = name


events = EventBus()
bus = CommandBus(events)
bus.register(CreateUser, lambda cmd, emit: cmd.name.upper())
print(bus.dispatch(CreateUser("ana")))  # ANA
```

## API overview

- `EventBus(*, on_event: Callable[[dict[str, str]], None] | None = None)` — `subscribe(event_type: type, handler: Callable[[object], None]) -> Callable[[], None]` registers a subscriber for exact `event_type` and returns an unsubscribe function; `publish(event: object) -> None` calls subscribers in subscription order. `publish` iterates over a snapshot, so unsubscribing during a publish affects the next publish. A subscriber failure is logged at WARNING, reported to `on_event` as `{"event": "subscriber_failed", "event_type": <class __name__>, "subscriber": <handler __qualname__>}`, and does not stop later subscribers.
- `CommandBus(events: EventBus, *, middlewares: Sequence[Middleware] = (), max_depth: int = 32, max_events_per_dispatch: int = 1_000)` — `register(command_type: type, handler: Callable[[object, Callable[[object], None]], object]) -> None` registers one handler per exact command type; `dispatch(command: object) -> object` runs the middleware chain, calls the handler with `(command, emit)`, buffers events from `emit`, and publishes them in emission order after normal return. If anything raises, the buffer is discarded and the original exception propagates unchanged.
- `QueryBus(*, middlewares: Sequence[Middleware] = ())` — `register(query_type: type, handler: Callable[[object], object]) -> None` registers one handler per exact query type; `ask(query: object) -> object` returns the handler result. Query handlers have no `emit`, so queries cannot publish events.
- `Middleware` — `Callable[[object, Callable[[object], object]], object]`; middlewares wrap the handler in list order, the first element outermost. A middleware may short-circuit by not calling `call_next`.
- `CqrsError(code)` — exception with `.code` from the set below.

Limits: one handler per command or query type; at most 10,000 registered command types, 10,000 query types, and 10,000 event types per bus; at most 1,000 subscribers per event type. `CommandBus` limits dispatch nesting to `max_depth` (default 32) and a single dispatch to `max_events_per_dispatch` emitted events (default 1,000).

## Error codes

| Code | Meaning |
|---|---|
| `duplicate_handler` | A handler is already registered for this exact command or query type. |
| `no_handler` | No handler is registered for the exact type of the message. |
| `invalid_registration` | The type is not a class or the handler is not callable. |
| `dispatch_depth_exceeded` | Command dispatch nesting exceeded `max_depth` (default 32). |
| `too_many_events` | A single dispatch emitted more than `max_events_per_dispatch` events. |
| `too_many_handlers` | Maximum registered types per bus or subscribers per event type was exceeded. |

## Why not a larger CQRS framework

`cqrs_kit` is three strict, small, synchronous buses whose failure semantics are written down and tested. It has no dependency-injection container, no async runtime, no persistence, and no outbox to adopt; applications keep their own handler wiring and infrastructure.

## Design notes

- No asynchronous support, dependency injection, sagas, outbox, or persistence.
- Middleware order: the first element is the outermost; it may skip the chain entirely.
- Subscriber failures are logged at WARNING and reported via `on_event`; they never stop other subscribers.
- Queries cannot publish events because query handlers do not receive an `emit` callable.

Security notes and the threat model are in [docs/SECURITY.md](docs/SECURITY.md).

## License

MIT
