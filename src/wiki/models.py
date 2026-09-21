"""Modelos de domínio: objetos de valor imutáveis trocados entre as camadas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from pathlib import Path

MARKDOWN_SUFFIX = ".md"
"""Extensão (em minúsculas) que identifica um arquivo como página."""


def is_markdown(name: str) -> bool:
    """Diz se o nome de arquivo corresponde a uma página Markdown."""
    return name.endswith(MARKDOWN_SUFFIX)


def slug_for(name: str) -> str:
    """Converte o nome de um arquivo Markdown no *slug* usado na URL.

    Example:
        ``"guia/instalacao.md"`` vira ``"guia/instalacao"``.
    """
    return name[: -len(MARKDOWN_SUFFIX)] if is_markdown(name) else name


def source_name_for(slug: str) -> str:
    """Operação inversa de :func:`slug_for`: ``"guia/x"`` vira ``"guia/x.md"``."""
    return slug + MARKDOWN_SUFFIX


def humanize(slug: str) -> str:
    """Gera um título legível a partir do slug, para páginas sem ``# Título``."""
    stem = slug.rpartition("/")[2]
    words = stem.replace("-", " ").replace("_", " ").strip()
    return words[:1].upper() + words[1:] if words else slug


@dataclass(frozen=True, slots=True)
class SourceFile:
    """Metadados de um arquivo visível na pasta de conteúdo.

    Attributes:
        name: Caminho relativo à raiz, sempre com ``/`` como separador.
        size: Tamanho em bytes.
        modified: Data da última modificação (UTC).
    """

    name: str
    size: int
    modified: datetime


@dataclass(frozen=True, slots=True)
class TocEntry:
    """Um item do índice ("Nesta página") de um documento.

    Attributes:
        level: Nível do título (1 a 6).
        title: Texto do título, sem marcação.
        anchor: Identificador usado no fragmento da URL (``#anchor``).
    """

    level: int
    title: str
    anchor: str


@dataclass(frozen=True, slots=True)
class RenderedDocument:
    """Resultado da conversão de Markdown para HTML.

    Attributes:
        html: Corpo do documento em HTML.
        title: Texto do primeiro ``# Título`` ou ``None`` se não houver.
        toc: Títulos do documento, na ordem em que aparecem.
    """

    html: str
    title: str | None
    toc: tuple[TocEntry, ...]


@dataclass(frozen=True, slots=True)
class PageInfo:
    """Resumo de uma página, usado no índice.

    Attributes:
        slug: Identificador na URL (sem a extensão ``.md``).
        title: Título exibido.
        source_name: Nome do arquivo de origem, relativo à raiz.
        size: Tamanho do arquivo em bytes.
        modified: Data da última modificação (UTC).
    """

    slug: str
    title: str
    source_name: str
    size: int
    modified: datetime

    @property
    def folder(self) -> str:
        """Pasta que contém a página (``""`` para a raiz)."""
        return self.slug.rpartition("/")[0]


@dataclass(frozen=True, slots=True)
class FileInfo:
    """Resumo de um arquivo que não é Markdown e fica disponível para download.

    Attributes:
        name: Caminho relativo à raiz.
        size: Tamanho em bytes.
        modified: Data da última modificação (UTC).
    """

    name: str
    size: int
    modified: datetime


@dataclass(frozen=True, slots=True)
class Catalog:
    """Tudo o que a pasta de conteúdo publica: páginas e arquivos para download.

    Attributes:
        pages: Páginas Markdown.
        files: Demais arquivos.
    """

    pages: tuple[PageInfo, ...]
    files: tuple[FileInfo, ...]

    def page_groups(self) -> tuple[tuple[str, tuple[PageInfo, ...]], ...]:
        """Agrupa as páginas por pasta, preservando a ordem interna de cada grupo.

        Returns:
            Tuplas ``(pasta, páginas)``; a raiz (``""``) vem primeiro.
        """
        ordered = sorted(self.pages, key=lambda page: page.folder.casefold())
        return tuple(
            (folder, tuple(items))
            for folder, items in groupby(ordered, key=lambda page: page.folder)
        )


@dataclass(frozen=True, slots=True)
class Page:
    """Uma página completa, pronta para ser exibida.

    Attributes:
        info: Metadados da página.
        document: Conteúdo já convertido em HTML.
    """

    info: PageInfo
    document: RenderedDocument


@dataclass(frozen=True, slots=True)
class Download:
    """Um arquivo a ser enviado ao cliente como anexo.

    Attributes:
        path: Caminho absoluto, já validado, no sistema de arquivos.
        filename: Nome sugerido para salvar o arquivo.
    """

    path: Path
    filename: str


Resource = Page | Download
"""O que uma URL pode resolver: uma página renderizada ou um arquivo para baixar."""
