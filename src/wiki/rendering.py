"""Conversão de Markdown em HTML.

Estrutura:

* :class:`Renderer` — contrato abstrato (*Strategy*): qualquer motor de Markdown que o
  implemente pode ser plugado na aplicação.
* :class:`MarkdownItRenderer` — implementação baseada em ``markdown-it-py`` com realce de
  código via Pygments, tabelas, títulos com âncora e reescrita de links ``.md``.
* :class:`CachedRenderer` — *Decorator* que memoriza resultados pelo conteúdo do texto,
  de modo que só se reprocessa um arquivo quando ele muda.
"""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexer import Lexer
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

from wiki.cache import LRUCache
from wiki.models import MARKDOWN_SUFFIX, RenderedDocument, TocEntry

MarkdownPlugin = Callable[[MarkdownIt], None]
"""Função que recebe a instância de ``MarkdownIt`` e registra regras extras nela."""

_FORMATTER = HtmlFormatter(nowrap=True)
_SAFE_LANGUAGE = re.compile(r"[\w+#.-]+")
_SLUG_INVALID = re.compile(r"[^\w\s-]")
_SLUG_SEPARATORS = re.compile(r"[\s-]+")


class Renderer(ABC):
    """Contrato de um conversor de Markdown em HTML."""

    @abstractmethod
    def render(self, text: str) -> RenderedDocument:
        """Converte o texto Markdown em um documento HTML completo."""

    @abstractmethod
    def title(self, text: str) -> str | None:
        """Extrai apenas o título (primeiro ``#``), sem gerar o HTML.

        É bem mais barato que :meth:`render` e por isso usado para montar o índice.
        """


# --------------------------------------------------------------------------- realce


@lru_cache(maxsize=128)
def _lexer_for(language: str) -> Lexer:
    """Localiza o *lexer* do Pygments para a linguagem, com texto puro como reserva."""
    if language:
        try:
            return get_lexer_by_name(language, stripnl=False)
        except ClassNotFound:
            pass
    return TextLexer(stripnl=False)


def highlight_code(code: str, language: str, _attrs: str = "") -> str:
    """Realça um bloco de código cercado (```` ```python ````) com o Pygments.

    O HTML devolvido começa com ``<pre`` — o que faz o ``markdown-it-py`` usá-lo como está,
    sem embrulhá-lo novamente. As cores vêm de classes CSS (ver ``pygments.css``).

    Args:
        code: Conteúdo do bloco.
        language: Linguagem informada após a cerca; vazia se não houver.
        _attrs: Demais atributos da cerca (ignorados).

    Returns:
        HTML do bloco. Linguagens desconhecidas são exibidas sem realce.
    """
    body = highlight(code, _lexer_for(language), _FORMATTER)
    css_class = f' class="language-{language}"' if _SAFE_LANGUAGE.fullmatch(language) else ""
    return f'<pre class="highlight"><code{css_class}>{body}</code></pre>'


# --------------------------------------------------------------------- regras extras


def _strip_markdown_suffix(href: str) -> str:
    """Troca ``pagina.md#secao`` por ``pagina#secao``; URLs absolutas não mudam."""
    parts = urlsplit(href)
    if parts.scheme or parts.netloc or not parts.path.endswith(MARKDOWN_SUFFIX):
        return href
    path = parts.path[: -len(MARKDOWN_SUFFIX)]
    return urlunsplit(parts._replace(path=path)) if path else href


def _rewrite_links(state: StateCore) -> None:
    """Regra de núcleo: links ``.md`` apontam para a página; imagens carregam sob demanda."""
    for block in state.tokens:
        if block.type != "inline" or not block.children:
            continue
        for child in block.children:
            if child.type == "link_open":
                href = child.attrGet("href")
                if isinstance(href, str):
                    child.attrSet("href", _strip_markdown_suffix(href))
            elif child.type == "image":
                child.attrSet("loading", "lazy")


def _plain_text(inline: Token) -> str:
    """Extrai o texto puro (sem marcação) de um token ``inline``."""
    parts: list[str] = []
    for child in inline.children or []:
        if child.type in {"text", "code_inline", "image"}:
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
    return "".join(parts).strip()


def slugify(text: str) -> str:
    """Gera um identificador de âncora estável a partir do texto de um título.

    Mantém letras acentuadas, troca espaços por hífens e remove pontuação.

    Example:
        ``slugify("Instalação & Uso")`` devolve ``"instalação-uso"``.
    """
    cleaned = _SLUG_INVALID.sub("", text.strip().lower())
    return _SLUG_SEPARATORS.sub("-", cleaned).strip("-") or "secao"


