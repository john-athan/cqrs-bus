"""Tests for the public build_buses() bootstrap wiring."""

import pytest

from cqrs_bus import Buses, MissingDependencyError, build_buses
from fake_app.commands.create_item_handler import CreateItemCommand
from fake_app.events.item_created_handler import RECORDED, ItemCreated
from fake_app.queries.get_item_handler import GetItemQuery
from fake_app.shared.commands.shared_command_handler import SharedCommand
from fake_app_di.commands.save_handler import Repo, SaveCommand


class TestBuildBuses:
    def test_returns_buses_with_both_buses(self):
        buses = build_buses("fake_app")
        assert isinstance(buses, Buses)
        assert buses.command_bus is not None
        assert buses.query_bus is not None

    async def test_command_dispatch_works(self):
        buses = build_buses("fake_app")
        assert await buses.command_bus.dispatch(CreateItemCommand(name="widget")) == "created:widget"
        assert await buses.command_bus.dispatch(SharedCommand(data="hi")) == "shared:hi"

    async def test_query_dispatch_works(self):
        buses = build_buses("fake_app")
        assert await buses.query_bus.dispatch(GetItemQuery(item_id=42)) == "item:42"

    def test_registers_all_discovered_handlers(self):
        buses = build_buses("fake_app")
        assert len(buses.command_bus._handlers) == 2
        assert len(buses.query_bus._handlers) == 1
        # Two event handlers subscribe to ItemCreated.
        assert buses.event_bus.handler_count(ItemCreated) == 2

    async def test_event_publish_fans_out_to_all_subscribers(self):
        buses = build_buses("fake_app")
        RECORDED.clear()
        await buses.event_bus.publish(ItemCreated(name="widget"))
        assert set(RECORDED) == {"log:widget", "notify:widget"}

    async def test_injects_dependencies(self):
        buses = build_buses("fake_app_di", {"repo": Repo()})
        assert await buses.command_bus.dispatch(SaveCommand(value="x")) == "saved:x"

    def test_missing_dependency_raises(self):
        with pytest.raises(MissingDependencyError):
            build_buses("fake_app_di", {})

    async def test_on_dispatch_wired_to_both_buses(self):
        calls: list[str] = []

        def on_dispatch(name: str, duration: float, exc: Exception | None) -> None:
            calls.append(name)

        buses = build_buses("fake_app", on_dispatch=on_dispatch)
        await buses.command_bus.dispatch(CreateItemCommand(name="w"))
        await buses.query_bus.dispatch(GetItemQuery(item_id=1))

        assert calls == ["CreateItemCommand", "GetItemQuery"]
