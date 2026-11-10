# Security notes

## Threat model

`cqrs_kit` is a synchronous, in-process Python library with no runtime dependencies and no I/O. Its security boundary is the application process; it does not authenticate, authorize, isolate, or sandbox handlers, middleware, or subscribers.

Defended:

- Exact-type dispatch: a subclass message does not invoke a handler or subscriber registered for a base class.
- Command event integrity: events emitted during a command dispatch are buffered and published only after the handler and all middleware return normally; an exception discards the buffer and propagates unchanged.
- Subscriber isolation: a subscriber exception is logged at WARNING with the event type name only, reported through `on_event` if configured, and does not stop later subscribers.
- Resource limits: each bus limits registered types to 10,000; `EventBus` limits subscribers to 1,000 per event type; `CommandBus` limits dispatch nesting to `max_depth` (default 32) and emissions per dispatch to `max_events_per_dispatch` (default 1,000). Exceeding these raises `CqrsError` with the documented code.
- No dynamic execution: the code does not use `eval`, `exec`, or deserialization of untrusted data.

Not defended:

- Code executed inside handlers, middleware, or subscribers; those callables run with the caller's full privileges.
- Authentication, authorization, input validation beyond the checks in `register` and `subscribe` (the type is a class and the handler is callable), secret storage, transport security, or persistence.
- Thread safety or concurrent mutation of bus registries; buses are synchronous and use no locks.
- Memory exhaustion from large event or message payloads; limits count entries, not payload size.
- Async execution, process boundaries, outbox delivery, or exactly-once semantics.

## Publishing

The library contains no release, publishing, credential, or network code. Any release automation and PyPI credentials live outside `src/cqrs_kit`.
