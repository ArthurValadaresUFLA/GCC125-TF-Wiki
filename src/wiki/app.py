"""Composição da aplicação: *application factory* e ligação das dependências."""

from __future__ import annotations

from flask import Flask, render_template, url_for
from werkzeug.exceptions import HTTPException

from wiki.config import Settings
from wiki.exceptions import ContentNotFoundError
from wiki.rendering import CachedRenderer, MarkdownItRenderer
from wiki.repository import FileSystemRepository
from wiki.security import SecurityHeaders
from wiki.service import WikiService
from wiki.views import create_blueprint


def build_service(settings: Settings) -> WikiService:
    """Monta o grafo de objetos do domínio (*composition root*).

    Args:
        settings: Configuração da aplicação.

    Returns:
        Um :class:`~wiki.service.WikiService` com repositório de arquivos e renderizador
        de Markdown com cache.

    Raises:
        ConfigurationError: Se a pasta de conteúdo não existir.
    """
    repository = FileSystemRepository(settings.content_dir)
    renderer = CachedRenderer(
        MarkdownItRenderer(allow_html=settings.allow_html),
        document_cache_size=settings.cache_size,
    )
    return WikiService(repository, renderer)


def create_app(settings: Settings | None = None) -> Flask:
    """*Application factory* do Flask.

    Os arquivos estáticos ficam em ``/_static`` (e não em ``/static``) para não colidir
    com uma pasta ``static`` dentro do conteúdo publicado.

    Args:
        settings: Configuração. Se omitida, é lida das variáveis de ambiente ``WIKI_*``.

    Returns:
        A aplicação WSGI configurada.

    Raises:
        ConfigurationError: Se a configuração for inválida.
    """
    settings = settings or Settings.from_env()
    app = Flask(__name__, static_url_path="/_static")
    app.extensions["wiki.settings"] = settings

    app.register_blueprint(create_blueprint(build_service(settings)))
    SecurityHeaders(settings).install(app)
    _register_template_context(app, settings)
    _register_error_handlers(app)
    return app


def _register_template_context(app: Flask, settings: Settings) -> None:
    """Disponibiliza em todos os templates o título, o idioma e a URL do tema."""

    @app.context_processor
    def inject_globals() -> dict[str, str]:
        theme = settings.theme_css
        if not settings.theme_is_remote:
            theme = url_for("static", filename=theme)
        return {
            "site_title": settings.site_title,
            "language": settings.language,
            "theme_href": theme,
        }


def _register_error_handlers(app: Flask) -> None:
    """Converte "conteúdo não encontrado" (e demais erros HTTP) em páginas amigáveis."""

    @app.errorhandler(ContentNotFoundError)
    @app.errorhandler(404)
    def not_found(_error: Exception) -> tuple[str, int]:
        return render_template("error.html", status=404, message="Página não encontrada."), 404

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException) -> tuple[str, int]:
        status = error.code or 500
        return render_template("error.html", status=status, message=error.name), status
