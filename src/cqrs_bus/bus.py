"""Shared message-bus machinery for the command and query buses.

``MessageBus`` owns everything the command and query buses have in common:
the handler registry, the middleware pipeline, dispatch orchestration, timing,
the ``on_dispatch`` callback, and structured logging. Subclasses supply only
what genuinely differs — the logger, the human-facing noun, the structured-log
key names, whether to emit slow-message warnings, and how to record metrics.
"""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar
from uuid import uuid4

TMessage = TypeVar("TMessage")

#: A continuation that invokes the rest of the pipeline (downstream middleware
#: and ultimately the handler) for a message, returning the handler result.
Next = Callable[[Any], Awaitable[Any]]

#: A middleware wraps the pipeline: it receives the message and a ``call_next``
#: continuation, and returns a result. It may inspect or replace the message,
#: short-circuit (skip ``call_next``), transform the result, or handle errors.
Middleware = Callable[[Any, Next], Awaitable[Any]]


class MessageBus(Generic[TMessage]):
    # --- per-bus configuration, overridden by subclasses ---
    _logger: logging.Logger = logging.getLogger(__name__)
    _label: str = "MessageBus"  # log-line prefix, e.g. "[CommandBus]"
    _noun: str = "message"  # human noun in error messages, e.g. "command"
    _id_key: str = "message_id"  # structured-log key for the per-dispatch id
    _type_key: str = "message_type"  # structured-log key for the message name
    _log_slow: bool = False  # emit an INFO line for slow dispatches
    _slow_threshold: float = 1.0  # seconds; only consulted when _log_slow

    def __init__(
        self,
        on_dispatch: Callable[[str, float, "Exception | None"], None] | None = None,
        middleware: "list[Middleware] | None" = None,
    ):
        self._handlers: dict[type, Any] = {}
        self._on_dispatch = on_dispatch
        self._middleware: list[Middleware] = list(middleware or [])

    def register(self, message_type: type, handler: Any) -> None:
        if message_type in self._handlers:
            raise ValueError(f"Handler already registered for {self._noun} type {message_type.__name__}")
        self._handlers[message_type] = handler

    def add_middleware(self, middleware: Middleware) -> None:
        """Append a middleware to the pipeline.

        Middlewares run outermost-first: the first one added is the outermost
        wrapper and sees the message before — and the result after — every
        middleware added later.
        """
        self._middleware.append(middleware)

    async def dispatch(self, message: Any) -> Any:
        message_type = type(message)
        name = message_type.__name__
        message_id = str(uuid4())
        extra = {self._id_key: message_id, self._type_key: name}

        handler = self._handlers.get(message_type)
        if handler is None:
            self._logger.error(f"[{self._label}] No handler registered for {name}", extra=extra)
            raise ValueError(f"No handler registered for {self._noun} type {name}")

        self._logger.debug(
            f"[{self._label}] Dispatching {name} to {type(handler).__name__}",
            extra={**extra, "handler_type": type(handler).__name__},
        )

        self._inc_total(name)
        chain = self._build_chain(handler)
        start_time = time.monotonic()

        try:
            result = await chain(message)
            duration = time.monotonic() - start_time

            self._observe(name, duration)
            if self._on_dispatch:
                self._on_dispatch(name, duration, None)
            self._log_success(name, message_id, duration)
            return result

        except Exception as e:
            duration = time.monotonic() - start_time
            error_type = type(e).__name__

            self._inc_error(name, error_type)
            if self._on_dispatch:
                self._on_dispatch(name, duration, e)
            self._logger.error(
                "[%s] Failed: %s - %s",
                self._label,
                name,
                error_type,
                extra={**extra, "error_type": error_type},
                exc_info=True,
            )
            raise

    def _build_chain(self, handler: Any) -> Next:
        async def core(message: Any) -> Any:
            return await handler.handle(message)

        chain: Next = core
        for middleware in reversed(self._middleware):
            chain = self._link(middleware, chain)
        return chain

    @staticmethod
    def _link(middleware: Middleware, call_next: Next) -> Next:
        async def linked(message: Any) -> Any:
            return await middleware(message, call_next)

        return linked

    def _log_success(self, name: str, message_id: str, duration: float) -> None:
        extra = {self._id_key: message_id, self._type_key: name, "duration_seconds": duration}
        if self._log_slow and duration > self._slow_threshold:
            self._logger.info(f"[{self._label}] Slow {self._noun}: {name} ({duration:.3f}s)", extra=extra)
        else:
            self._logger.debug(f"[{self._label}] Success: {name} ({duration:.3f}s)", extra=extra)

    # --- metric hooks: no-ops here, overridden when prometheus is installed ---
    def _inc_total(self, name: str) -> None: ...

    def _observe(self, name: str, duration: float) -> None: ...

    def _inc_error(self, name: str, error_type: str) -> None: ...
