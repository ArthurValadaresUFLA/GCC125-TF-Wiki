"""Camada de serviço: orquestra repositório e renderizador (padrão *Facade*).

As rotas HTTP conversam somente com :class:`WikiService`; não conhecem o sistema de
arquivos nem o motor de Markdown.
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
    """Casos de uso da wiki: montar o índice, abrir uma página, localizar um download.

    As dependências são injetadas no construtor, o que permite trocar o repositório
    (ex.: por um em memória, nos testes) ou o renderizador sem tocar nesta classe.

    Args:
        repository: Fonte do conteúdo.
        renderer: Conversor de Markdown em HTML.
    """

    def __init__(self, repository: ContentRepository, renderer: Renderer) -> None:
        self._repository = repository
        self._renderer = renderer

    def catalog(self) -> Catalog:
        """Monta o índice: páginas Markdown de um lado, demais arquivos do outro.

        Returns:
            O catálogo com todo o conteúdo visível.
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
                continue  # removido entre a listagem e a leitura
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
        """Abre uma página Markdown já convertida em HTML.

        Args:
            slug: Caminho da página sem a extensão (``"guia/instalacao"``).

        Returns:
            A página pronta para exibição.

        Raises:
            ContentNotFoundError: Se não houver um ``.md`` correspondente.
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
        """Localiza um arquivo (de qualquer tipo, inclusive ``.md``) para download.

        Args:
            name: Caminho relativo do arquivo, com a extensão.

        Returns:
            O caminho validado e o nome sugerido para salvar.

        Raises:
            ContentNotFoundError: Se o arquivo não existir ou não puder ser exposto.
        """
        path = self._repository.path_of(name)
        return Download(path=path, filename=path.name)

    def resolve(self, name: str) -> Resource:
        """Resolve o nome recebido na URL: primeiro como página, depois como arquivo.

        ``guia/instalacao`` abre a página ``guia/instalacao.md``; ``guia/instalacao.md``
        (com extensão) baixa o Markdown original; ``dados/tabela.csv`` baixa o CSV.

        Args:
            name: Trecho de caminho recebido na URL.

        Returns:
            Uma :class:`~wiki.models.Page` ou um :class:`~wiki.models.Download`.

        Raises:
            ContentNotFoundError: Se nada corresponder ao nome.
        """
        with suppress(ContentNotFoundError):
            return self.get_page(name)
        return self.get_download(name)
