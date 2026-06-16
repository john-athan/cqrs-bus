from dataclasses import dataclass

from cqrs_bus import Command, CommandHandler


class Repo:
    """A stand-in dependency injected into the handler."""

    def save(self, value: str) -> str:
        return f"saved:{value}"


@dataclass
class SaveCommand(Command):
    value: str


class SaveHandler(CommandHandler[SaveCommand, str]):
    def __init__(self, repo: Repo):
        self.repo = repo

    async def handle(self, command: SaveCommand) -> str:
        return self.repo.save(command.value)
