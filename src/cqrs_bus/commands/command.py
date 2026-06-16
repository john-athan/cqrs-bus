from abc import ABC, abstractmethod
from typing import Generic, TypeVar


class Command(ABC):
    """Marker base class for commands (state-changing intents).

    Carries no fields of its own — subclass it and add data with ``@dataclass``,
    Pydantic, ``attrs``, or whatever you prefer.
    """


TCommand = TypeVar("TCommand", bound=Command)
TResult = TypeVar("TResult")


class CommandHandler(ABC, Generic[TCommand, TResult]):
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        pass
