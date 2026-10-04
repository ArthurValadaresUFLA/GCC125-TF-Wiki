"""Fixtures shared across the test suite.

We do not use the ``pytest-flask`` plugin: it has seen minimal maintenance since its
last release (Dec 2023), and Flask itself already provides everything it used to add.
``client`` is just ``app.test_client()``; to inspect rendered templates, we hook into
the ``flask.template_rendered`` signal directly (via ``captured_templates``), which
only relies on ``blinker`` — a mandatory dependency of Flask 2.3+.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from flask import Flask, template_rendered
from flask.testing import FlaskClient


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    """A temporary "root" folder. Files "outside" the wiki (to test path/symlink
    escapes) can be created here."""
    return tmp_path


@pytest.fixture
def content_dir(workdir: Path) -> Path:
    """Subfolder of ``workdir`` holding the wiki's content. Empty by default — each
    test module populates it as needed (via ``write_tree``)."""
    content = workdir / "content"
    content.mkdir()
    return content


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Flask's standard test client, built from the ``app`` fixture each module defines."""
    return app.test_client()


@contextmanager
def captured_templates(app: Flask) -> Iterator[list[str]]:
    """Record, via the `template_rendered` signal, the names of templates rendered
    within the `with` block. Replaces the `response.templates` that pytest-flask used
    to provide."""
    recorded: list[str] = []

    def record(_sender: Flask, template: object, **_extra: object) -> None:
        recorded.append(getattr(template, "name", None))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)
