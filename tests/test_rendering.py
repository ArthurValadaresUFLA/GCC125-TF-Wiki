"""Testes de wiki.rendering."""

from __future__ import annotations

import unittest

from wiki.models import RenderedDocument
from wiki.rendering import CachedRenderer, MarkdownItRenderer, Renderer, slugify


class MarkdownItRendererTests(unittest.TestCase):
    """Conversão de Markdown em HTML."""

    def setUp(self) -> None:
        self.renderer = MarkdownItRenderer()

    def test_title_and_toc(self) -> None:
        doc = self.renderer.render("# Olá *mundo*\n\n## Um\n\n### Dois\n")
        self.assertEqual(doc.title, "Olá mundo")
        self.assertEqual([(e.level, e.title) for e in doc.toc], [(1, "Olá mundo"), (2, "Um"), (3, "Dois")])
        self.assertIn('<h2 id="um">', doc.html)

    def test_document_without_h1_has_no_title(self) -> None:
        self.assertIsNone(self.renderer.render("só texto").title)

    def test_duplicate_headings_get_unique_anchors(self) -> None:
        doc = self.renderer.render("## Dica\n\n## Dica\n\n## Dica\n")
        self.assertEqual([e.anchor for e in doc.toc], ["dica", "dica-1", "dica-2"])

    def test_title_ignores_headings_inside_code_fences(self) -> None:
        self.assertEqual(self.renderer.title("# Real\n\n```\n# comentário\n```"), "Real")
        self.assertIsNone(self.renderer.title("```\n# comentário\n```"))

    def test_slugify_keeps_accents_and_drops_punctuation(self) -> None:
        self.assertEqual(slugify("Instalação & Uso!"), "instalação-uso")
        self.assertEqual(slugify("???"), "secao")

    def test_code_block_is_highlighted_with_pygments(self) -> None:
        html = self.renderer.render("```python\ndef f():\n    return 1\n```").html
        self.assertIn('<pre class="highlight"><code class="language-python">', html)
        self.assertIn('<span class="k">def</span>', html)

    def test_unknown_language_falls_back_to_plain_text_escaped(self) -> None:
        html = self.renderer.render("```linguagem-inexistente\n<b>x</b>\n```").html
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
        self.assertNotIn("<b>", html)

    def test_malicious_language_string_cannot_break_out_of_attribute(self) -> None:
        html = self.renderer.render('```"><script>alert(1)</script>\ncódigo\n```').html
        self.assertNotIn("<script>", html)

    def test_raw_html_is_escaped_by_default(self) -> None:
        html = self.renderer.render("<script>alert(1)</script>\n\ntexto <b>x</b>").html
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_raw_html_is_kept_when_allowed(self) -> None:
        html = MarkdownItRenderer(allow_html=True).render("<details><summary>x</summary></details>").html
        self.assertIn("<details>", html)

    def test_dangerous_link_schemes_are_not_linked(self) -> None:
        html = self.renderer.render("[x](javascript:alert(1))").html
        self.assertNotIn("<a ", html)

    def test_markdown_links_point_to_pages(self) -> None:
        cases = {
            "[a](outra.md)": 'href="outra"',
            "[a](guia/x.md#sec)": 'href="guia/x#sec"',
            "[a](../y.md?q=1)": 'href="../y?q=1"',
            "[a](https://site.com/leia.md)": 'href="https://site.com/leia.md"',
            "[a](dados.csv)": 'href="dados.csv"',
            "[a](#ancora)": 'href="#ancora"',
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertIn(expected, self.renderer.render(source).html)

    def test_images_are_lazy(self) -> None:
        self.assertIn('loading="lazy"', self.renderer.render("![x](a.png)").html)

    def test_tables_are_wrapped_for_horizontal_scroll(self) -> None:
        html = self.renderer.render("| a | b |\n|---|---|\n| 1 | 2 |").html
        self.assertIn('<div class="table-wrap"><table>', html)
        self.assertIn("</table>\n</div>", html)

    def test_strikethrough(self) -> None:
        self.assertIn("<s>x</s>", self.renderer.render("~~x~~").html)

    def test_plugins_are_applied(self) -> None:
        applied: list[object] = []
        MarkdownItRenderer(plugins=[applied.append])
        self.assertEqual(len(applied), 1)


class _CountingRenderer(Renderer):
    """Dublê de teste que conta quantas vezes foi chamado."""

    def __init__(self) -> None:
        self.render_calls = 0
        self.title_calls = 0

    def render(self, text: str) -> RenderedDocument:
        self.render_calls += 1
        return RenderedDocument(html=text.upper(), title=None, toc=())

    def title(self, text: str) -> str | None:
        self.title_calls += 1
        return text[:3]


class CachedRendererTests(unittest.TestCase):
    """O decorator só delega quando o conteúdo é novo."""

    def test_same_text_is_rendered_once(self) -> None:
        inner = _CountingRenderer()
        cached = CachedRenderer(inner)
        self.assertEqual(cached.render("abc").html, "ABC")
        self.assertEqual(cached.render("abc").html, "ABC")
        self.assertEqual(inner.render_calls, 1)

    def test_changed_text_is_rendered_again(self) -> None:
        inner = _CountingRenderer()
        cached = CachedRenderer(inner)
        cached.render("abc")
        self.assertEqual(cached.render("abd").html, "ABD")
        self.assertEqual(inner.render_calls, 2)

    def test_titles_are_cached_separately(self) -> None:
        inner = _CountingRenderer()
        cached = CachedRenderer(inner)
        cached.title("abcdef")
        cached.title("abcdef")
        self.assertEqual(inner.title_calls, 1)
        self.assertEqual(inner.render_calls, 0)


if __name__ == "__main__":
    unittest.main()
