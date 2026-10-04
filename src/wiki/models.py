"""Domain models: immutable value objects passed between layers.

None of these types know anything about Flask, the filesystem, or Markdown — they are
plain data plus a handful of pure helper functions, which keeps :mod:`wiki.service`
easy to unit-test with an in-memory repository (see ``tests/test_service.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from pathlib import Path

MARKDOWN_SUFFIX = ".md"
"""Lower-case extension that identifies a file as a page."""


def is_markdown(name: str) -> bool:
    """Return whether the filename corresponds to a Markdown page."""
    return name.endswith(MARKDOWN_SUFFIX)


def slug_for(name: str) -> str:
    """Convert a Markdown filename into the slug used in the URL.

    Example:
        ``"guia/instalacao.md"`` becomes ``"guia/instalacao"``.
    """
    return name[: -len(MARKDOWN_SUFFIX)] if is_markdown(name) else name


def source_name_for(slug: str) -> str:
    """Reverse of :func:`slug_for`: ``"guia/x"`` becomes ``"guia/x.md"``."""
    return slug + MARKDOWN_SUFFIX


def humanize(slug: str) -> str:
    """Derive a readable title from a slug, for pages with no ``# Title`` heading.

    Only the final path segment is used (so ``"guia/dica_rapida"`` yields
    ``"Dica rapida"``, not ``"Guia dica rapida"``), underscores and hyphens become
    spaces, and the first letter is capitalised.
    """
    stem = slug.rpartition("/")[2]
    words = stem.replace("-", " ").replace("_", " ").strip()
    return words[:1].upper() + words[1:] if words else slug


@dataclass(frozen=True, slots=True)
class SourceFile:
    """Metadata for a file visible in the content folder.

    Attributes:
        name: Path relative to the content root, always using ``/`` as the separator
            (even on Windows), so slugs and URLs stay platform-independent.
        size: Size in bytes.
        modified: Last-modified timestamp, in UTC.
    """

    name: str
    size: int
    modified: datetime


@dataclass(frozen=True, slots=True)
class TocEntry:
    """A single entry in a document's table of contents ("On this page").

    Attributes:
        level: Heading level, from 1 (``#``) to 6 (``######``).
        title: Plain-text heading, with any Markdown inline formatting stripped.
        anchor: Identifier used in the URL fragment (``#anchor``); see
            :func:`wiki.rendering.slugify` for how it is derived, and how collisions
            between identically worded headings are disambiguated.
    """

    level: int
    title: str
    anchor: str


@dataclass(frozen=True, slots=True)
class RenderedDocument:
    """The result of converting Markdown into HTML.

    Attributes:
        html: The document body, as HTML.
        title: Text of the first ``# Heading``, or ``None`` if the document has none —
            in which case callers typically fall back to :func:`humanize`.
        toc: The document's headings, in the order they appear in the source text.
    """

    html: str
    title: str | None
    toc: tuple[TocEntry, ...]


@dataclass(frozen=True, slots=True)
class PageInfo:
    """Summary of a page, as shown in the index.

    Attributes:
        slug: Identifier used in the URL (without the ``.md`` extension).
        title: Title displayed to the reader.
        source_name: Name of the underlying source file, relative to the content root.
        size: Size of the source file, in bytes.
        modified: Last-modified timestamp of the source file, in UTC.
    """

    slug: str
    title: str
    source_name: str
    size: int
    modified: datetime

    @property
    def folder(self) -> str:
        """Folder that contains this page (``""`` for the content root)."""
        return self.slug.rpartition("/")[0]


@dataclass(frozen=True, slots=True)
class FileInfo:
    """Summary of a non-Markdown file made available for download.

    Attributes:
        name: Path relative to the content root.
        size: Size in bytes.
        modified: Last-modified timestamp, in UTC.
    """

    name: str
    size: int
    modified: datetime


@dataclass(frozen=True, slots=True)
class Catalog:
    """Everything the content folder publishes: pages and downloadable files.

    Attributes:
        pages: Markdown pages.
        files: Every other file.
    """

    pages: tuple[PageInfo, ...]
    files: tuple[FileInfo, ...]

    def page_groups(self) -> tuple[tuple[str, tuple[PageInfo, ...]], ...]:
        """Group the pages by folder, preserving each group's internal order.

        Sorting is case-insensitive and folder names are compared with
        :meth:`str.casefold`, so ``"Guia"`` and ``"guia"`` end up in the same group.
        The content root (``""``) always sorts first, since it casefolds to the empty
        string, which precedes any non-empty folder name.

        Returns:
            ``(folder, pages)`` tuples, with the content root first.
        """
        ordered = sorted(self.pages, key=lambda page: page.folder.casefold())
        return tuple(
            (folder, tuple(items))
            for folder, items in groupby(ordered, key=lambda page: page.folder)
        )


@dataclass(frozen=True, slots=True)
class Page:
    """A complete page, ready to be displayed.

    Attributes:
        info: The page's metadata.
        document: Its content, already converted to HTML.
    """

    info: PageInfo
    document: RenderedDocument


@dataclass(frozen=True, slots=True)
class Download:
    """A file to be sent to the client as an attachment.

    Attributes:
        path: Absolute, already-validated path on the filesystem — see
            :meth:`wiki.repository.FileSystemRepository.path_of` for the security
            checks applied before this value is ever constructed.
        filename: Filename suggested to the browser when saving.
    """

    path: Path
    filename: str


Resource = Page | Download
"""What a URL can resolve to: either a rendered page or a downloadable file."""
