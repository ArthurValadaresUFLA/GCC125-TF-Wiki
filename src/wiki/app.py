"""Application composition: the *application factory* and dependency wiring."""

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
    """Assemble the domain's object graph (the *composition root*).

    Args:
        settings: The application's configuration.

    Returns:
        A :class:`~wiki.service.WikiService` wired to a filesystem repository and a
        cached Markdown renderer.

    Raises:
        ConfigurationError: If the content folder does not exist.
    """
    repository = FileSystemRepository(settings.content_dir)
    renderer = CachedRenderer(
        MarkdownItRenderer(allow_html=settings.allow_html),
        document_cache_size=settings.cache_size,
    )
    return WikiService(repository, renderer)


def create_app(settings: Settings | None = None) -> Flask:
    """Flask *application factory*.

    Static assets are served from ``/_static`` rather than the default ``/static``,
    precisely so that they never collide with a folder literally named ``static``
    inside the *published content* — see
    ``tests/test_views.py::TestPage::test_static_assets_do_not_shadow_content_named_static``
    for the regression this guards against.

    Args:
        settings: Configuration to use. If omitted, it is read from the ``WIKI_*``
            environment variables (see :meth:`wiki.config.Settings.from_env`).

    Returns:
        The fully configured WSGI application.

    Raises:
        ConfigurationError: If the configuration is invalid.
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
    """Make the site title, language, and theme URL available in every template."""

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
    """Turn "content not found" (and every other HTTP error) into a friendly page.

    Two handlers are registered:

    * :func:`not_found` covers both the domain-specific
      :class:`~wiki.exceptions.ContentNotFoundError` and the generic HTTP 404, so a
      missing page and a genuinely unmatched route render the exact same message.
    * :func:`http_error` is the catch-all for any *other* :class:`HTTPException`
      (405 Method Not Allowed, 500 Internal Server Error, …). Flask dispatches to the
      most specific handler available, so this one only ever fires for status codes
      that are not 404.
    """

    @app.errorhandler(ContentNotFoundError)
    @app.errorhandler(404)
    def not_found(_error: Exception) -> tuple[str, int]:
        return render_template("error.html", status=404, message="Page not found."), 404

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException) -> tuple[str, int]:
        status = error.code or 500
        return render_template("error.html", status=status, message=error.name), status
