"""Tests for wiki.rendering."""

from __future__ import annotations

import pytest

from wiki.models import RenderedDocument
from wiki.rendering import CachedRenderer, MarkdownItRenderer, Renderer, slugify


@pytest.fixture
def renderer() -> MarkdownItRenderer:
    return MarkdownItRenderer()


class TestMarkdownItRenderer:
    """Conversion of Markdown into HTML."""

    def test_title_and_toc(self, renderer: MarkdownItRenderer) -> None:
        doc = renderer.render("# Hello *world*\n\n## One\n\n### Two\n")
        assert doc.title == "Hello world"
        assert [(e.level, e.title) for e in doc.toc] == [
            (1, "Hello world"),
            (2, "One"),
            (3, "Two"),
        ]
        assert '<h2 id="one">' in doc.html

    def test_document_without_h1_has_no_title(self, renderer: MarkdownItRenderer) -> None:
        assert renderer.render("just text").title is None

    def test_duplicate_headings_get_unique_anchors(self, renderer: MarkdownItRenderer) -> None:
        doc = renderer.render("## Tip\n\n## Tip\n\n## Tip\n")
        assert [e.anchor for e in doc.toc] == ["tip", "tip-1", "tip-2"]

    def test_title_ignores_headings_inside_code_fences(self, renderer: MarkdownItRenderer) -> None:
        assert renderer.title("# Real\n\n```\n# comment\n```") == "Real"
        assert renderer.title("```\n# comment\n```") is None

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Café & Résumé!", "café-résumé"),
            ("seção", "seção"),
            ("Jhonson & Jhonson", "jhonson-jhonson"),
        ],
    )
    def test_slugify_keeps_accents_and_drops_punctuation(self, text: str, expected: str) -> None:
        assert slugify(text) == expected

    def test_code_block_is_highlighted_with_pygments(self, renderer: MarkdownItRenderer) -> None:
        html = renderer.render("```python\ndef f():\n    return 1\n```").html
        assert '<pre class="highlight"><code class="language-python">' in html
        assert '<span class="k">def</span>' in html

    def test_unknown_language_falls_back_to_plain_text_escaped(
        self, renderer: MarkdownItRenderer
    ) -> None:
        html = renderer.render("```made-up-language\n<b>x</b>\n```").html
        assert "&lt;b&gt;x&lt;/b&gt;" in html
        assert "<b>" not in html

    def test_malicious_language_string_cannot_break_out_of_attribute(
        self, renderer: MarkdownItRenderer
    ) -> None:
        html = renderer.render('```"><script>alert(1)</script>\ncode\n```').html
        assert "<script>" not in html

    def test_raw_html_is_escaped_by_default(self, renderer: MarkdownItRenderer) -> None:
        html = renderer.render("<script>alert(1)</script>\n\ntext <b>x</b>").html
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_raw_html_is_kept_when_allowed(self) -> None:
        html = (
            MarkdownItRenderer(allow_html=True)
            .render("<details><summary>x</summary></details>")
            .html
        )
        assert "<details>" in html

    def test_dangerous_link_schemes_are_not_linked(self, renderer: MarkdownItRenderer) -> None:
        html = renderer.render("[x](javascript:alert(1))").html
        assert "<a " not in html

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("[a](other.md)", 'href="other"'),
            ("[a](guide/x.md#sec)", 'href="guide/x#sec"'),
            ("[a](../y.md?q=1)", 'href="../y?q=1"'),
            ("[a](https://site.com/read.md)", 'href="https://site.com/read.md"'),
            ("[a](data.csv)", 'href="data.csv"'),
            ("[a](#anchor)", 'href="#anchor"'),
        ],
    )
    def test_markdown_links_point_to_pages(
        self, renderer: MarkdownItRenderer, source: str, expected: str
    ) -> None:
        assert expected in renderer.render(source).html

    def test_images_are_lazy(self, renderer: MarkdownItRenderer) -> None:
        assert 'loading="lazy"' in renderer.render("![x](a.png)").html

    def test_tables_are_wrapped_for_horizontal_scroll(self, renderer: MarkdownItRenderer) -> None:
        html = renderer.render("| a | b |\n|---|---|\n| 1 | 2 |").html
        assert '<div class="table-wrap"><table>' in html
        assert "</table>\n</div>" in html

    def test_strikethrough(self, renderer: MarkdownItRenderer) -> None:
        assert "<s>x</s>" in renderer.render("~~x~~").html

    def test_plugins_are_applied(self) -> None:
        applied: list[object] = []
        MarkdownItRenderer(plugins=[applied.append])
        assert len(applied) == 1


class _CountingRenderer(Renderer):
    """Test double that counts how many times it was called."""

    def __init__(self) -> None:
        self.render_calls = 0
        self.title_calls = 0

    def render(self, text: str) -> RenderedDocument:
        self.render_calls += 1
        return RenderedDocument(html=text.upper(), title=None, toc=())

    def title(self, text: str) -> str | None:
        self.title_calls += 1
        return text[:3]


class TestCachedRenderer:
    """The decorator only delegates when the content is new."""

    def test_same_text_is_rendered_once(self) -> None:
        inner = _CountingRenderer()
        cached = CachedRenderer(inner)
        assert cached.render("abc").html == "ABC"
        assert cached.render("abc").html == "ABC"
        assert inner.render_calls == 1

    def test_changed_text_is_rendered_again(self) -> None:
        inner = _CountingRenderer()
        cached = CachedRenderer(inner)
        cached.render("abc")
        assert cached.render("abd").html == "ABD"
        assert inner.render_calls == 2

    def test_titles_are_cached_separately(self) -> None:
        inner = _CountingRenderer()
        cached = CachedRenderer(inner)
        cached.title("abcdef")
        cached.title("abcdef")
        assert inner.title_calls == 1
        assert inner.render_calls == 0
