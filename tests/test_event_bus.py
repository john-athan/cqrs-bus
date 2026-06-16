"""Tests for the EventBus pub/sub semantics."""

import logging

from cqrs_bus import Event, EventBus, EventHandler


class Thing(Event):
    def __init__(self, value: str = "x"):
        self.value = value


class OtherThing(Event):
    pass


class TestSubscribe:
    def test_handler_count_starts_at_zero(self):
        bus = EventBus()
        assert bus.handler_count(Thing) == 0

    def test_subscribe_increments_count(self):
        bus = EventBus()

        class H(EventHandler[Thing]):
            async def handle(self, event: Thing) -> None: ...

        bus.subscribe(Thing, H())
        bus.subscribe(Thing, H())
        assert bus.handler_count(Thing) == 2


class TestPublish:
    async def test_invokes_single_subscriber(self):
        seen: list[str] = []

        class H(EventHandler[Thing]):
            async def handle(self, event: Thing) -> None:
                seen.append(event.value)

        bus = EventBus()
        bus.subscribe(Thing, H())
        await bus.publish(Thing(value="hello"))
        assert seen == ["hello"]

    async def test_fans_out_to_all_subscribers(self):
        seen: list[str] = []

        def make(tag: str):
            class H(EventHandler[Thing]):
                async def handle(self, event: Thing) -> None:
                    seen.append(tag)

            return H()

        bus = EventBus()
        bus.subscribe(Thing, make("a"))
        bus.subscribe(Thing, make("b"))
        await bus.publish(Thing())
        assert set(seen) == {"a", "b"}

    async def test_no_subscribers_is_a_noop(self):
        bus = EventBus()
        await bus.publish(Thing())  # must not raise

    async def test_only_matching_type_is_invoked(self):
        seen: list[str] = []

        class H(EventHandler[Thing]):
            async def handle(self, event: Thing) -> None:
                seen.append("thing")

        bus = EventBus()
        bus.subscribe(Thing, H())
        await bus.publish(OtherThing())
        assert seen == []


class TestErrorIsolation:
    async def test_one_failure_does_not_block_others_and_publish_does_not_raise(self, caplog):
        survived: list[str] = []

        class Boom(EventHandler[Thing]):
            async def handle(self, event: Thing) -> None:
                raise RuntimeError("boom")

        class Ok(EventHandler[Thing]):
            async def handle(self, event: Thing) -> None:
                survived.append("ok")

        bus = EventBus()
        bus.subscribe(Thing, Boom())
        bus.subscribe(Thing, Ok())

        with caplog.at_level(logging.ERROR, logger="cqrs_bus.events.event_bus"):
            await bus.publish(Thing())  # does not raise

        assert survived == ["ok"]
        assert any("failed" in r.message for r in caplog.records)


class TestOnDispatch:
    async def test_callback_invoked_with_no_error_on_success(self):
        calls: list[tuple] = []

        class H(EventHandler[Thing]):
            async def handle(self, event: Thing) -> None: ...

        bus = EventBus(on_dispatch=lambda n, d, e: calls.append((n, d, e)))
        bus.subscribe(Thing, H())
        await bus.publish(Thing())

        assert len(calls) == 1
        name, duration, exc = calls[0]
        assert name == "Thing"
        assert isinstance(duration, float)
        assert exc is None

    async def test_callback_receives_error_when_a_subscriber_fails(self):
        calls: list[tuple] = []

        class Boom(EventHandler[Thing]):
            async def handle(self, event: Thing) -> None:
                raise ValueError("nope")

        bus = EventBus(on_dispatch=lambda n, d, e: calls.append((n, d, e)))
        bus.subscribe(Thing, Boom())
        await bus.publish(Thing())

        assert len(calls) == 1
        assert isinstance(calls[0][2], ValueError)
