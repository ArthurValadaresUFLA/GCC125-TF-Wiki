"""Service layer: orchestrates the repository and the renderer (*Facade* pattern).

HTTP routes talk only to :class:`WikiService`; they know nothing about the filesystem
or the Markdown engine underneath it. This keeps :mod:`wiki.views` thin and makes the
use cases below independently testable against an in-memory repository.
"""

from __future__ import annotations

from contextlib import suppress

from wiki.exceptions import ContentNotFoundError
from wiki.models import (
    Catalog,
    Download,
    FileInfo,
    Page,
    PageInfo,
    Resource,
    humanize,
    is_markdown,
    slug_for,
    source_name_for,
)
from wiki.rendering import Renderer
from wiki.repository import ContentRepository


class WikiService:
    """Use cases for the wiki: build the index, open a page, locate a download.

    Dependencies are injected through the constructor, which allows swapping the
    repository (e.g. for an in-memory one in tests) or the renderer without touching
    this class at all.

    Args:
        repository: Source of the content.
        renderer: Converter from Markdown to HTML.
    """

    def __init__(self, repository: ContentRepository, renderer: Renderer) -> None:
        self._repository = repository
        self._renderer = renderer

    def catalog(self) -> Catalog:
        """Build the index: Markdown pages on one side, every other file on the other.

        A page whose file disappears between :meth:`~wiki.repository.ContentRepository.list_files`
        and the subsequent read is silently skipped rather than raising, since that
        race is expected under normal filesystem activity and should not break the
        whole index for the sake of one page.

        Returns:
            The catalogue of all currently visible content.
        """
        pages: list[PageInfo] = []
        files: list[FileInfo] = []
        for source in self._repository.list_files():
            if not is_markdown(source.name):
                files.append(FileInfo(source.name, source.size, source.modified))
                continue
            try:
                text = self._repository.read_text(source.name)
            except ContentNotFoundError:
                continue  # removed between listing and reading
            slug = slug_for(source.name)
            pages.append(
                PageInfo(
                    slug=slug,
                    title=self._renderer.title(text) or humanize(slug),
                    source_name=source.name,
                    size=source.size,
                    modified=source.modified,
                )
            )
        return Catalog(pages=tuple(pages), files=tuple(files))

    def get_page(self, slug: str) -> Page:
        """Open a Markdown page, already converted to HTML.

        Args:
            slug: The page's path without its extension (e.g. ``"guia/instalacao"``).

        Returns:
            The page, ready for display.

        Raises:
            ContentNotFoundError: If no corresponding ``.md`` file exists.
        """
        name = source_name_for(slug)
        source = self._repository.stat(name)
        document = self._renderer.render(self._repository.read_text(name))
        info = PageInfo(
            slug=slug,
            title=document.title or humanize(slug),
            source_name=source.name,
            size=source.size,
            modified=source.modified,
        )
        return Page(info=info, document=document)

    def get_download(self, name: str) -> Download:
        """Locate a file (of any type, including ``.md``) for download.

        Args:
            name: Relative path of the file, including its extension.

        Returns:
            The validated path and the filename suggested for saving.

        Raises:
            ContentNotFoundError: If the file does not exist or must not be exposed.
        """
        path = self._repository.path_of(name)
        return Download(path=path, filename=path.name)

    def resolve(self, name: str) -> Resource:
        """Resolve a name received in the URL: first as a page, then as a file.

        ``guia/instalacao`` opens the page rendered from ``guia/instalacao.md``;
        ``guia/instalacao.md`` (with the extension) downloads the original Markdown
        source instead of rendering it; ``dados/tabela.csv`` downloads the CSV. This
        "page first" ordering is what lets a page and a same-named download coexist
        without ambiguity — see ``tests/test_service.py::test_resolve_prefers_page_over_file``.

        Args:
            name: The path segment received in the URL.

        Returns:
            Either a :class:`~wiki.models.Page` or a :class:`~wiki.models.Download`.

        Raises:
            ContentNotFoundError: If nothing matches the given name.
        """
        with suppress(ContentNotFoundError):
            return self.get_page(name)
        return self.get_download(name)
