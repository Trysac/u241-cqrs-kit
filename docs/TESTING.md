# Testing

## Running

```sh
pytest tests/test_cqrs_kit.py
```

## Policy

The tests import the public `cqrs_kit` API and assert observable results: return values, raised `CqrsError` codes, call order, and side effects. They use plain pytest functions and do not require network access or external services.

## Tiers

There is one test tier: `tests/test_cqrs_kit.py`. No conformance, property-test, or external-tool test files are present.

## Layout

The only test file is `tests/test_cqrs_kit.py`; there is no `tests/conftest.py` in the provided tree.

## What the tests cover

`tests/test_cqrs_kit.py` contains these tests:

- `test_command_basic_registration_and_dispatch` — command dispatch return value, duplicate registration, and missing handler.
- `test_exact_type_lookup_subclass_not_found` — a subclass command with no handler raises `no_handler`.
- `test_register_validation` — registration rejects non-class types and non-callables with `invalid_registration`.
- `test_middleware_order` — command middleware runs in list order, first outermost.
- `test_middleware_short_circuit` — a middleware can skip the handler and prevent events.
- `test_dispatch_returns_none` — a handler returning `None` is preserved.
- `test_plain_class_message` — plain classes work as messages.
- `test_event_buffering_and_order` — events publish after the handler, in emission order.
- `test_exception_discards_events` — a handler exception propagates unchanged and no subscriber is called.
- `test_subscriber_failure_does_not_stop_others` — subscriber failures are isolated and reported through `on_event` without the event payload.
- `test_unsubscribe_during_publish_takes_effect_next_publish` — unsubscribe affects the next publish, not the current one.
- `test_command_bus_max_registered_types` — command registration limit raises `too_many_handlers`.
- `test_query_bus_max_registered_types` — query registration limit raises `too_many_handlers`.
- `test_event_bus_max_event_types` — event-type registration limit raises `too_many_handlers`.
