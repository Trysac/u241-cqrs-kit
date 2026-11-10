# Adopt strict exact-type buses with onion middleware for CQRS

Status: accepted (generated, pending human review)

## Context

Applications separating writes from reads often maintain ad hoc handler dictionaries, leading to silent misdispatch and events published on failure. Full CQRS frameworks bring dependencies and async runtimes that many services do not need.

## Decision

Implement three small, synchronous buses (EventBus, CommandBus, QueryBus) with exact-type handler lookup, onion middleware, buffered events published only after command success, and bounded nesting/event limits. All errors use a single `CqrsError` with machine-readable codes.

## Consequences

Predictable failure semantics and easy unit testing. The library remains minimal and deliberately omits async, persistence, sagas, and dependency injection.
