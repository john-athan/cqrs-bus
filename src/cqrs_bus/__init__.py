from cqrs_bus.bootstrap import Buses, build_buses
from cqrs_bus.bus import MessageBus, Middleware, Next
from cqrs_bus.commands.command import Command, CommandHandler, TCommand
from cqrs_bus.commands.command_bus import CommandBus
from cqrs_bus.discovery.dependency_resolver import DependencyResolver
from cqrs_bus.discovery.exceptions import (
    DuplicateHandlerError,
    HandlerDiscoveryError,
    InvalidHandlerError,
    MissingDependencyError,
)
from cqrs_bus.discovery.handler_discovery import HandlerDiscovery
from cqrs_bus.discovery.handler_registry import HandlerMetadata, HandlerRegistry
from cqrs_bus.events.event import Event, EventHandler, TEvent
from cqrs_bus.events.event_bus import EventBus
from cqrs_bus.queries.query import Query, QueryHandler, TQuery
from cqrs_bus.queries.query_bus import QueryBus
from typing import TypeVar

TResult = TypeVar("TResult")

__all__ = [
    "Buses",
    "build_buses",
    "Command",
    "CommandHandler",
    "CommandBus",
    "TCommand",
    "Query",
    "QueryHandler",
    "QueryBus",
    "TQuery",
    "Event",
    "EventHandler",
    "EventBus",
    "TEvent",
    "TResult",
    "HandlerDiscovery",
    "HandlerRegistry",
    "HandlerMetadata",
    "DependencyResolver",
    "MessageBus",
    "Middleware",
    "Next",
    "HandlerDiscoveryError",
    "MissingDependencyError",
    "DuplicateHandlerError",
    "InvalidHandlerError",
]
