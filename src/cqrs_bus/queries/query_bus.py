import logging
from collections.abc import Callable
from typing import Any, TypeVar

from cqrs_bus.bus import MessageBus, Middleware
from cqrs_bus.queries.query import Query, QueryHandler

logger = logging.getLogger(__name__)

TQuery = TypeVar("TQuery", bound=Query)
TResult = TypeVar("TResult")

try:
    from prometheus_client import Counter, Histogram

    _query_duration = Histogram(
        "query_duration_seconds",
        "Query handler execution duration",
        ["query_type"],
    )
    _query_errors = Counter(
        "query_errors_total",
        "Total query handler errors",
        ["query_type", "error_type"],
    )
    _query_total = Counter(
        "query_executions_total",
        "Total query executions",
        ["query_type"],
    )
    _prometheus = True
except ImportError:
    _prometheus = False


class QueryBus(MessageBus[Query]):
    _logger = logger
    _label = "QueryBus"
    _noun = "query"
    _id_key = "query_id"
    _type_key = "query_type"

    def __init__(
        self,
        on_dispatch: Callable[[str, float, "Exception | None"], None] | None = None,
        middleware: "list[Middleware] | None" = None,
    ):
        super().__init__(on_dispatch=on_dispatch, middleware=middleware)

    def register(self, query_type: type[TQuery], handler: QueryHandler[TQuery, Any]) -> None:
        super().register(query_type, handler)

    async def dispatch(self, query: "Query[TResult]") -> TResult:
        return await super().dispatch(query)

    def _inc_total(self, name: str) -> None:
        if _prometheus:
            _query_total.labels(query_type=name).inc()

    def _observe(self, name: str, duration: float) -> None:
        if _prometheus:
            _query_duration.labels(query_type=name).observe(duration)

    def _inc_error(self, name: str, error_type: str) -> None:
        if _prometheus:
            _query_errors.labels(query_type=name, error_type=error_type).inc()
