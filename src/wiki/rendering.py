"""Conversion of Markdown into HTML.

Structure:

* :class:`Renderer` — the abstract contract (*Strategy* pattern): any Markdown engine
  that implements it can be plugged into the application.
* :class:`MarkdownItRenderer` — implementation built on ``markdown-it-py``, with syntax
  highlighting via Pygments, tables, anchored headings, and rewriting of ``.md`` links.
* :class:`CachedRenderer` — a *Decorator* that memoises results by the text's content,
  so a file is only re-processed once, when it actually changes.
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
"""A function that receives the ``MarkdownIt`` instance and registers extra rules on it."""

_FORMATTER = HtmlFormatter(nowrap=True)
_SAFE_LANGUAGE = re.compile(r"[\w+#.-]+")
_SLUG_INVALID = re.compile(r"[^\w\s-]")
_SLUG_SEPARATORS = re.compile(r"[\s-]+")


class Renderer(ABC):
    """Contract for something that converts Markdown into HTML."""

    @abstractmethod
    def render(self, text: str) -> RenderedDocument:
        """Convert the Markdown text into a complete HTML document."""

    @abstractmethod
    def title(self, text: str) -> str | None:
        """Extract only the title (first ``#`` heading), without generating HTML.

        This is considerably cheaper than :meth:`render` and is used purely to build
        the index (see :meth:`wiki.service.WikiService.catalog`), where the full HTML
        body is never needed.
        """


# --------------------------------------------------------------------------- highlighting


@lru_cache(maxsize=128)
def _lexer_for(language: str) -> Lexer:
    """Find the Pygments lexer for a language name, falling back to plain text.

    Cached because looking up a lexer by name is comparatively expensive and the same
    handful of languages (Python, JSON, Bash, …) tend to repeat across a whole site.
    """
    if language:
        try:
            return get_lexer_by_name(language, stripnl=False)
        except ClassNotFound:
            pass
    return TextLexer(stripnl=False)


def highlight_code(code: str, language: str, _attrs: str = "") -> str:
    """Highlight a fenced code block (```` ```python ````) using Pygments.

    The returned HTML starts with ``<pre``, which makes ``markdown-it-py`` use it
    as-is rather than wrapping it again. Colours come from CSS classes (see
    ``pygments.css``), not inline styles, which keeps the output compatible with the
    strict ``style-src`` directive set by :class:`wiki.security.SecurityHeaders`.

    Args:
        code: Contents of the block.
        language: Language named after the fence; empty if none was given.
        _attrs: Any further fence attributes (currently ignored).

    Returns:
        HTML for the block. Unknown languages are shown without highlighting, but
        still safely escaped.
    """
    body = highlight(code, _lexer_for(language), _FORMATTER)
    css_class = f' class="language-{language}"' if _SAFE_LANGUAGE.fullmatch(language) else ""
    return f'<pre class="highlight"><code{css_class}>{body}</code></pre>'


# --------------------------------------------------------------------------- extra rules


def _strip_markdown_suffix(href: str) -> str:
    """Turn ``page.md#section`` into ``page#section``; absolute URLs are left untouched."""
    parts = urlsplit(href)
    if parts.scheme or parts.netloc or not parts.path.endswith(MARKDOWN_SUFFIX):
        return href
    path = parts.path[: -len(MARKDOWN_SUFFIX)]
    return urlunsplit(parts._replace(path=path)) if path else href


def _rewrite_links(state: StateCore) -> None:
    """Core rule: ``.md`` links point to the rendered page; images are lazily loaded."""
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
    """Extract the plain text (with no markup) from an ``inline`` token.

    Used to build both the table of contents and the page title from a heading, which
    must never contain HTML markup (an anchor's ``id`` attribute, or a ``<title>``
    element, cannot safely hold arbitrary inline formatting).
    """
    parts: list[str] = []
    for child in inline.children or []:
        if child.type in {"text", "code_inline", "image"}:
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
    return "".join(parts).strip()


def slugify(text: str) -> str:
    """Generate a stable anchor identifier from a heading's text.

    Accented letters are kept as-is — useful for loanwords and non-English proper
    nouns — whitespace becomes a hyphen, and punctuation is stripped entirely. A
    heading with no usable characters left after cleaning (e.g. one made up solely of
    punctuation) falls back to the generic anchor ``"section"``.

    Example:
        >>> slugify("Café & Résumé")
        'café-résumé'
        >>> slugify("???")
        'section'
    """
    cleaned = _SLUG_INVALID.sub("", text.strip().lower())
    return _SLUG_SEPARATORS.sub("-", cleaned).strip("-") or "section"


def _unique_slug(text: str, used: dict[str, int]) -> str:
    """Ensure anchors are unique within a document (``title``, ``title-1``, ``title-2``…)."""
    base = slugify(text)
    count = used.get(base, 0)
    used[base] = count + 1
    return base if count == 0 else f"{base}-{count}"


def _collect_headings(state: StateCore) -> None:
    """Core rule: assign an ``id`` to each heading, and record the ToC and page title.

    Only the *first* level-1 heading sets the page title — subsequent ``# Heading``
    tokens (unusual, but not forbidden by CommonMark) are recorded in the table of
    contents like any other heading, without overriding the title already found.
    """
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
    """Wrap the table in a container that scrolls horizontally on narrow screens."""
    return '<div class="table-wrap">' + self.renderToken(tokens, idx, options, env)


def _table_close(
    self: RendererHTML, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
) -> str:
    """Close the container opened by :func:`_table_open`."""
    return self.renderToken(tokens, idx, options, env) + "</div>\n"


# ------------------------------------------------------------------ implementations


class MarkdownItRenderer(Renderer):
    """Renderer built on ``markdown-it-py`` (CommonMark-compliant).

    Enabled features: tables, ~~strikethrough~~, syntax-highlighted code blocks (via
    Pygments), anchored headings, a table of contents, cross-page links
    (``[x](other.md)``) and lazily loaded images. Raw HTML embedded in the Markdown
    source is escaped, unless ``allow_html`` is enabled — and even then, the
    ``script-src`` directive from :class:`wiki.security.SecurityHeaders` still
    prevents any inline ``<script>`` from executing.

    Args:
        allow_html: Preserve raw HTML found in the Markdown source when ``True``.
        plugins: Extra callables that receive the underlying ``MarkdownIt`` instance,
            so additional rules can be registered on it (an extension point intended
            for packages such as ``mdit-py-plugins``).
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
        """See :meth:`Renderer.render`."""
        env: dict[str, Any] = {}
        html = self._md.render(text, env)
        return RenderedDocument(
            html=html,
            title=env.get("title"),
            toc=tuple(env.get("toc", ())),
        )

    def title(self, text: str) -> str | None:
        """See :meth:`Renderer.title`. Only parses the source; never generates HTML."""
        env: dict[str, Any] = {}
        self._md.parse(text, env)
        title: str | None = env.get("title")
        return title


def _digest(text: str) -> bytes:
    """Compute a short digest of the content, used as the cache key."""
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()


class CachedRenderer(Renderer):
    """A *Decorator* that memoises the results of another :class:`Renderer`.

    The cache key is a digest of the text's **content**, not the file's name or
    modification time — so the cache can never serve stale HTML after an edit, and its
    correctness does not depend on the filesystem clock's resolution or accuracy.

    Args:
        inner: The wrapped renderer that actually does the work on a cache miss.
        document_cache_size: Maximum number of rendered documents kept in memory —
            forwarded to an internal :class:`wiki.cache.LRUCache`.
        title_cache_size: Maximum number of titles kept. Titles are tiny compared to
            full documents, so a much larger limit is cheap and worthwhile — the index
            page needs every page's title, even ones whose body was never rendered.
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
        """See :meth:`Renderer.render`."""
        return self._documents.get_or_compute(_digest(text), lambda: self._inner.render(text))

    def title(self, text: str) -> str | None:
        """See :meth:`Renderer.title`."""
        return self._titles.get_or_compute(_digest(text), lambda: self._inner.title(text))
