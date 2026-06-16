from abc import ABC, abstractmethod
from typing import Generic, TypeVar


class Event(ABC):
    """Marker base class for domain events (something that has happened).

    Carries no fields of its own — subclass it and add data with ``@dataclass``,
    Pydantic, ``attrs``, or whatever you prefer.

    Unlike a command or query, an event may have zero, one, or many subscribers,
    and handlers return nothing — they react to the event.
    """


TEvent = TypeVar("TEvent", bound=Event)


class EventHandler(ABC, Generic[TEvent]):
    @abstractmethod
    async def handle(self, event: TEvent) -> None:
        pass
