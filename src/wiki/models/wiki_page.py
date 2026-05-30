from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class WikiPage:
    name: str
    path: Path

    @property
    def title(self) -> str:
        return self.name.replace("-", " ").replace("_", " ").title()