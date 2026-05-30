from pathlib import Path
from wiki.models.wiki_page import WikiPage
from wiki.interfaces import IWikiRepository


class FileWikiRepository(IWikiRepository):
    def __init__(self, wiki_dir: Path):
        self.wiki_dir = Path(wiki_dir)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)  # Garante que exista

    def get_by_name(self, name: str) -> WikiPage | None:
        path = self.wiki_dir / f"{name}.md"
        if not path.exists() or not path.is_file():
            return None
        return WikiPage(name=path.stem, path=path)

    def list_all(self) -> list[WikiPage]:
        return sorted(
            [
                WikiPage(name=file_path.stem, path=file_path)
                for file_path in self.wiki_dir.glob("*.md")
                if file_path.name != "index.md"
            ],
            key=lambda page: page.name,
        )

    def read(self, page: WikiPage) -> str:
        return page.path.read_text(encoding="utf-8")
