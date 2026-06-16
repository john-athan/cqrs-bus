# cqrs-bus

An async CQRS command/query bus for Python with handler auto-discovery.

The idea is simple: your app dispatches commands and queries without knowing anything about what handles them. Handlers live in their own modules, get picked up automatically at startup, and dependencies are resolved from their `__init__` signatures. No decorators, no registries you have to maintain by hand.

## Installation

```bash
pip install cqrs-bus
```

With Prometheus metrics:

```bash
pip install "cqrs-bus[prometheus]"
```

## Quick start

Define a command and its handler:

```python
from dataclasses import dataclass

from cqrs_bus import Command, CommandHandler

@dataclass
class CreateOrder(Command):
    customer_id: str
    total: float

class CreateOrderHandler(CommandHandler[CreateOrder, str]):
    def __init__(self, db: Database):
        self.db = db

    async def handle(self, command: CreateOrder) -> str:
        order_id = await self.db.insert_order(command.customer_id, command.total)
        return order_id
```

`Command` and `Query` are plain marker base classes — they carry no fields of
their own. Give your messages data however you like; `@dataclass` is the
zero-dependency default, but Pydantic or `attrs` models work just as well.
`CommandHandler[TCommand, TResult]` is parameterized by both the message type
it handles and the type it returns.

### Typed dispatch

Parameterize the message with its result type — `Command[str]`, `Query[Order]`
— and `dispatch` is statically typed end to end, so type checkers infer the
return type with no casts:

```python
@dataclass
class CreateOrder(Command[str]):   # this command resolves to a str
    customer_id: str
    total: float

order_id = await bus.dispatch(CreateOrder(...))  # inferred as str
```

The parameter is optional; an unparameterized `Command` simply dispatches to
`Any`.

Wire it up and dispatch:

```python
from cqrs_bus import CommandBus

bus = CommandBus()
bus.register(CreateOrder, CreateOrderHandler(db=my_db))

order_id = await bus.dispatch(CreateOrder(customer_id="c-123", total=49.99))
```

Queries work the same way, just using `Query` and `QueryHandler` instead.

## Auto-discovery

If you have more than a handful of handlers, use `HandlerDiscovery` instead of registering them manually. Point it at your handlers package and it scans for all concrete `CommandHandler` and `QueryHandler` subclasses:

```
myapp/
  handlers/
    commands/
      create_order.py   # contains CreateOrderHandler
      cancel_order.py   # contains CancelOrderHandler
    queries/
      get_order.py      # contains GetOrderHandler
```

The one-liner is `build_buses`. Point it at your handlers package, hand it the
shared dependencies your handlers need, and it returns ready-to-use buses:

```python
from cqrs_bus import build_buses

buses = build_buses("myapp.handlers", dependencies={"db": my_db})

order_id = await buses.command_bus.dispatch(CreateOrder(customer_id="c-123", total=49.99))
order = await buses.query_bus.dispatch(GetOrder(order_id=order_id))
```

Dependencies are injected by **parameter name**: a handler whose `__init__`
takes `db: Database` receives whatever you passed as `dependencies["db"]`.
Missing dependencies raise `MissingDependencyError` at build time, not on first
dispatch.

### Lower-level building blocks

If you have your own DI container and want to control instantiation, drop down
to `HandlerDiscovery` (which finds handlers) and the bus `register` methods:

```python
from cqrs_bus import HandlerDiscovery, CommandBus, QueryBus

registry = HandlerDiscovery(base_package="myapp.handlers").discover_all_handlers()

command_bus = CommandBus()
for meta in registry.get_all_command_handlers():
    deps = {name: my_container.resolve(dep) for name, dep in meta.dependencies.items()}
    command_bus.register(meta.command_or_query_type, meta.handler_class(**deps))

query_bus = QueryBus()
for meta in registry.get_all_query_handlers():
    deps = {name: my_container.resolve(dep) for name, dep in meta.dependencies.items()}
    query_bus.register(meta.command_or_query_type, meta.handler_class(**deps))
```

Handler dependencies are inferred from type annotations in `__init__`. The `DependencyResolver` inspects each handler class and returns a `{param_name: type}` dict that you can use with whatever DI container or factory you already have.

## Middleware

Wrap every dispatch with cross-cutting behavior — validation, transactions,
retries, logging, auth — using an onion-style pipeline. A middleware receives
the message and a `call_next` continuation; it can inspect or replace the
message, short-circuit, transform the result, or catch errors:

```python
async def transactional(message, call_next):
    async with db.transaction():
        return await call_next(message)

async def timing(message, call_next):
    start = time.monotonic()
    try:
        return await call_next(message)
    finally:
        metrics.observe(type(message).__name__, time.monotonic() - start)

bus = CommandBus(middleware=[timing])   # or bus.add_middleware(...)
bus.add_middleware(transactional)
```

Middlewares run **outermost-first**: the first one added sees the message
before — and the result after — every middleware added later. Both `CommandBus`
and `QueryBus` support them (they share the same `MessageBus` base), and the
`on_dispatch` callback and metrics measure the whole pipeline, middleware
included.

## Observability

The bus logs at `DEBUG` for normal dispatches and `INFO` for anything that takes over a second. It logs at `ERROR` with full traceback on handler failures. All log records include `command_type` and `command_id` (a UUID generated per dispatch) as structured extras.

If `prometheus-client` is installed, the bus automatically tracks:

- `command_executions_total` / `query_executions_total`
- `command_duration_seconds` / `query_duration_seconds`
- `command_errors_total` / `query_errors_total`

No setup required — the metrics are registered on import.

You can also pass an `on_dispatch` callback to the bus constructor if you want to hook into your own telemetry:

```python
def my_hook(name: str, duration: float, error: Exception | None):
    ...

bus = CommandBus(on_dispatch=my_hook)
```

## Requirements

Python 3.11+. No runtime dependencies unless you opt into the `prometheus` extra.

## License

MIT
