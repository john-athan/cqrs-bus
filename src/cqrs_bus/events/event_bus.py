import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from uuid import uuid4

from cqrs_bus.events.event import Event, EventHandler

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram

    _event_duration = Histogram(
        "event_duration_seconds",
        "Event publish duration across all subscribers",
        ["event_type"],
    )
    _event_errors = Counter(
        "event_handler_errors_total",
        "Total event handler errors",
        ["event_type", "error_type"],
    )
    _event_total = Counter(
        "event_publications_total",
        "Total event publications",
        ["event_type"],
    )
    _prometheus = True
except ImportError:
    _prometheus = False


class EventBus:
    """Publish/subscribe bus: an event may have many independent subscribers.

    Subscribers run concurrently and in isolation — one failing handler is
    logged (and counted in metrics) but never aborts the others, and
    ``publish`` itself does not raise. This matches domain-event semantics: the
    publisher is decoupled from whoever happens to be listening.
    """

    def __init__(self, on_dispatch: Callable[[str, float, "Exception | None"], None] | None = None):
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)
        self._on_dispatch = on_dispatch

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def handler_count(self, event_type: type[Event]) -> int:
        return len(self._handlers.get(event_type, []))

    async def publish(self, event: Event) -> None:
        event_type = type(event)
        name = event_type.__name__
        event_id = str(uuid4())
        extra = {"event_id": event_id, "event_type": name}

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug(f"[EventBus] No subscribers for {name}", extra=extra)
            return

        if _prometheus:
            _event_total.labels(event_type=name).inc()

        logger.debug(f"[EventBus] Publishing {name} to {len(handlers)} subscriber(s)", extra=extra)
        start_time = time.monotonic()

        results = await asyncio.gather(*(self._invoke(handler, event, name, event_id) for handler in handlers))

        duration = time.monotonic() - start_time
        if _prometheus:
            _event_duration.labels(event_type=name).observe(duration)

        errors = [result for result in results if result is not None]
        if self._on_dispatch:
            self._on_dispatch(name, duration, errors[0] if errors else None)

        if errors:
            logger.error(
                "[EventBus] %s: %d of %d subscriber(s) failed",
                name,
                len(errors),
                len(handlers),
                extra=extra,
            )
        else:
            logger.debug(f"[EventBus] Success: {name} ({duration:.3f}s)", extra=extra)

    async def _invoke(
        self,
        handler: EventHandler,
        event: Event,
        name: str,
        event_id: str,
    ) -> "Exception | None":
        # Isolation: catch here so one subscriber's failure can't cancel the
        # asyncio.gather and take down its siblings. Return the error for the
        # caller to summarize.
        try:
            await handler.handle(event)
            return None
        except Exception as e:
            error_type = type(e).__name__
            if _prometheus:
                _event_errors.labels(event_type=name, error_type=error_type).inc()
            logger.error(
                "[EventBus] Subscriber %s failed for %s - %s",
                type(handler).__name__,
                name,
                error_type,
                extra={
                    "event_id": event_id,
                    "event_type": name,
                    "error_type": error_type,
                    "handler_type": type(handler).__name__,
                },
                exc_info=True,
            )
            return e
