from abc import ABC, abstractmethod
from typing import Generic, TypeVar


class Query(ABC):
    """Marker base class for queries (read-only requests).

    Carries no fields of its own — subclass it and add data with ``@dataclass``,
    Pydantic, ``attrs``, or whatever you prefer.
    """


TQuery = TypeVar("TQuery", bound=Query)
TResult = TypeVar("TResult")


class QueryHandler(ABC, Generic[TQuery, TResult]):
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        pass
