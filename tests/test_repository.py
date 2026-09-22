"""Testes de wiki.repository."""

from __future__ import annotations

import unittest

from tests.helpers import ContentDirTestCase, write_tree
from wiki.exceptions import ConfigurationError, ContentNotFoundError
from wiki.repository import FileSystemRepository


class FileSystemRepositoryTests(ContentDirTestCase):
    """Listagem, leitura e regras de segurança de caminhos."""

    def setUp(self) -> None:
        super().setUp()
        write_tree(
            self.content,
            {
                "b.md": "# B",
                "A.md": "# A",
                "guia/x.md": "# X",
                "dados/t.csv": "a,b\n",
                ".env": "SEGREDO=1",
                ".git/config": "[core]",
                ".oculta/y.md": "# Y",
                "bom.md": b"\xef\xbb\xbf# Com BOM",
            },
        )
        write_tree(self.workdir, {"fora.txt": "segredo fora da raiz"})
        self.repo = FileSystemRepository(self.content)

    def test_missing_root_raises_configuration_error(self) -> None:
        with self.assertRaises(ConfigurationError):
            FileSystemRepository(self.workdir / "nao-existe")

    def test_lists_visible_files_sorted_by_folder_then_name(self) -> None:
        names = [f.name for f in self.repo.list_files()]
        self.assertEqual(names, ["A.md", "b.md", "bom.md", "dados/t.csv", "guia/x.md"])

    def test_hidden_files_and_folders_are_never_exposed(self) -> None:
        for name in [".env", ".git/config", ".oculta/y.md", "guia/../.env"]:
            with self.subTest(name=name), self.assertRaises(ContentNotFoundError):
                self.repo.path_of(name)

    def test_rejects_path_traversal_and_absolute_paths(self) -> None:
        for name in ["../fora.txt", "guia/../../fora.txt", "/etc/passwd", "", "a\x00b"]:
            with self.subTest(name=name), self.assertRaises(ContentNotFoundError):
                self.repo.path_of(name)

    def test_symlink_escaping_root_is_rejected_and_not_listed(self) -> None:
        (self.content / "atalho.txt").symlink_to(self.workdir / "fora.txt")
        with self.assertRaises(ContentNotFoundError):
            self.repo.path_of("atalho.txt")
        self.assertNotIn("atalho.txt", [f.name for f in self.repo.list_files()])

    def test_symlink_inside_root_is_allowed(self) -> None:
        (self.content / "alias.md").symlink_to(self.content / "b.md")
        self.assertEqual(self.repo.read_text("alias.md"), "# B")

    def test_broken_symlink_is_ignored(self) -> None:
        (self.content / "quebrado.md").symlink_to(self.content / "sumiu.md")
        self.assertNotIn("quebrado.md", [f.name for f in self.repo.list_files()])

    def test_directories_are_not_files(self) -> None:
        with self.assertRaises(ContentNotFoundError):
            self.repo.path_of("guia")

    def test_read_text_strips_bom(self) -> None:
        self.assertEqual(self.repo.read_text("bom.md"), "# Com BOM")

    def test_stat_reports_size_and_normalized_name(self) -> None:
        info = self.repo.stat("guia/x.md")
        self.assertEqual(info.name, "guia/x.md")
        self.assertEqual(info.size, len(b"# X"))
        self.assertIsNotNone(info.modified.tzinfo)


if __name__ == "__main__":
    unittest.main()
