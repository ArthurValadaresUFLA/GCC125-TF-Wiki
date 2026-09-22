"""Testes de wiki.service, usando um repositório em memória (injeção de dependência)."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path

from wiki.exceptions import ContentNotFoundError
from wiki.models import Download, Page, SourceFile
from wiki.rendering import CachedRenderer, MarkdownItRenderer
from wiki.repository import ContentRepository
from wiki.service import WikiService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class InMemoryRepository(ContentRepository):
    """Repositório de teste: o "sistema de arquivos" é um dicionário."""

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


class WikiServiceTests(unittest.TestCase):
    """Casos de uso da camada de serviço."""

    def setUp(self) -> None:
        self.service = WikiService(
            InMemoryRepository(
                {
                    "inicio.md": "# Início\n\ntexto",
                    "sem-titulo.md": "apenas texto",
                    "guia/dica_rapida.md": "conteúdo",
                    "dados/tabela.csv": "a,b",
                    "foo.md": "# Página foo",
                    "foo": "arquivo sem extensão chamado foo",
                }
            ),
            CachedRenderer(MarkdownItRenderer()),
        )

    def test_catalog_splits_pages_and_files(self) -> None:
        catalog = self.service.catalog()
        self.assertEqual(
            sorted(p.slug for p in catalog.pages),
            ["foo", "guia/dica_rapida", "inicio", "sem-titulo"],
        )
        self.assertEqual(sorted(f.name for f in catalog.files), ["dados/tabela.csv", "foo"])

    def test_catalog_titles_use_h1_or_humanized_slug(self) -> None:
        titles = {p.slug: p.title for p in self.service.catalog().pages}
        self.assertEqual(titles["inicio"], "Início")
        self.assertEqual(titles["sem-titulo"], "Sem titulo")
        self.assertEqual(titles["guia/dica_rapida"], "Dica rapida")

    def test_page_groups_put_root_first(self) -> None:
        groups = self.service.catalog().page_groups()
        self.assertEqual([folder for folder, _ in groups], ["", "guia"])

    def test_get_page(self) -> None:
        page = self.service.get_page("inicio")
        self.assertEqual(page.info.title, "Início")
        self.assertEqual(page.info.source_name, "inicio.md")
        self.assertIn("<p>texto</p>", page.document.html)

    def test_get_page_missing(self) -> None:
        with self.assertRaises(ContentNotFoundError):
            self.service.get_page("nao-existe")

    def test_get_download(self) -> None:
        download = self.service.get_download("dados/tabela.csv")
        self.assertEqual(download.filename, "tabela.csv")

    def test_resolve_prefers_page_over_file(self) -> None:
        self.assertIsInstance(self.service.resolve("foo"), Page)

    def test_resolve_falls_back_to_download(self) -> None:
        self.assertIsInstance(self.service.resolve("dados/tabela.csv"), Download)
        # com extensão, o .md é baixado em vez de exibido
        resource = self.service.resolve("inicio.md")
        self.assertIsInstance(resource, Download)
        assert isinstance(resource, Download)
        self.assertEqual(resource.filename, "inicio.md")

    def test_resolve_missing(self) -> None:
        with self.assertRaises(ContentNotFoundError):
            self.service.resolve("nada")


if __name__ == "__main__":
    unittest.main()
