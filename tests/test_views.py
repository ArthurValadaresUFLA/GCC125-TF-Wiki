"""Integration tests for the HTTP routes (Flask test client)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from tests.conftest import captured_templates
from tests.helpers import write_tree
from wiki import create_app
from wiki.config import Settings


def get(client: FlaskClient, url: str, **kwargs: Any) -> TestResponse:
    """GET with the body fully read, so any served files get closed."""
    return client.get(url, buffered=True, **kwargs)


# --------------------------------------------------------------------------
# `content_dir` overrides the fixture of the same name from conftest.py: here
# it comes pre-populated with the default content used by the view tests.
# `app` is the fixture the `client` fixture (defined in conftest.py) uses to
# build Flask's test client.
# --------------------------------------------------------------------------


@pytest.fixture
def content_dir(workdir: Path) -> Path:
    content = workdir / "content"
    content.mkdir()
    write_tree(
        content,
        {
            "home.md": "# Home\n\nWelcome. See the [guide](guide/installation.md).\n",
            "guide/installation.md": (
                "# Installation\n\n## Step 1\n\n## Step 2\n\n"
                "```python\nprint('hi')\n```\n\n![img](../images/logo.png)\n"
            ),
            "data/sales.csv": "month,value\njan,1\n",
            "images/logo.png": b"\x89PNG\r\n\x1a\n",
            "html-page.md": "# HTML\n\n<script>alert(1)</script>\n",
            ".env": "SECRET=1",
        },
    )
    write_tree(workdir, {"outside.txt": "outside the root"})
    return content


@pytest.fixture
def settings_overrides() -> dict[str, object]:
    """Extra settings for `Settings`; test classes may override this."""
    return {}


@pytest.fixture
def app(content_dir: Path, settings_overrides: dict[str, object]) -> Flask:
    settings = Settings(content_dir=content_dir, site_title="My Wiki", **settings_overrides)  # type: ignore[arg-type]
    return create_app(settings)


# --------------------------------------------------------------------------
# GET /
# --------------------------------------------------------------------------


class TestIndex:
    def test_lists_pages_grouped_and_downloads(self, client: FlaskClient) -> None:
        response = get(client, "/")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "My Wiki" in html
        assert 'href="/home"' in html
        assert 'href="/guide/installation"' in html
        assert ">guide</h2>" in html
        assert "Downloadable files" in html
        assert 'href="/data/sales.csv"' in html
        assert 'href="/images/logo.png"' in html

    def test_hidden_files_are_not_listed(self, client: FlaskClient) -> None:
        assert ".env" not in get(client, "/").get_data(as_text=True)

    def test_empty_folder_shows_hint(self, workdir: Path) -> None:
        empty = workdir / "empty"
        empty.mkdir()
        client = create_app(Settings(content_dir=empty)).test_client()
        assert "No content found yet." in client.get("/").get_data(as_text=True)


# --------------------------------------------------------------------------
# GET /<name>
# --------------------------------------------------------------------------


class TestPage:
    def test_renders_markdown_page(self, client: FlaskClient) -> None:
        response = get(client, "/guide/installation")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "<title>Installation · My Wiki</title>" in html
        assert '<h2 id="step-1">Step 1</h2>' in html
        assert 'class="highlight"' in html
        assert "On this page" in html  # table of contents, since there are 2+ sections
        assert 'href="/guide/installation.md"' in html  # download the .md source
        assert "data-autoprint" not in html
        assert "<base" not in html

    def test_links_between_pages_drop_the_md_extension(self, client: FlaskClient) -> None:
        assert 'href="guide/installation"' in get(client, "/home").get_data(as_text=True)

    def test_markdown_source_is_downloaded_as_attachment(self, client: FlaskClient) -> None:
        response = get(client, "/guide/installation.md")
        assert response.status_code == 200
        assert "attachment" in response.headers["Content-Disposition"]
        assert "installation.md" in response.headers["Content-Disposition"]
        assert response.get_data(as_text=True).startswith("# Installation")

    def test_other_files_are_attachments(self, client: FlaskClient) -> None:
        response = get(client, "/data/sales.csv")
        assert response.status_code == 200
        assert "attachment" in response.headers["Content-Disposition"]
        assert response.get_data(as_text=True) == "month,value\njan,1\n"

    def test_unknown_path_is_404_html(self, client: FlaskClient) -> None:
        response = get(client, "/does-not-exist")
        assert response.status_code == 404
        assert "Page not found." in response.get_data(as_text=True)

    @pytest.mark.parametrize(
        "url",
        ["/.env", "/../outside.txt", "/%2e%2e/outside.txt", "/guide/../.env", "/%2Fetc/passwd"],
    )
    def test_hidden_and_traversal_paths_are_404(self, client: FlaskClient, url: str) -> None:
        assert get(client, url).status_code == 404

    def test_symlink_pointing_outside_is_404(
        self, client: FlaskClient, content_dir: Path, workdir: Path
    ) -> None:
        (content_dir / "shortcut.txt").symlink_to(workdir / "outside.txt")
        assert get(client, "/shortcut.txt").status_code == 404

    def test_http_error_handler_405(self, app: Flask, client: FlaskClient) -> None:
        with captured_templates(app) as templates:
            response = client.post("/")
        assert response.status_code == 405
        assert "error.html" in templates or b"error" in response.data

    def test_raw_html_in_markdown_is_escaped(self, client: FlaskClient) -> None:
        html = get(client, "/html-page").get_data(as_text=True)
        assert "<script>alert(1)</script>" not in html

    def test_etag_allows_304(self, client: FlaskClient) -> None:
        first = get(client, "/home")
        second = get(client, "/home", headers={"If-None-Match": first.headers["ETag"]})
        assert second.status_code == 304

    def test_edit_on_disk_is_reflected(self, client: FlaskClient, content_dir: Path) -> None:
        assert "Home" in get(client, "/home").get_data(as_text=True)
        (content_dir / "home.md").write_text("# New title\n", encoding="utf-8")
        assert "New title" in get(client, "/home").get_data(as_text=True)

    def test_static_assets_do_not_shadow_content_named_static(
        self, client: FlaskClient, content_dir: Path
    ) -> None:
        write_tree(content_dir, {"static/x.md": "# Static"})
        assert get(client, "/static/x").status_code == 200
        assert get(client, "/_static/css/wiki.css").status_code == 200


# --------------------------------------------------------------------------
# Security headers
# --------------------------------------------------------------------------


class TestSecurityHeaders:
    @pytest.mark.parametrize("url", ["/", "/home", "/data/sales.csv", "/does-not-exist"])
    def test_headers_on_pages_and_downloads(self, client: FlaskClient, url: str) -> None:
        headers = get(client, url).headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        csp = headers["Content-Security-Policy"]
        assert "default-src 'none'" in csp
        assert "script-src 'self'" in csp
        assert "unsafe-inline" not in csp

    def test_remote_theme_origin_is_whitelisted(self, content_dir: Path) -> None:
        settings = Settings(
            content_dir=content_dir, theme_css="https://cdn.example.com/x/theme.css"
        )
        headers = create_app(settings).test_client().get("/").headers
        assert "style-src 'self' https://cdn.example.com" in headers["Content-Security-Policy"]

    def test_remote_theme_link_is_used_as_is(self, content_dir: Path) -> None:
        settings = Settings(
            content_dir=content_dir, theme_css="https://cdn.example.com/x/theme.css"
        )
        html = create_app(settings).test_client().get("/").get_data(as_text=True)
        assert 'href="https://cdn.example.com/x/theme.css"' in html

    def test_local_theme_is_served_from_static(self, client: FlaskClient) -> None:
        assert 'href="/_static/vendor/picocss/pico.min.css"' in get(client, "/").get_data(
            as_text=True
        )


# --------------------------------------------------------------------------
# With WIKI_ALLOW_HTML, HTML is preserved, but the CSP still blocks scripts.
# --------------------------------------------------------------------------


class TestAllowHtml:
    @pytest.fixture
    def settings_overrides(self) -> dict[str, object]:
        return {"allow_html": True}

    def test_html_is_preserved_but_csp_blocks_inline_scripts(self, client: FlaskClient) -> None:
        response = get(client, "/html-page")
        assert "<script>alert(1)</script>" in response.get_data(as_text=True)
        assert "unsafe-inline" not in response.headers["Content-Security-Policy"]