def _unique_slug(text: str, used: dict[str, int]) -> str:
    """Garante âncoras únicas no documento (``titulo``, ``titulo-1``, ``titulo-2``…)."""
    base = slugify(text)
    count = used.get(base, 0)
    used[base] = count + 1
    return base if count == 0 else f"{base}-{count}"


def _collect_headings(state: StateCore) -> None:
    """Regra de núcleo: atribui ``id`` aos títulos e registra o índice e o título do texto."""
    toc: list[TocEntry] = []
    used: dict[str, int] = {}
    title: str | None = None
    tokens = state.tokens
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        text = _plain_text(tokens[index + 1])
        level = int(token.tag[1:])
        anchor = _unique_slug(text, used)
        token.attrSet("id", anchor)
        toc.append(TocEntry(level=level, title=text, anchor=anchor))
        if level == 1 and title is None:
            title = text or None
    state.env["toc"] = toc
    state.env["title"] = title


def _table_open(
    self: RendererHTML, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
) -> str:
    """Envolve a tabela em um contêiner com rolagem horizontal (telas estreitas)."""
    return '<div class="table-wrap">' + self.renderToken(tokens, idx, options, env)


def _table_close(
    self: RendererHTML, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
) -> str:
    """Fecha o contêiner aberto por :func:`_table_open`."""
    return self.renderToken(tokens, idx, options, env) + "</div>\n"


# ------------------------------------------------------------------ implementações


class MarkdownItRenderer(Renderer):
    """Renderizador baseado em ``markdown-it-py`` (compatível com CommonMark).

    Recursos habilitados: tabelas, ~~tachado~~, realce de código (Pygments), âncoras nos
    títulos, índice, links entre páginas (``[x](outra.md)``) e imagens com carga tardia.
    HTML cru no Markdown é escapado, a menos que ``allow_html`` seja verdadeiro.

    Args:
        allow_html: Preserva HTML cru presente no Markdown quando verdadeiro.
        plugins: Funções extras que recebem o ``MarkdownIt`` para registrar novas regras
            (ponto de extensão, ex.: ``mdit-py-plugins``).
    """

    def __init__(
        self,
        *,
        allow_html: bool = False,
        plugins: Iterable[MarkdownPlugin] = (),
    ) -> None:
        md = MarkdownIt("commonmark", {"html": allow_html, "highlight": highlight_code})
        md.enable(["table", "strikethrough"])
        md.add_render_rule("table_open", _table_open)
        md.add_render_rule("table_close", _table_close)
        md.core.ruler.push("wiki_links", _rewrite_links)
        md.core.ruler.push("wiki_headings", _collect_headings)
        for plugin in plugins:
            plugin(md)
        self._md = md

    def render(self, text: str) -> RenderedDocument:
        """Ver :meth:`Renderer.render`."""
        env: dict[str, Any] = {}
        html = self._md.render(text, env)
        return RenderedDocument(
            html=html,
            title=env.get("title"),
            toc=tuple(env.get("toc", ())),
        )

    def title(self, text: str) -> str | None:
        """Ver :meth:`Renderer.title`. Faz apenas a análise, sem realce nem HTML."""
        env: dict[str, Any] = {}
        self._md.parse(text, env)
        title: str | None = env.get("title")
        return title


def _digest(text: str) -> bytes:
    """Resumo curto do conteúdo, usado como chave de cache."""
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()


class CachedRenderer(Renderer):
    """*Decorator* que memoriza os resultados de outro :class:`Renderer`.

    A chave é um resumo do **conteúdo** do texto e não do nome/data do arquivo; assim o
    cache nunca serve HTML desatualizado e não depende da precisão do relógio do disco.

    Args:
        inner: Renderizador decorado.
        document_cache_size: Máximo de documentos renderizados mantidos em memória.
        title_cache_size: Máximo de títulos mantidos (são pequenos, então o limite é maior).
    """

    def __init__(
        self,
        inner: Renderer,
        *,
        document_cache_size: int = 128,
        title_cache_size: int = 4096,
    ) -> None:
        self._inner = inner
        self._documents: LRUCache[bytes, RenderedDocument] = LRUCache(document_cache_size)
        self._titles: LRUCache[bytes, str | None] = LRUCache(title_cache_size)

    def render(self, text: str) -> RenderedDocument:
        """Ver :meth:`Renderer.render`."""
        return self._documents.get_or_compute(_digest(text), lambda: self._inner.render(text))

    def title(self, text: str) -> str | None:
        """Ver :meth:`Renderer.title`."""
        return self._titles.get_or_compute(_digest(text), lambda: self._inner.title(text))
