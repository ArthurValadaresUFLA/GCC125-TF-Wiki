"""Wiki: a web service that publishes a folder of Markdown files as HTML pages.

The entry point is the *application factory* :func:`wiki.app.create_app`, re-exported
here for convenience so that WSGI servers can locate it without importing the
``wiki.app`` module directly::

    gunicorn "wiki:create_app()"

See :mod:`wiki.config` for the environment variables that configure the application,
and :mod:`wiki.app` for how the dependency graph (repository, renderer, service and
views) is assembled.
"""

from wiki.app import create_app

__all__ = ["create_app"]
