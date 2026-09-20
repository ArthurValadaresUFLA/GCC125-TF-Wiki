"""Utilidades compartilhadas pelos testes."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


def write_tree(root: Path, files: dict[str, str | bytes]) -> None:
    """Cria, dentro de ``root``, os arquivos descritos em ``files`` (caminho -> conteúdo)."""
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")


class ContentDirTestCase(unittest.TestCase):
    """Base de testes que precisam de uma pasta de conteúdo temporária.

    Cria ``self.workdir`` (pasta descartada ao final) e ``self.content`` (dentro dela).
    Arquivos "de fora" da raiz podem ser criados em ``self.workdir`` para testar fugas.
    """

    def setUp(self) -> None:
        """Cria as pastas temporárias."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.workdir = Path(tmp.name)
        self.content = self.workdir / "content"
        self.content.mkdir()
