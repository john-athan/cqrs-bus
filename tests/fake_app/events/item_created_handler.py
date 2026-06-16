from dataclasses import dataclass

from cqrs_bus import Event, EventHandler

# Module-level sink so tests can observe that subscribers actually ran.
RECORDED: list[str] = []


@dataclass
class ItemCreated(Event):
    name: str


class LogItemCreated(EventHandler[ItemCreated]):
    async def handle(self, event: ItemCreated) -> None:
        RECORDED.append(f"log:{event.name}")


class NotifyItemCreated(EventHandler[ItemCreated]):
    async def handle(self, event: ItemCreated) -> None:
        RECORDED.append(f"notify:{event.name}")
