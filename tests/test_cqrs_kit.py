import logging
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from cqrs_kit import (
    CommandBus,
    CqrsError,
    EventBus,
    Middleware,
    QueryBus,
)

# --- Message fixtures ---


@dataclass
class CreateUser:
    name: str


@dataclass
class DeleteUser:
    id: str


class AdminCreateUser(CreateUser):
    pass


@dataclass
class UserCreated:
    user_id: str


@dataclass
class WelcomeQueued:
    user_id: str


@dataclass
class GetUser:
    id: str


class PlainCommand:
    def __init__(self, value: int) -> None:
        self.value = value


# --- Helper callables ---


def _make_mw(name: str, log: list[str]) -> Middleware:
    def middleware(msg: object, next_: Callable[[object], object]) -> object:
        log.append(f"{name}:before")
        result = next_(msg)
        log.append(f"{name}:after")
        return result

    return middleware


# --- Tests: command registration and dispatch ---


def test_command_basic_registration_and_dispatch() -> None:
    bus = CommandBus(EventBus())

    def handler(cmd: object, emit: Callable[[object], None]) -> object:
        return "u1"

    bus.register(CreateUser, handler)
    assert bus.dispatch(CreateUser(name="ana")) == "u1"

    with pytest.raises(CqrsError) as exc_info:
        bus.register(CreateUser, handler)
    assert exc_info.value.code == "duplicate_handler"

    with pytest.raises(CqrsError) as exc_info:
        bus.dispatch(DeleteUser(id="u1"))
    assert exc_info.value.code == "no_handler"


def test_exact_type_lookup_subclass_not_found() -> None:
    bus = CommandBus(EventBus())
    bus.register(CreateUser, lambda cmd, emit: "base")
    with pytest.raises(CqrsError) as exc_info:
        bus.dispatch(AdminCreateUser(name="bo"))
    assert exc_info.value.code == "no_handler"


def test_register_validation() -> None:
    bus = CommandBus(EventBus())
    with pytest.raises(CqrsError) as exc_info:
        bus.register("not_a_class", lambda cmd, emit: None)  # type: ignore[arg-type]
    assert exc_info.value.code == "invalid_registration"

    with pytest.raises(CqrsError) as exc_info:
        bus.register(CreateUser, "not_callable")  # type: ignore[arg-type]
    assert exc_info.value.code == "invalid_registration"


def test_middleware_order() -> None:
    log: list[str] = []
    m1 = _make_mw("m1", log)
    m2 = _make_mw("m2", log)

    def handler(cmd: object, emit: Callable[[object], None]) -> object:
        log.append("handler")
        return "result"

    bus = CommandBus(EventBus(), middlewares=[m1, m2])
    bus.register(CreateUser, handler)
    result = bus.dispatch(CreateUser(name="ana"))
    assert result == "result"
    assert log == ["m1:before", "m2:before", "handler", "m2:after", "m1:after"]


def test_middleware_short_circuit() -> None:
    handler_called = False

    def handler(cmd: object, emit: Callable[[object], None]) -> object:
        nonlocal handler_called
        handler_called = True
        return "handler"

    def short_middleware(msg: object, next_: Callable[[object], object]) -> object:
        return "short"

    bus = CommandBus(EventBus(), middlewares=[short_middleware])
    bus.register(CreateUser, handler)
    result = bus.dispatch(CreateUser(name="x"))
    assert result == "short"
    assert not handler_called


def test_dispatch_returns_none() -> None:
    bus = CommandBus(EventBus())
    bus.register(CreateUser, lambda cmd, emit: None)
    assert bus.dispatch(CreateUser(name="x")) is None


def test_plain_class_message() -> None:
    bus = CommandBus(EventBus())
    bus.register(PlainCommand, lambda cmd, emit: cmd.value)
    assert bus.dispatch(PlainCommand(42)) == 42


# --- Tests: event buffering and publication ---


def test_event_buffering_and_order() -> None:
    events = EventBus()
    log: list[str] = []

    def user_created_subscriber(event: object) -> None:
        log.append(type(event).__name__)

    def welcome_subscriber(event: object) -> None:
        log.append(type(event).__name__)

    events.subscribe(UserCreated, user_created_subscriber)
    events.subscribe(WelcomeQueued, welcome_subscriber)

    def handler(cmd: object, emit: Callable[[object], None]) -> object:
        emit(UserCreated("u1"))
        emit(WelcomeQueued("u1"))
        log.append("handler done")
        return "result"

    bus = CommandBus(events)
    bus.register(CreateUser, handler)
    result = bus.dispatch(CreateUser(name="ana"))
    assert result == "result"
    assert log == ["handler done", "UserCreated", "WelcomeQueued"]


def test_exception_discards_events() -> None:
    events = EventBus()
    called: list[object] = []
    events.subscribe(UserCreated, lambda e: called.append(e))

    def handler(cmd: object, emit: Callable[[object], None]) -> object:
        emit(UserCreated("u1"))
        raise ValueError("x")

    bus = CommandBus(events)
    bus.register(CreateUser, handler)
    with pytest.raises(ValueError) as exc_info:
        bus.dispatch(CreateUser(name="ana"))
    assert exc_info.value.args == ("x",)
    assert called == []


