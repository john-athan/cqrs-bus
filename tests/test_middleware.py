"""Tests for the bus middleware pipeline (shared across command and query buses)."""

from cqrs_bus import Command, CommandBus, CommandHandler, Query, QueryBus, QueryHandler


class Ping(Command[str]):
    pass


class PingHandler(CommandHandler[Ping, str]):
    async def handle(self, command: Ping) -> str:
        return "pong"


def _make_bus() -> CommandBus:
    bus = CommandBus()
    bus.register(Ping, PingHandler())
    return bus


class TestMiddleware:
    async def test_wraps_handler_before_and_after(self):
        calls: list[str] = []
        bus = _make_bus()

        async def mw(message, call_next):
            calls.append("before")
            result = await call_next(message)
            calls.append("after")
            return result

        bus.add_middleware(mw)
        assert await bus.dispatch(Ping()) == "pong"
        assert calls == ["before", "after"]

    async def test_runs_outermost_first(self):
        calls: list[str] = []
        bus = _make_bus()

        def make(label: str):
            async def mw(message, call_next):
                calls.append(f"{label}:in")
                result = await call_next(message)
                calls.append(f"{label}:out")
                return result

            return mw

        bus.add_middleware(make("A"))
        bus.add_middleware(make("B"))
        await bus.dispatch(Ping())
        assert calls == ["A:in", "B:in", "B:out", "A:out"]

    async def test_can_short_circuit(self):
        bus = _make_bus()

        async def block(message, call_next):
            return "blocked"

        bus.add_middleware(block)
        assert await bus.dispatch(Ping()) == "blocked"

    async def test_can_transform_result(self):
        bus = _make_bus()

        async def upper(message, call_next):
            return (await call_next(message)).upper()

        bus.add_middleware(upper)
        assert await bus.dispatch(Ping()) == "PONG"

    async def test_can_catch_handler_errors(self):
        class Boom(Command[str]):
            pass

        class BoomHandler(CommandHandler[Boom, str]):
            async def handle(self, command: Boom) -> str:
                raise RuntimeError("kaboom")

        bus = CommandBus()
        bus.register(Boom, BoomHandler())

        async def swallow(message, call_next):
            try:
                return await call_next(message)
            except RuntimeError:
                return "recovered"

        bus.add_middleware(swallow)
        assert await bus.dispatch(Boom()) == "recovered"

    async def test_constructor_accepts_middleware(self):
        calls: list[str] = []

        async def mw(message, call_next):
            calls.append("mw")
            return await call_next(message)

        bus = CommandBus(middleware=[mw])
        bus.register(Ping, PingHandler())
        await bus.dispatch(Ping())
        assert calls == ["mw"]

    async def test_query_bus_supports_middleware(self):
        class GetAnswer(Query[int]):
            pass

        class AnswerHandler(QueryHandler[GetAnswer, int]):
            async def handle(self, query: GetAnswer) -> int:
                return 42

        seen: list[int] = []
        bus = QueryBus()
        bus.register(GetAnswer, AnswerHandler())

        async def mw(message, call_next):
            seen.append(1)
            return await call_next(message)

        bus.add_middleware(mw)
        assert await bus.dispatch(GetAnswer()) == 42
        assert seen == [1]
