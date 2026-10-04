"""Access to the published content (*Repository* pattern).

:class:`ContentRepository` defines the contract the rest of the application sees;
:class:`FileSystemRepository` is the implementation that reads from a local folder.
All of the path-safety logic — path traversal, hidden files, symlinks that escape the
content root — is concentrated here, so every other layer can treat a validated name
as trustworthy.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from wiki.exceptions import ConfigurationError, ContentNotFoundError
from wiki.models import SourceFile


class ContentRepository(ABC):
    """Contract for accessing content, independent of where it is actually stored.

    Implementing this against, say, an in-memory dictionary or a remote object store
    is enough to reuse :class:`wiki.service.WikiService` unchanged — see
    ``tests/test_service.py`` for an in-memory example used purely for unit testing.
    """

    @abstractmethod
    def list_files(self) -> tuple[SourceFile, ...]:
        """List every visible file, ordered by folder and then by name."""

    @abstractmethod
    def stat(self, name: str) -> SourceFile:
        """Return the metadata for a file.

        Args:
            name: Path relative to the content root, using ``/`` as the separator.

        Raises:
            ContentNotFoundError: If the file does not exist or must not be exposed.
        """

    @abstractmethod
    def read_text(self, name: str) -> str:
        """Read a UTF-8 text file (with or without a byte-order mark).

        Raises:
            ContentNotFoundError: If the file does not exist or must not be exposed.
        """

    @abstractmethod
    def path_of(self, name: str) -> Path:
        """Return the absolute, validated path of a file, ready to be sent to a client.

        Raises:
            ContentNotFoundError: If the file does not exist or must not be exposed.
        """


def _is_hidden(part: str) -> bool:
    """Names starting with a dot (``.git``, ``.env``, …) are never published."""
    return part.startswith(".")


def _sort_key(source: SourceFile) -> tuple[str, str]:
    """Sort by folder (content root first), then case-insensitively by filename."""
    folder, _, base = source.name.rpartition("/")
    return folder.casefold(), base.casefold()


class FileSystemRepository(ContentRepository):
    """A repository that publishes the contents of a folder on the local filesystem.

    Rules governing exposure:

    * Files and folders whose name starts with ``.`` are ignored entirely.
    * A symlink to a *file* is only accepted if its target resolves to somewhere
      inside the content root — this is the primary defence against a symlink being
      used to read files elsewhere on disk (e.g. ``/etc/passwd``).
    * A symlink to a *folder* is never followed while listing content
      (``os.walk(..., followlinks=False)``), which also prevents infinite loops from
      a symlink that points back to an ancestor of itself.

    Args:
        root: Root folder of the content.

    Raises:
        ConfigurationError: If ``root`` is not an existing folder.
    """

    def __init__(self, root: Path | str) -> None:
        resolved = Path(root).expanduser().resolve()
        if not resolved.is_dir():
            raise ConfigurationError(f"The content folder does not exist: {resolved}")
        self._root = resolved

    @property
    def root(self) -> Path:
        """Root folder (absolute, already-resolved path)."""
        return self._root

    def list_files(self) -> tuple[SourceFile, ...]:
        """Walk the root folder and return the visible files."""
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
                    continue  # broken link, escapes the root, or removed mid-scan
        found.sort(key=_sort_key)
        return tuple(found)

    def stat(self, name: str) -> SourceFile:
        """See :meth:`ContentRepository.stat`."""
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
        """See :meth:`ContentRepository.read_text`."""
        _, path = self._locate(name)
        try:
            return path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            raise ContentNotFoundError(name) from None

    def path_of(self, name: str) -> Path:
        """See :meth:`ContentRepository.path_of`."""
        return self._locate(name)[1]

    def _locate(self, name: str) -> tuple[str, Path]:
        """Validate ``name`` and turn it into a real path inside the content root.

        This is the single choke point through which every public method passes a
        client-supplied name, which is what makes the security guarantees of this
        class hold: nothing downstream ever sees an unvalidated path.

        Returns:
            The normalised name (relative, ``/``-separated) and the resolved absolute
            path.

        Raises:
            ContentNotFoundError: For empty, absolute, ``..``-containing, hidden, or
                non-existent names, and for any name whose final resolved target
                escapes the content root.
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
