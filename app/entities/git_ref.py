from pathlib import Path
from typing import NamedTuple


class Ref(NamedTuple):
    name: str
    target: str

    def store(self, dot_git: Path) -> None:
        (dot_git / self.name).write_text(f"{self.target}\n")
