"""Utilities shared by the test suite."""

from __future__ import annotations

from pathlib import Path


def write_tree(root: Path, files: dict[str, str | bytes]) -> None:
    """Create, inside ``root``, the files described in ``files`` (path -> content)."""
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
