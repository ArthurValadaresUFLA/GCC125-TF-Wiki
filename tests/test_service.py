"""Tests for wiki.service, using an in-memory repository (dependency injection)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from wiki.exceptions import ContentNotFoundError
from wiki.models import Download, Page, SourceFile
from wiki.rendering import CachedRenderer, MarkdownItRenderer
from wiki.repository import ContentRepository
from wiki.service import WikiService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class InMemoryRepository(ContentRepository):
    """Test repository: the "filesystem" is just a dictionary."""

    def __init__(self, files: dict[str, str]) -> None:
        self._files = files

    def list_files(self) -> tuple[SourceFile, ...]:
        return tuple(SourceFile(n, len(t), NOW) for n, t in sorted(self._files.items()))

    def stat(self, name: str) -> SourceFile:
        if name not in self._files:
            raise ContentNotFoundError(name)
        return SourceFile(name, len(self._files[name]), NOW)

    def read_text(self, name: str) -> str:
        if name not in self._files:
            raise ContentNotFoundError(name)
        return self._files[name]

    def path_of(self, name: str) -> Path:
        if name not in self._files:
            raise ContentNotFoundError(name)
        return Path("/virtual") / name


@pytest.fixture
def service() -> WikiService:
    return WikiService(
        InMemoryRepository(
            {
                "home.md": "# Home\n\ntext",
                "no-title.md": "just text",
                "guide/quick_tip.md": "content",
                "data/table.csv": "a,b",
                "foo.md": "# Foo page",
                "foo": "extensionless file called foo",
            }
        ),
        CachedRenderer(MarkdownItRenderer()),
    )


class TestWikiService:
    """Use cases in the service layer."""

    def test_catalog_splits_pages_and_files(self, service: WikiService) -> None:
        catalog = service.catalog()
        assert sorted(p.slug for p in catalog.pages) == [
            "foo",
            "guide/quick_tip",
            "home",
            "no-title",
        ]
        assert sorted(f.name for f in catalog.files) == ["data/table.csv", "foo"]

    def test_catalog_titles_use_h1_or_humanized_slug(self, service: WikiService) -> None:
        titles = {p.slug: p.title for p in service.catalog().pages}
        assert titles["home"] == "Home"
        assert titles["no-title"] == "No title"
        assert titles["guide/quick_tip"] == "Quick tip"

    def test_page_groups_put_root_first(self, service: WikiService) -> None:
        groups = service.catalog().page_groups()
        assert [folder for folder, _ in groups] == ["", "guide"]

    def test_get_page(self, service: WikiService) -> None:
        page = service.get_page("home")
        assert page.info.title == "Home"
        assert page.info.source_name == "home.md"
        assert "<p>text</p>" in page.document.html

    def test_get_page_missing(self, service: WikiService) -> None:
        with pytest.raises(ContentNotFoundError):
            service.get_page("does-not-exist")

    def test_get_download(self, service: WikiService) -> None:
        download = service.get_download("data/table.csv")
        assert download.filename == "table.csv"

    def test_resolve_prefers_page_over_file(self, service: WikiService) -> None:
        assert isinstance(service.resolve("foo"), Page)

    def test_resolve_falls_back_to_download(self, service: WikiService) -> None:
        assert isinstance(service.resolve("data/table.csv"), Download)
        # with the extension, the .md file is downloaded rather than rendered
        resource = service.resolve("home.md")
        assert isinstance(resource, Download)
        assert resource.filename == "home.md"

    def test_resolve_missing(self, service: WikiService) -> None:
        with pytest.raises(ContentNotFoundError):
            service.resolve("nothing")
