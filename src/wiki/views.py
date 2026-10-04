"""The HTTP layer: the application's routes, implemented as class-based views.

=========================  ==================================================
Route                      Behaviour
=========================  ==================================================
``/``                      Index: pages and downloadable files.
``/<name>``                A page (``guia/x``) or a file download (``x.md``).
=========================  ==================================================

Each view receives the :class:`~wiki.service.WikiService` through its constructor
(dependency injection), and is instantiated only once per application, rather than
once per request (``init_every_request = False``) — the view itself is stateless, so
there is nothing to gain from recreating it on every call.
"""

from __future__ import annotations

from flask import Blueprint, Response, render_template, request, send_file
from flask.views import View

from wiki.models import Download, Page
from wiki.service import WikiService


def _html_response(html: str) -> Response:
    """Wrap HTML with an ``ETag``, enabling conditional ``304 Not Modified`` responses.

    ``Cache-Control: no-cache`` makes the browser always revalidate with the server,
    so an edit to the underlying file is reflected immediately — but without
    re-transferring the body when nothing has actually changed.
    """
    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-cache"
    response.add_etag()
    response.make_conditional(request)
    return response


class _ServiceView(View):
    """Base class for the views: holds the injected service and avoids re-instantiation."""

    init_every_request = False

    def __init__(self, service: WikiService) -> None:
        self._service = service


class IndexView(_ServiceView):
    """``GET /`` — lists the pages (grouped by folder) and the downloadable files."""

    def dispatch_request(self) -> Response:
        """Render the index page."""
        catalog = self._service.catalog()
        return _html_response(render_template("index.html", catalog=catalog))


class PageView(_ServiceView):
    """``GET /<name>`` — displays a page, or sends a file back as an attachment."""

    def dispatch_request(self, name: str) -> Response:  # type: ignore[override]
        """Resolve ``name`` and respond according to the kind of resource found.

        Args:
            name: Path segment received in the URL.
        """
        resource = self._service.resolve(name)
        if isinstance(resource, Download):
            # Always as an attachment: HTML/SVG sent as a download never executes
            # with the wiki's own origin, unlike a page rendered inline.
            return send_file(resource.path, as_attachment=True, download_name=resource.filename)
        return _html_response(self._render_page(resource))

    @staticmethod
    def _render_page(page: Page) -> str:
        return render_template("page.html", page=page, print_mode=False)


def create_blueprint(service: WikiService) -> Blueprint:
    """Create the blueprint holding the routes, already bound to the given service.

    Args:
        service: Service instance injected into all three views.

    Returns:
        The ``Blueprint``, ready to be registered on the application.
    """
    blueprint = Blueprint("wiki", __name__)
    blueprint.add_url_rule("/", view_func=IndexView.as_view("index", service))
    blueprint.add_url_rule("/<path:name>", view_func=PageView.as_view("page", service))
    return blueprint
