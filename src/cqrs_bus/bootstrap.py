"""High-level wiring: discover handlers and assemble ready-to-use buses.

This is the front door for most applications. Instead of hand-rolling the
discovery -> dependency resolution -> registration loop, call
:func:`build_buses` with the package to scan and a map of shared dependencies.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cqrs_bus.commands.command_bus import CommandBus
from cqrs_bus.discovery.dependency_resolver import DependencyResolver
from cqrs_bus.discovery.handler_discovery import HandlerDiscovery
from cqrs_bus.discovery.handler_registry import HandlerMetadata
from cqrs_bus.events.event_bus import EventBus
from cqrs_bus.queries.query_bus import QueryBus

OnDispatch = Callable[[str, float, "Exception | None"], None]


@dataclass(frozen=True)
class Buses:
    """The assembled command, query, and event buses for an application."""

    command_bus: CommandBus
    query_bus: QueryBus
    event_bus: EventBus


def _wire(
    metadata: list[HandlerMetadata],
    resolver: DependencyResolver,
    dependencies: dict[str, Any],
    register: Callable[[type, Any], None],
) -> None:
    for meta in metadata:
        handler = resolver.create_handler_instance(meta.handler_class, dependencies)
        register(meta.command_or_query_type, handler)


def build_buses(
    base_package: str,
    dependencies: dict[str, Any] | None = None,
    *,
    strict: bool = False,
    on_dispatch: OnDispatch | None = None,
) -> Buses:
    """Discover handlers under ``base_package`` and wire them into live buses.

    Args:
        base_package: Importable package to scan for ``commands``/``queries``
            handler modules (e.g. ``"myapp.handlers"``).
        dependencies: Map of dependency type -> instance, matched against each
            discovered handler's ``__init__`` annotations by type (with Union
            unwrapping and subclass fallback) and injected.
        strict: When True, discovery re-raises import/processing errors instead
            of logging and skipping the offending module.
        on_dispatch: Optional callback invoked after every dispatch on both
            buses with ``(message_name, duration_seconds, exception | None)``.

    Returns:
        A :class:`Buses` holding the assembled command, query, and event buses.

    Raises:
        MissingDependencyError: A handler requires a dependency not present in
            ``dependencies``, or cannot be instantiated.
        DuplicateHandlerError: Two handlers target the same command or query.
    """
    deps = dependencies or {}
    registry = HandlerDiscovery(base_package, strict=strict).discover_all_handlers()
    resolver = DependencyResolver()

    command_bus = CommandBus(on_dispatch=on_dispatch)
    _wire(registry.get_all_command_handlers(), resolver, deps, command_bus.register)

    query_bus = QueryBus(on_dispatch=on_dispatch)
    _wire(registry.get_all_query_handlers(), resolver, deps, query_bus.register)

    event_bus = EventBus(on_dispatch=on_dispatch)
    _wire(registry.get_all_event_handlers(), resolver, deps, event_bus.subscribe)

    return Buses(command_bus=command_bus, query_bus=query_bus, event_bus=event_bus)
