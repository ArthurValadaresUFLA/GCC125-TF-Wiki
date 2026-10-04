"""Tests for wiki.repository."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import write_tree
from wiki.exceptions import ConfigurationError, ContentNotFoundError
from wiki.repository import FileSystemRepository


@pytest.fixture
def repo(content_dir: Path, workdir: Path) -> FileSystemRepository:
    write_tree(
        content_dir,
        {
            "b.md": "# B",
            "A.md": "# A",
            "guide/x.md": "# X",
            "data/t.csv": "a,b\n",
            ".env": "SECRET=1",
            ".git/config": "[core]",
            ".hidden/y.md": "# Y",
            "bom.md": b"\xef\xbb\xbf# With BOM",
        },
    )
    write_tree(workdir, {"outside.txt": "secret outside the root"})
    return FileSystemRepository(content_dir)


class TestFileSystemRepository:
    """Listing, reading, and path-safety rules."""

    def test_missing_root_raises_configuration_error(self, workdir: Path) -> None:
        with pytest.raises(ConfigurationError):
            FileSystemRepository(workdir / "does-not-exist")

    def test_lists_visible_files_sorted_by_folder_then_name(
        self, repo: FileSystemRepository
    ) -> None:
        names = [f.name for f in repo.list_files()]
        assert names == ["A.md", "b.md", "bom.md", "data/t.csv", "guide/x.md"]

    @pytest.mark.parametrize("name", [".env", ".git/config", ".hidden/y.md", "guide/../.env"])
    def test_hidden_files_and_folders_are_never_exposed(
        self, repo: FileSystemRepository, name: str
    ) -> None:
        with pytest.raises(ContentNotFoundError):
            repo.path_of(name)

    @pytest.mark.parametrize(
        "name", ["../outside.txt", "guide/../../outside.txt", "/etc/passwd", "", "a\x00b"]
    )
    def test_rejects_path_traversal_and_absolute_paths(
        self, repo: FileSystemRepository, name: str
    ) -> None:
        with pytest.raises(ContentNotFoundError):
            repo.path_of(name)

    def test_symlink_escaping_root_is_rejected_and_not_listed(
        self, repo: FileSystemRepository, content_dir: Path, workdir: Path
    ) -> None:
        (content_dir / "shortcut.txt").symlink_to(workdir / "outside.txt")
        with pytest.raises(ContentNotFoundError):
            repo.path_of("shortcut.txt")
        assert "shortcut.txt" not in [f.name for f in repo.list_files()]

    def test_symlink_inside_root_is_allowed(
        self, repo: FileSystemRepository, content_dir: Path
    ) -> None:
        (content_dir / "alias.md").symlink_to(content_dir / "b.md")
        assert repo.read_text("alias.md") == "# B"

    def test_broken_symlink_is_ignored(self, repo: FileSystemRepository, content_dir: Path) -> None:
        (content_dir / "broken.md").symlink_to(content_dir / "gone.md")
        assert "broken.md" not in [f.name for f in repo.list_files()]

    def test_directories_are_not_files(self, repo: FileSystemRepository) -> None:
        with pytest.raises(ContentNotFoundError):
            repo.path_of("guide")

    def test_read_text_strips_bom(self, repo: FileSystemRepository) -> None:
        assert repo.read_text("bom.md") == "# With BOM"

    def test_stat_reports_size_and_normalized_name(self, repo: FileSystemRepository) -> None:
        info = repo.stat("guide/x.md")
        assert info.name == "guide/x.md"
        assert info.size == len(b"# X")
        assert info.modified.tzinfo is not None