def test_subscriber_failure_does_not_stop_others() -> None:
    reports: list[dict[str, str]] = []

    def on_event(payload: dict[str, str]) -> None:
        reports.append(payload)

    events = EventBus(on_event=on_event)
    good_calls: list[object] = []

    def good_subscriber(event: object) -> None:
        good_calls.append(event)

    def failing_subscriber(event: object) -> None:
        raise RuntimeError("boom")

    events.subscribe(UserCreated, failing_subscriber)
    events.subscribe(UserCreated, good_subscriber)

    def handler(cmd: object, emit: Callable[[object], None]) -> object:
        emit(UserCreated("u1"))
        return "u1"

    bus = CommandBus(events)
    bus.register(CreateUser, handler)
    result = bus.dispatch(CreateUser(name="ana"))

    assert result == "u1"
    assert len(good_calls) == 1
    assert isinstance(good_calls[0], UserCreated)
    assert len(reports) == 1
    report = reports[0]
    assert set(report.keys()) == {"event", "event_type", "subscriber"}
    assert report["event"] == "subscriber_failed"
    assert report["event_type"] == "UserCreated"
    assert report["subscriber"] == failing_subscriber.__qualname__


def test_unsubscribe_during_publish_takes_effect_next_publish() -> None:
    events = EventBus()
    calls: list[str] = []

    class DummyEvent:
        pass

    def second(event: object) -> None:
        calls.append("second")

    # Subscribe second first, then first
    unsub2 = events.subscribe(DummyEvent, second)

    def first(event: object) -> None:
        calls.append("first")
        # unsubscribe second during this publish
        unsub2()

    events.subscribe(DummyEvent, first)

    events.publish(DummyEvent())
    assert calls == ["second", "first"]

    calls.clear()
    events.publish(DummyEvent())
    assert calls == ["first"]


# --- Tests: limits ---


def test_command_bus_max_registered_types() -> None:
    bus = CommandBus(EventBus())
    bus._max_command_types = 2  # type: ignore[attr-defined]  # internal limit for test

    class C1:
        pass

    class C2:
        pass

    class C3:
        pass

    bus.register(C1, lambda c, e: None)
    bus.register(C2, lambda c, e: None)
    with pytest.raises(CqrsError) as exc_info:
        bus.register(C3, lambda c, e: None)
    assert exc_info.value.code == "too_many_handlers"


def test_query_bus_max_registered_types() -> None:
    qb = QueryBus()
    qb._max_query_types = 2  # type: ignore[attr-defined]

    class Q1:
        pass

    class Q2:
        pass

    class Q3:
        pass

    qb.register(Q1, lambda q: None)
    qb.register(Q2, lambda q: None)
    with pytest.raises(CqrsError) as exc_info:
        qb.register(Q3, lambda q: None)
    assert exc_info.value.code == "too_many_handlers"


def test_event_bus_max_event_types() -> None:
    eb = EventBus()
    eb._max_event_types = 1  # type: ignore[attr-defined]

    class E1:
        pass

    class E2:
        pass

    eb.subscribe(E1, lambda e: None)
    with pytest.raises(CqrsError) as exc_info:
        eb.subscribe(E2, lambda e: None)
    assert exc_info.value.code == "too_many_handlers"


def test_event_bus_max_subscribers_per_event() -> None:
    eb = EventBus()
    eb._max_subscribers_per_event = 2  # type: ignore[attr-defined]

    class E:
        pass

    eb.subscribe(E, lambda e: None)
    eb.subscribe(E, lambda e: None)
    with pytest.raises(CqrsError) as exc_info:
        eb.subscribe(E, lambda e: None)
    assert exc_info.value.code == "too_many_handlers"


def test_dispatch_depth_limit() -> None:
    bus = CommandBus(EventBus())
    depth = 0

    def handler(cmd: object, emit: Callable[[object], None]) -> object:
        nonlocal depth
        depth += 1
        if depth <= 32:
            # trigger nested dispatch; at depth=32 the next dispatch should fail
            bus.dispatch(CreateUser(name="nested"))
        return "done"

    bus.register(CreateUser, handler)
    with pytest.raises(CqrsError) as exc_info:
        bus.dispatch(CreateUser(name="root"))
    assert exc_info.value.code == "dispatch_depth_exceeded"
    # after exception, depth counter restored
    assert bus._depth == 0  # type: ignore[attr-defined]


def test_too_many_events() -> None:
    bus = CommandBus(EventBus())

    def handler(cmd: object, emit: Callable[[object], None]) -> object:
        for _ in range(1001):
            emit(UserCreated("u1"))
        return "ok"

    bus.register(CreateUser, handler)
    with pytest.raises(CqrsError) as exc_info:
        bus.dispatch(CreateUser(name="ana"))
    assert exc_info.value.code == "too_many_events"


# --- Tests: query bus ---


def test_query_basic() -> None:
    qb = QueryBus()
    qb.register(GetUser, lambda q: {"id": q.id})
    result = qb.ask(GetUser(id="u1"))
    assert result == {"id": "u1"}

    with pytest.raises(CqrsError) as exc_info:
        qb.ask(DeleteUser(id="u1"))
    assert exc_info.value.code == "no_handler"

    with pytest.raises(CqrsError) as exc_info:
        qb.register("GetUser", lambda q: None)  # type: ignore[arg-type]
    assert exc_info.value.code == "invalid_registration"


def test_query_middleware_order() -> None:
    log: list[str] = []
    m1 = _make_mw("m1", log)
    m2 = _make_mw("m2", log)

    def handler(q: object) -> object:
        log.append("handler")
        return "result"

    qb = QueryBus(middlewares=[m1, m2])
    qb.register(GetUser, handler)
    result = qb.ask(GetUser(id="u1"))
    assert result == "result"
    assert log == ["m1:before", "m2:before", "handler", "m2:after", "m1:after"]


# --- Logging test ---


def test_subscriber_failure_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    events = EventBus()

    class MyEvent:
        pass

    def failing(event: object) -> None:
        raise RuntimeError()

    events.subscribe(MyEvent, failing)
    with caplog.at_level(logging.WARNING, logger="cqrs_kit"):
        events.publish(MyEvent())
    assert any("Event subscriber failed" in record.message for record in caplog.records)
    assert any("MyEvent" in record.message for record in caplog.records)
