"""Testes de integração das rotas HTTP (Flask test client)."""

from __future__ import annotations

import unittest
from typing import Any, ClassVar

from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from tests.helpers import ContentDirTestCase, write_tree
from wiki import create_app
from wiki.config import Settings


class ViewsTestCase(ContentDirTestCase):
    """Sobe a aplicação sobre uma pasta temporária com conteúdo variado."""

    settings_overrides: ClassVar[dict[str, object]] = {}

    def setUp(self) -> None:
        super().setUp()

        write_tree(
            self.content,
            {
                "inicio.md": "# Início\n\nBem-vindo. Veja o [guia](guia/instalacao.md).\n",
                "guia/instalacao.md": (
                    "# Instalação\n\n## Passo 1\n\n## Passo 2\n\n"
                    "```python\nprint('oi')\n```\n\n![img](../imagens/logo.png)\n"
                ),
                "dados/vendas.csv": "mes,valor\njan,1\n",
                "imagens/logo.png": b"\x89PNG\r\n\x1a\n",
                "pagina-html.md": "# HTML\n\n<script>alert(1)</script>\n",
                ".env": "SEGREDO=1",
            },
        )
        write_tree(self.workdir, {"fora.txt": "fora da raiz"})
        settings = Settings(
            content_dir=self.content, site_title="Minha Wiki", **self.settings_overrides
        )  # type: ignore[arg-type]
        self.app: Flask = create_app(settings)
        self.client: FlaskClient = self.app.test_client()

    def get(self, url: str, **kwargs: Any) -> TestResponse:
        """GET com o corpo lido por inteiro, para que arquivos enviados sejam fechados."""
        return self.client.get(url, buffered=True, **kwargs)


class IndexTests(ViewsTestCase):
    """GET /"""

    def test_lists_pages_grouped_and_downloads(self) -> None:
        response = self.get("/")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Minha Wiki", html)
        self.assertIn('href="/inicio"', html)
        self.assertIn('href="/guia/instalacao"', html)
        self.assertIn(">guia</h2>", html)
        self.assertIn("Arquivos para download", html)
        self.assertIn('href="/dados/vendas.csv"', html)
        self.assertIn('href="/imagens/logo.png"', html)

    def test_hidden_files_are_not_listed(self) -> None:
        self.assertNotIn(".env", self.get("/").get_data(as_text=True))

    def test_empty_folder_shows_hint(self) -> None:
        empty = self.workdir / "vazia"
        empty.mkdir()
        client = create_app(Settings(content_dir=empty)).test_client()
        self.assertIn("Nenhum conteúdo encontrado", client.get("/").get_data(as_text=True))


class PageTests(ViewsTestCase):
    """GET /<nome>"""

    def test_renders_markdown_page(self) -> None:
        response = self.get("/guia/instalacao")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("<title>Instalação · Minha Wiki</title>", html)
        self.assertIn('<h2 id="passo-1">Passo 1</h2>', html)
        self.assertIn('class="highlight"', html)
        self.assertIn("Nesta página", html)  # índice, pois há 2+ seções
        self.assertIn('href="/guia/instalacao.md"', html)  # baixar .md
        self.assertNotIn("data-autoprint", html)
        self.assertNotIn("<base", html)

    def test_links_between_pages_drop_the_md_extension(self) -> None:
        self.assertIn('href="guia/instalacao"', self.get("/inicio").get_data(as_text=True))

    def test_markdown_source_is_downloaded_as_attachment(self) -> None:
        response = self.get("/guia/instalacao.md")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertIn("instalacao.md", response.headers["Content-Disposition"])
        self.assertTrue(response.get_data(as_text=True).startswith("# Instalação"))

    def test_other_files_are_attachments(self) -> None:
        response = self.get("/dados/vendas.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(response.get_data(as_text=True), "mes,valor\njan,1\n")

    def test_unknown_path_is_404_html(self) -> None:
        response = self.get("/nao-existe")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Página não encontrada", response.get_data(as_text=True))

    def test_hidden_and_traversal_paths_are_404(self) -> None:
        for url in ["/.env", "/../fora.txt", "/%2e%2e/fora.txt", "/guia/../.env", "/%2Fetc/passwd"]:
            with self.subTest(url=url):
                self.assertEqual(self.get(url).status_code, 404)

    def test_symlink_pointing_outside_is_404(self) -> None:
        (self.content / "atalho.txt").symlink_to(self.workdir / "fora.txt")
        self.assertEqual(self.get("/atalho.txt").status_code, 404)

    def test_raw_html_in_markdown_is_escaped(self) -> None:
        html = self.get("/pagina-html").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_etag_allows_304(self) -> None:
        first = self.get("/inicio")
        second = self.get("/inicio", headers={"If-None-Match": first.headers["ETag"]})
        self.assertEqual(second.status_code, 304)

    def test_edit_on_disk_is_reflected(self) -> None:
        self.assertIn("Início", self.get("/inicio").get_data(as_text=True))
        (self.content / "inicio.md").write_text("# Novo título\n", encoding="utf-8")
        self.assertIn("Novo título", self.get("/inicio").get_data(as_text=True))

    def test_static_assets_do_not_shadow_content_named_static(self) -> None:
        write_tree(self.content, {"static/x.md": "# Estática"})
        self.assertEqual(self.get("/static/x").status_code, 200)
        self.assertEqual(self.get("/_static/css/wiki.css").status_code, 200)


class SecurityHeadersTests(ViewsTestCase):
    """Cabeçalhos de segurança."""

    def test_headers_on_pages_and_downloads(self) -> None:
        for url in ["/", "/inicio", "/dados/vendas.csv", "/nao-existe"]:
            with self.subTest(url=url):
                headers = self.get(url).headers
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                csp = headers["Content-Security-Policy"]
                self.assertIn("default-src 'none'", csp)
                self.assertIn("script-src 'self'", csp)
                self.assertNotIn("unsafe-inline", csp)

    def test_remote_theme_origin_is_whitelisted(self) -> None:
        settings = Settings(
            content_dir=self.content, theme_css="https://cdn.example.com/x/tema.css"
        )
        headers = create_app(settings).test_client().get("/").headers
        self.assertIn(
            "style-src 'self' https://cdn.example.com", headers["Content-Security-Policy"]
        )

    def test_remote_theme_link_is_used_as_is(self) -> None:
        settings = Settings(
            content_dir=self.content, theme_css="https://cdn.example.com/x/tema.css"
        )
        html = create_app(settings).test_client().get("/").get_data(as_text=True)
        self.assertIn('href="https://cdn.example.com/x/tema.css"', html)

    def test_local_theme_is_served_from_static(self) -> None:
        self.assertIn(
            'href="/_static/vendor/picocss/pico.min.css"',
            self.get("/").get_data(as_text=True),
        )


class AllowHtmlTests(ViewsTestCase):
    """Com WIKI_ALLOW_HTML o HTML é preservado, mas a CSP continua barrando scripts."""

    settings_overrides: ClassVar[dict[str, object]] = {"allow_html": True}

    def test_html_is_preserved_but_csp_blocks_inline_scripts(self) -> None:
        response = self.get("/pagina-html")
        self.assertIn("<script>alert(1)</script>", response.get_data(as_text=True))
        self.assertNotIn("unsafe-inline", response.headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
