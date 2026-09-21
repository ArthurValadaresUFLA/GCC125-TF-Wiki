"""Wiki: serviço web que publica uma pasta de arquivos Markdown como páginas HTML.

O ponto de entrada é a *application factory* :func:`wiki.app.create_app`, reexportada
aqui por conveniência::

    gunicorn "wiki:create_app()"
"""

from wiki.app import create_app

__all__ = ["create_app"]
