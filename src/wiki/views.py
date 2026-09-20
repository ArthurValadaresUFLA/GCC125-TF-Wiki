"""Camada HTTP: as três rotas da aplicação, como *class-based views*.

=========================  ==================================================
Rota                       Comportamento
=========================  ==================================================
``/``                      Índice: páginas e arquivos para download.
``/<nome>``                Página (``guia/x``) ou download de arquivo (``x.md``).
=========================  ==================================================

Cada *view* recebe o :class:`~wiki.service.WikiService` no construtor (injeção de
dependência), e é instanciada uma única vez (``init_every_request = False``).
"""

from __future__ import annotations

from flask import Blueprint, Response, render_template, request, send_file
from flask.views import View

from wiki.models import Download, Page
from wiki.service import WikiService


def _html_response(html: str) -> Response:
    """Empacota HTML com ``ETag``, permitindo respostas ``304 Not Modified``.

    ``Cache-Control: no-cache`` faz o navegador revalidar sempre, de modo que uma edição
    no arquivo aparece imediatamente, mas sem retransferir o corpo se nada mudou.
    """
    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-cache"
    response.add_etag()
    return response.make_conditional(request)


class _ServiceView(View):
    """Base das *views*: guarda o serviço injetado e evita recriar a instância a cada request."""

    init_every_request = False

    def __init__(self, service: WikiService) -> None:
        self._service = service


class IndexView(_ServiceView):
    """``GET /`` — lista as páginas (por pasta) e os arquivos para download."""

    def dispatch_request(self) -> Response:
        """Renderiza o índice."""
        catalog = self._service.catalog()
        return _html_response(render_template("index.html", catalog=catalog))


class PageView(_ServiceView):
    """``GET /<nome>`` — exibe uma página ou envia um arquivo como anexo."""

    def dispatch_request(self, name: str) -> Response:  # type: ignore[override]
        """Resolve ``name`` e responde de acordo com o tipo de recurso encontrado.

        Args:
            name: Caminho recebido na URL.
        """
        resource = self._service.resolve(name)
        if isinstance(resource, Download):
            # Sempre como anexo: HTML/SVG enviados no download não executam na origem da wiki.
            return send_file(resource.path, as_attachment=True, download_name=resource.filename)
        return _html_response(self._render_page(resource))

    @staticmethod
    def _render_page(page: Page) -> str:
        return render_template("page.html", page=page, print_mode=False)


def create_blueprint(service: WikiService) -> Blueprint:
    """Cria o *blueprint* com as rotas, já ligado ao serviço informado.

    Args:
        service: Serviço injetado nas três *views*.

    Returns:
        O ``Blueprint`` pronto para ser registrado na aplicação.
    """
    blueprint = Blueprint("wiki", __name__)
    blueprint.add_url_rule("/", view_func=IndexView.as_view("index", service))
    blueprint.add_url_rule("/<path:name>", view_func=PageView.as_view("page", service))
    return blueprint
