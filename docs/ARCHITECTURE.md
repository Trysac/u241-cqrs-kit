# Architecture

## Overview

`cqrs_kit` implements three synchronous buses for command-query responsibility segregation (CQRS) in Python, with strict rules designed for testability and predictability.

## Core principles

1. **Exact-type lookup**  
   Handlers and subscribers are stored in dictionaries keyed by the exact runtime type of the message (`type(message)`). Inheritance is ignored. This prevents accidental dispatch to a base handler when a subclass is intended.

2. **Onion middleware**  
   Middleware is a simple callable `(message, call_next) -> result`. The chain is built from the supplied sequence in list order, with the first middleware outermost. A middleware may short-circuit by not calling `call_next`.

3. **Buffered command events**  
   During `CommandBus.dispatch`, calls to `emit` append events to a local buffer. The buffer is published to the associated `EventBus` only after the handler and all middleware return without exception. A nested `dispatch` creates its own buffer independently.

4. **Bounded resources**  
   - `max_depth` limits recursive dispatch calls (default 32).
   - `max_events_per_dispatch` limits event emissions per dispatch (default 1000).
   - Each bus limits the total number of registered types (10,000).
   - `EventBus` additionally limits subscribers per event type (1,000).

## Error model

All failures raise `CqrsError` with a `code` attribute from a fixed set. Original exceptions from handlers, middleware, or subscribers are propagated without wrapping (except subscriber failures, which are caught, logged, and reported).

## Logging

The package uses `logging.getLogger(__name__)` and attaches a `NullHandler`. Subscriber failures are logged at WARNING with the event type name only; no exception details or event payloads are logged.

## Testing strategy

- Unit tests cover every acceptance criterion and additional edge cases (unsubscribe during publish, middleware short‑circuit, plain class messages, `None` return).
- Limits are tested by temporarily overriding internal limit attributes.
- Deterministic: no time, randomness, or I/O.
