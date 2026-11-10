"""Typed command, query and event buses for Python.

Provides three small, synchronous buses with strict, documented rules:

- :class:`EventBus` manages subscription and publication of events.
- :class:`CommandBus` dispatches commands, buffers emitted events and publishes
  them only after the command and its middleware succeed.
- :class:`QueryBus` dispatches queries without side effects.

All handler lookups are by exact type of the message, never by inheritance.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable, Sequence
from typing import Literal, TypeAlias

__all__ = [
    "CommandBus",
    "CqrsError",
    "EventBus",
    "Middleware",
    "QueryBus",
]

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

CqrsErrorCode = Literal[
    "duplicate_handler",
    "no_handler",
    "invalid_registration",
    "dispatch_depth_exceeded",
    "too_many_events",
    "too_many_handlers",
]


class CqrsError(Exception):
    """Base error for all bus failures, with a stable machine-readable code."""

    def __init__(self, code: CqrsErrorCode) -> None:
        super().__init__(code)
        self.code: CqrsErrorCode = code


Middleware: TypeAlias = Callable[[object, Callable[[object], object]], object]


def _compose(
    middleware: Middleware,
    call_next: Callable[[object], object],
) -> Callable[[object], object]:
    """Wrap ``call_next`` with ``middleware`` (which becomes the outer layer)."""

    def wrapped(message: object) -> object:
        return middleware(message, call_next)

    return wrapped


class EventBus:
    """Synchronous event bus with exact-type subscriber lookup.

    Args:
        on_event: Optional callback invoked when a subscriber fails. The
            callback receives a dict with keys ``event``, ``event_type`` and
            ``subscriber`` (all strings).
    """

    def __init__(
        self,
        *,
        on_event: Callable[[dict[str, str]], None] | None = None,
    ) -> None:
        self._on_event = on_event
        self._subscribers: dict[type, list[Callable[[object], None]]] = {}
        self._max_event_types = 10_000
        self._max_subscribers_per_event = 1_000

    def subscribe(
        self,
        event_type: type,
        handler: Callable[[object], None],
    ) -> Callable[[], None]:
        """Register ``handler`` for exact ``event_type``.

        Returns an unsubscribe function that removes the subscription
        idempotently.

        Raises:
            CqrsError: if ``event_type`` is not a class, ``handler`` is not
                callable, the maximum number of event types or subscribers per
                event type is exceeded.
        """
        if not isinstance(event_type, type):
            raise CqrsError("invalid_registration")
        if not callable(handler):
            raise CqrsError("invalid_registration")

        if event_type not in self._subscribers and len(self._subscribers) >= self._max_event_types:
            raise CqrsError("too_many_handlers")

        subscribers = self._subscribers.setdefault(event_type, [])
        if len(subscribers) >= self._max_subscribers_per_event:
            raise CqrsError("too_many_handlers")

        subscribers.append(handler)

        def unsubscribe() -> None:
            try:
                subscribers.remove(handler)
                if not subscribers:
                    self._subscribers.pop(event_type, None)
            except (ValueError, KeyError):
                pass

        return unsubscribe

    def publish(self, event: object) -> None:
        """Publish ``event`` to subscribers for its exact type.

        Subscribers are called in subscription order. If a subscriber raises,
        a warning is logged with the event type name, ``on_event`` is called
        (if provided) and the next subscriber is invoked.
        """
        event_type = type(event)
        subscribers = self._subscribers.get(event_type, [])
        # Snapshot the list so unsubscribing during publish affects only the
        # next publish.
        for handler in list(subscribers):
            try:
                handler(event)
            except Exception:
                logger.warning("Event subscriber failed for %s", event_type.__name__)
                if self._on_event is not None:
                    with contextlib.suppress(Exception):
                        self._on_event(
                            {
                                "event": "subscriber_failed",
                                "event_type": event_type.__name__,
                                "subscriber": handler.__qualname__,
                            }
                        )


class CommandBus:
    """Synchronous command bus with onion middleware and buffered events.

    Args:
        events: The :class:`EventBus` to which emitted events are published.
        middlewares: Optional sequence of :class:`Middleware` callables. The
            first element is the outermost middleware.
        max_depth: Maximum nesting depth of dispatches (default 32).
        max_events_per_dispatch: Maximum number of events a single command may
            emit (default 1000).
    """

    def __init__(
        self,
        events: EventBus,
        *,
        middlewares: Sequence[Middleware] = (),
        max_depth: int = 32,
        max_events_per_dispatch: int = 1_000,
    ) -> None:
        self._events = events
        self._middlewares = tuple(middlewares)
        self._handlers: dict[
            type,
            Callable[[object, Callable[[object], None]], object],
        ] = {}
        self._max_depth = max_depth
        self._max_events_per_dispatch = max_events_per_dispatch
        self._depth = 0
        self._max_command_types = 10_000

    def register(
        self,
        command_type: type,
        handler: Callable[[object, Callable[[object], None]], object],
    ) -> None:
        """Register ``handler`` for exact ``command_type``.

        Raises:
            CqrsError: if ``command_type`` is not a class, ``handler`` is not
                callable, a handler already exists for this type, or the
                maximum number of registered command types is exceeded.
        """
        if not isinstance(command_type, type):
            raise CqrsError("invalid_registration")
        if not callable(handler):
            raise CqrsError("invalid_registration")
        if command_type in self._handlers:
            raise CqrsError("duplicate_handler")
        if len(self._handlers) >= self._max_command_types:
            raise CqrsError("too_many_handlers")
        self._handlers[command_type] = handler

    def dispatch(self, command: object) -> object:
        """Dispatch ``command`` to its exact-type handler.

        Emitted events are buffered and published in order only after the
        handler and all middleware have returned normally. If any exception
        is raised, the buffer is discarded and the exception propagates
        unchanged.

        Raises:
            CqrsError: if no handler is registered for the exact type,
                nesting depth exceeds ``max_depth``, or the command emits more
                than ``max_events_per_dispatch`` events.
        """
        if self._depth >= self._max_depth:
            raise CqrsError("dispatch_depth_exceeded")

        handler = self._handlers.get(type(command))
        if handler is None:
            raise CqrsError("no_handler")

        self._depth += 1
        buffer: list[object] = []

        def emit(event: object) -> None:
            if len(buffer) >= self._max_events_per_dispatch:
                raise CqrsError("too_many_events")
            buffer.append(event)

        def actual_handler(cmd: object) -> object:
            return handler(cmd, emit)

        wrapped: Callable[[object], object] = actual_handler
        for middleware in reversed(self._middlewares):
            wrapped = _compose(middleware, wrapped)

        try:
            result = wrapped(command)
        finally:
            self._depth -= 1

        for event in buffer:
            self._events.publish(event)
        return result


class QueryBus:
    """Synchronous query bus with onion middleware.

    Args:
        middlewares: Optional sequence of :class:`Middleware` callables. The
            first element is the outermost middleware.
    """

    def __init__(self, *, middlewares: Sequence[Middleware] = ()) -> None:
        self._middlewares = tuple(middlewares)
        self._handlers: dict[type, Callable[[object], object]] = {}
        self._max_query_types = 10_000

    def register(
        self,
        query_type: type,
        handler: Callable[[object], object],
    ) -> None:
        """Register ``handler`` for exact ``query_type``.

        Raises:
            CqrsError: if ``query_type`` is not a class, ``handler`` is not
                callable, a handler already exists for this type, or the
                maximum number of registered query types is exceeded.
        """
        if not isinstance(query_type, type):
            raise CqrsError("invalid_registration")
        if not callable(handler):
            raise CqrsError("invalid_registration")
        if query_type in self._handlers:
            raise CqrsError("duplicate_handler")
        if len(self._handlers) >= self._max_query_types:
            raise CqrsError("too_many_handlers")
        self._handlers[query_type] = handler

    def ask(self, query: object) -> object:
        """Ask ``query`` and return the exact-type handler's result.

        Raises:
            CqrsError: if no handler is registered for the exact type.
        """
        handler = self._handlers.get(type(query))
        if handler is None:
            raise CqrsError("no_handler")

        wrapped: Callable[[object], object] = handler
        for middleware in reversed(self._middlewares):
            wrapped = _compose(middleware, wrapped)

        return wrapped(query)
