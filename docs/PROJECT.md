# Project record

## Objective

Typed command, query and event buses for Python: exact-type handler lookup, onion middleware, events published only after a command succeeds, and bounded nesting.

## Scope

In scope:

- The public API of `cqrs_kit`: `EventBus`, `CommandBus`, `QueryBus`, `Middleware`, and `CqrsError`.
- Exact runtime-type lookup for handlers and subscribers.
- Synchronous onion middleware for commands and queries.
- Per-dispatch event buffering; events publish only after the command handler and all middleware succeed.
- Bounded dispatch depth, events per dispatch, registered types per bus, and subscribers per event type.
- Stable, machine-readable error codes.

Out of scope:

- Asynchronous handlers.
- Sagas or process managers.
- Persistence.
- An outbox.
- Dependency injection.
- Handler discovery by decorators or imports.
- Any runtime dependency or I/O layer.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 859141 / 56444 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.0871 |

## Factory run u241 (measured from API usage)

| Date (UTC) | Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 2026-11-10 | generation | deepseek-v4-pro | yes | 1550 | 17619 | 0 | 3200 | 0.0360 |
| 2026-11-10 | fix-1 | deepseek-flash | no | 28538 | 3314 | 0 | 216448 | 0.0069 |
| 2026-11-10 | audit | deepseek-flash | no | 31797 | 24237 | 0 | 465792 | 0.0207 |
| 2026-11-10 | docs | deepseek-flash | no | 111560 | 11274 | 0 | 256 | 0.0235 |

Total: $0.0871. Prices: deepseek line, as measured by its adapter. Providers serve the current version of each model id, so the date tells which version answered; versions, launch stages and price sources per line are in the factory's model register (docs/MODELS.md).
