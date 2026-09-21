"""Acesso ao conteúdo publicado (padrão *Repository*).

:class:`ContentRepository` define o contrato que o restante da aplicação enxerga;
:class:`FileSystemRepository` é a implementação que lê de uma pasta local. Toda a
lógica de segurança de caminhos (path traversal, arquivos ocultos, *symlinks* que
escapam da raiz) fica concentrada aqui.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from wiki.exceptions import ConfigurationError, ContentNotFoundError
from wiki.models import SourceFile


class ContentRepository(ABC):
    """Contrato de acesso ao conteúdo, independente de onde ele está armazenado."""

    @abstractmethod
    def list_files(self) -> tuple[SourceFile, ...]:
        """Lista todos os arquivos visíveis, ordenados por pasta e nome."""

    @abstractmethod
    def stat(self, name: str) -> SourceFile:
        """Devolve os metadados de um arquivo.

        Args:
            name: Caminho relativo à raiz, com ``/`` como separador.

        Raises:
            ContentNotFoundError: Se o arquivo não existir ou não puder ser exposto.
        """

    @abstractmethod
    def read_text(self, name: str) -> str:
        """Lê um arquivo de texto UTF-8 (com ou sem BOM).

        Raises:
            ContentNotFoundError: Se o arquivo não existir ou não puder ser exposto.
        """

    @abstractmethod
    def path_of(self, name: str) -> Path:
        """Devolve o caminho absoluto e validado de um arquivo, para envio ao cliente.

        Raises:
            ContentNotFoundError: Se o arquivo não existir ou não puder ser exposto.
        """


def _is_hidden(part: str) -> bool:
    """Nomes iniciados por ponto (``.git``, ``.env``…) nunca são publicados."""
    return part.startswith(".")


def _sort_key(source: SourceFile) -> tuple[str, str]:
    """Ordena por pasta (a raiz primeiro) e, dentro dela, por nome sem distinguir caixa."""
    folder, _, base = source.name.rpartition("/")
    return folder.casefold(), base.casefold()


class FileSystemRepository(ContentRepository):
    """Repositório que publica o conteúdo de uma pasta do sistema de arquivos.

    Regras de exposição:

    * arquivos e pastas cujo nome começa com ``.`` são ignorados;
    * *symlinks* para arquivos são aceitos apenas se o destino estiver dentro da raiz;
    * *symlinks* para pastas não são percorridos na listagem.

    Args:
        root: Pasta raiz do conteúdo.

    Raises:
        ConfigurationError: Se ``root`` não for uma pasta existente.
    """

    def __init__(self, root: Path | str) -> None:
        resolved = Path(root).expanduser().resolve()
        if not resolved.is_dir():
            raise ConfigurationError(f"A pasta de conteúdo não existe: {resolved}")
        self._root = resolved

    @property
    def root(self) -> Path:
        """Pasta raiz (caminho absoluto, já resolvido)."""
        return self._root

    def list_files(self) -> tuple[SourceFile, ...]:
        """Percorre a raiz e devolve os arquivos visíveis."""
        found: list[SourceFile] = []
        for dirpath, dirnames, filenames in os.walk(self._root, followlinks=False):
            dirnames[:] = [d for d in dirnames if not _is_hidden(d)]
            for filename in filenames:
                if _is_hidden(filename):
                    continue
                path = Path(dirpath) / filename
                relative = path.relative_to(self._root).as_posix()
                try:
                    found.append(self.stat(relative))
                except ContentNotFoundError:
                    continue  # link quebrado, fora da raiz ou removido durante a varredura
        found.sort(key=_sort_key)
        return tuple(found)

    def stat(self, name: str) -> SourceFile:
        """Ver :meth:`ContentRepository.stat`."""
        normalized, path = self._locate(name)
        try:
            info = path.stat()
        except OSError:
            raise ContentNotFoundError(name) from None
        return SourceFile(
            name=normalized,
            size=info.st_size,
            modified=datetime.fromtimestamp(info.st_mtime, tz=UTC),
        )

    def read_text(self, name: str) -> str:
        """Ver :meth:`ContentRepository.read_text`."""
        _, path = self._locate(name)
        try:
            return path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            raise ContentNotFoundError(name) from None

    def path_of(self, name: str) -> Path:
        """Ver :meth:`ContentRepository.path_of`."""
        return self._locate(name)[1]

    def _locate(self, name: str) -> tuple[str, Path]:
        """Valida ``name`` e o converte em um caminho real dentro da raiz.

        Returns:
            O nome normalizado (relativo, com ``/``) e o caminho absoluto resolvido.

        Raises:
            ContentNotFoundError: Para nomes vazios, absolutos, com ``..``, ocultos,
                inexistentes ou cujo destino final escape da raiz.
        """
        if not name or "\x00" in name:
            raise ContentNotFoundError(name)

        posix = PurePosixPath(name)
        if posix.is_absolute() or any(p == ".." or _is_hidden(p) for p in posix.parts):
            raise ContentNotFoundError(name)

        try:
            real = (self._root / Path(*posix.parts)).resolve(strict=True)
            relative = real.relative_to(self._root)
        except (OSError, ValueError, RuntimeError):
            raise ContentNotFoundError(name) from None

        if not real.is_file() or any(_is_hidden(p) for p in relative.parts):
            raise ContentNotFoundError(name)
        return "/".join(posix.parts), real
