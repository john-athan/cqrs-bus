import logging
from collections.abc import Callable
from typing import Any, TypeVar

from cqrs_bus.bus import MessageBus, Middleware
from cqrs_bus.commands.command import Command, CommandHandler

logger = logging.getLogger(__name__)

TCommand = TypeVar("TCommand", bound=Command)
TResult = TypeVar("TResult")

try:
    from prometheus_client import Counter, Histogram

    _command_duration = Histogram(
        "command_duration_seconds",
        "Command handler execution duration",
        ["command_type"],
    )
    _command_errors = Counter(
        "command_errors_total",
        "Total command handler errors",
        ["command_type", "error_type"],
    )
    _command_total = Counter(
        "command_executions_total",
        "Total command executions",
        ["command_type"],
    )
    _prometheus = True
except ImportError:
    _prometheus = False


class CommandBus(MessageBus[Command]):
    _logger = logger
    _label = "CommandBus"
    _noun = "command"
    _id_key = "command_id"
    _type_key = "command_type"
    _log_slow = True

    def __init__(
        self,
        on_dispatch: Callable[[str, float, "Exception | None"], None] | None = None,
        middleware: "list[Middleware] | None" = None,
    ):
        super().__init__(on_dispatch=on_dispatch, middleware=middleware)

    def register(self, command_type: type[TCommand], handler: CommandHandler[TCommand, Any]) -> None:
        super().register(command_type, handler)

    async def dispatch(self, command: "Command[TResult]") -> TResult:
        return await super().dispatch(command)

    def _inc_total(self, name: str) -> None:
        if _prometheus:
            _command_total.labels(command_type=name).inc()

    def _observe(self, name: str, duration: float) -> None:
        if _prometheus:
            _command_duration.labels(command_type=name).observe(duration)

    def _inc_error(self, name: str, error_type: str) -> None:
        if _prometheus:
            _command_errors.labels(command_type=name, error_type=error_type).inc()
