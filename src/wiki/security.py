"""HTTP security headers applied to every response."""

from __future__ import annotations

from urllib.parse import urlsplit

from flask import Flask, Response

from wiki.config import Settings


class SecurityHeaders:
    """Adds ``Content-Security-Policy`` and other defensive headers to every response.

    The policy is deliberately restrictive: no inline scripts, no forms, no frames,
    and no external connections beyond what the configured theme explicitly needs.
    Even with ``WIKI_ALLOW_HTML=true`` (see :class:`wiki.config.Settings`), a
    ``<script>`` tag written into a Markdown file will not execute, because
    ``script-src`` never includes ``'unsafe-inline'`` — the CSP, not Markdown
    escaping, is what actually stops it in that case. If the theme is an external URL,
    only that URL's origin is allow-listed for styles and fonts; everything else stays
    blocked.

    Args:
        settings: Application configuration (used to work out the theme's origin, if
            any).
    """

    def __init__(self, settings: Settings) -> None:
        self._headers = {
            "Content-Security-Policy": self._build_csp(settings),
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
        }

    @staticmethod
    def _build_csp(settings: Settings) -> str:
        """Build the value of the ``Content-Security-Policy`` header."""
        theme_source = ""
        if settings.theme_is_remote:
            parts = urlsplit(settings.theme_css)
            theme_source = f" {parts.scheme}://{parts.netloc}"
        directives = (
            "default-src 'none'",
            f"style-src 'self'{theme_source}",
            "script-src 'self'",
            "img-src 'self' data: https:",
            f"font-src 'self'{theme_source}",
            "base-uri 'self'",
            "form-action 'none'",
            "frame-ancestors 'none'",
        )
        return "; ".join(directives)

    def __call__(self, response: Response) -> Response:
        """Apply the headers to the response, without overwriting any already set."""
        for name, value in self._headers.items():
            response.headers.setdefault(name, value)
        return response

    def install(self, app: Flask) -> None:
        """Register this object as the application's ``after_request`` hook."""
        app.after_request(self)
