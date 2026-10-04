"""Application-specific exceptions.

Keeping these separate from the standard library's exceptions lets callers (views,
error handlers, tests) catch failures that originate from *this* application's domain
logic without accidentally swallowing unrelated errors such as a genuine ``OSError``
raised by a misbehaving disk.
"""

from __future__ import annotations


class WikiError(Exception):
    """Base class for every exception raised by this application.

    Catching :class:`WikiError` is a convenient way to distinguish "expected" failures
    (bad configuration, missing content) from unexpected bugs, without having to list
    every concrete subclass.
    """


class ConfigurationError(WikiError):
    """The application was given invalid or incomplete configuration.

    Raised, for example, when an environment variable holds a value that cannot be
    parsed (see :mod:`wiki.config`), or when the configured content directory does not
    exist on disk (see :class:`wiki.repository.FileSystemRepository`).
    """


class ContentNotFoundError(WikiError, LookupError):
    """The requested content does not exist, or must not be exposed.

    This covers both genuinely missing files and files that exist on disk but are
    deliberately hidden from the public API — dotfiles, symlinks that escape the
    content root, path-traversal attempts, and similar cases. Callers should not need
    to distinguish between "missing" and "hidden": both result in an HTTP 404.

    Inherits from :class:`LookupError` so it also behaves naturally alongside built-in
    lookup failures (e.g. in a ``try``/``except (KeyError, ContentNotFoundError)``).
    """
