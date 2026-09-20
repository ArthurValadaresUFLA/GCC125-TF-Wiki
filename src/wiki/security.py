"""Cabeçalhos HTTP de segurança aplicados a todas as respostas."""

from __future__ import annotations

from urllib.parse import urlsplit

from flask import Flask, Response

from wiki.config import Settings


class SecurityHeaders:
    """Adiciona ``Content-Security-Policy`` e outros cabeçalhos defensivos.

    A política é restritiva: sem scripts inline, sem formulários, sem *frames* e sem
    conexões externas. Mesmo com ``WIKI_ALLOW_HTML=true``, um ``<script>`` escrito num
    arquivo Markdown não executa. Se o tema for uma URL externa, apenas a origem dela é
    liberada para estilos e fontes.

    Args:
        settings: Configuração da aplicação (usada para descobrir a origem do tema).
    """

    def __init__(self, settings: Settings) -> None:
        self._headers = {
            "Content-Security-Policy": self._build_csp(settings),
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
        }

    @staticmethod
    def _build_csp(settings: Settings) -> str:
        """Monta o valor do cabeçalho ``Content-Security-Policy``."""
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
        """Aplica os cabeçalhos à resposta (sem sobrescrever os já definidos)."""
        for name, value in self._headers.items():
            response.headers.setdefault(name, value)
        return response

    def install(self, app: Flask) -> None:
        """Registra o objeto como *hook* ``after_request`` da aplicação."""
        app.after_request(self)
