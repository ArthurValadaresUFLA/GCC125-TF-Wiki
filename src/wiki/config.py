"""Application configuration, read from environment variables.

All configuration happens once, at container start-up, through variables prefixed
with ``WIKI_``. :class:`Settings` is immutable and has no dependency on Flask, which
makes it trivial to construct directly in tests without spinning up a real
application.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from wiki.exceptions import ConfigurationError

DEFAULT_CONTENT_DIR = "data"
DEFAULT_THEME_CSS = "vendor/picocss/pico.min.css"

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _parse_bool(name: str, raw: str) -> bool:
    """Convert text into a boolean, accepting the most common spellings.

    The usual English spellings (``true``/``false``, ``yes``/``no``, ``on``/``off``,
    ``1``/``0``) are accepted, case-insensitively.

    Args:
        name: Name of the variable (used in the error message).
        raw: Raw value read from the environment.

    Returns:
        The corresponding boolean value.

    Raises:
        ConfigurationError: If the text is not a recognised boolean spelling.
    """
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ConfigurationError(f"{name}: invalid boolean value: {raw!r}")


def _parse_positive_int(name: str, raw: str) -> int:
    """Convert text into a strictly positive integer.

    Args:
        name: Name of the variable (used in the error message).
        raw: Raw value read from the environment.

    Returns:
        The corresponding integer.

    Raises:
        ConfigurationError: If the text is not an integer greater than zero.
    """
    try:
        value = int(raw)
    except ValueError:
        raise ConfigurationError(f"{name}: expected an integer, got {raw!r}") from None
    if value < 1:
        raise ConfigurationError(f"{name}: the value must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime parameters for the application.

    Instances are immutable (``frozen=True``) and validated in :meth:`__post_init__`,
    so an invalid :class:`Settings` can never exist for long enough to cause confusing
    failures elsewhere — the error surfaces at the point of construction, whether that
    is :meth:`from_env` or a direct call in a test.

    Attributes:
        content_dir: Folder containing the published ``.md`` files and any other
            files made available for download.
        site_title: Title shown in the page header and in the browser tab.
        language: Language code used for the HTML ``lang`` attribute.
        allow_html: When ``True``, raw HTML embedded in Markdown is preserved as-is.
            Defaults to ``False``, which is the safe behaviour for untrusted content —
            see :class:`wiki.rendering.MarkdownItRenderer` for how escaping works, and
            :class:`wiki.security.SecurityHeaders` for the CSP that still blocks
            inline scripts even when this is enabled.
        theme_css: Stylesheet for the theme. Either a path relative to the ``static``
            folder, or a full ``http(s)://`` URL (see :attr:`theme_is_remote`).
        cache_size: Maximum number of rendered pages kept in memory — forwarded to
            :class:`wiki.rendering.CachedRenderer`.
    """

    content_dir: Path
    site_title: str = "Wiki"
    language: str = "en-GB"
    allow_html: bool = False
    theme_css: str = DEFAULT_THEME_CSS
    cache_size: int = 128

    def __post_init__(self) -> None:
        """Validate invariants that hold regardless of where the values came from."""
        if self.cache_size < 1:
            raise ConfigurationError("cache_size must be greater than zero")
        if not self.theme_css:
            raise ConfigurationError("theme_css must not be empty")

    @property
    def theme_is_remote(self) -> bool:
        """Whether the theme is loaded from an external URL rather than bundled locally."""
        return self.theme_css.startswith(("http://", "https://"))

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Build the settings from environment variables.

        Recognised variables: ``WIKI_DIR``, ``WIKI_TITLE``, ``WIKI_LANG``,
        ``WIKI_ALLOW_HTML``, ``WIKI_THEME_CSS`` and ``WIKI_CACHE_SIZE``. Any variable
        that is absent falls back to the corresponding default on :class:`Settings`,
        so a bare deployment with no environment configured at all still produces a
        valid instance.

        Args:
            environ: Mapping to read values from. Defaults to ``os.environ``; tests
                typically pass a plain ``dict`` instead, to avoid touching real
                process-wide state.

        Returns:
            A validated :class:`Settings` instance.

        Raises:
            ConfigurationError: If any value fails to parse.
        """
        env = os.environ if environ is None else environ
        defaults = cls(content_dir=Path(DEFAULT_CONTENT_DIR))

        allow_html = defaults.allow_html
        if "WIKI_ALLOW_HTML" in env:
            allow_html = _parse_bool("WIKI_ALLOW_HTML", env["WIKI_ALLOW_HTML"])

        cache_size = defaults.cache_size
        if "WIKI_CACHE_SIZE" in env:
            cache_size = _parse_positive_int("WIKI_CACHE_SIZE", env["WIKI_CACHE_SIZE"])

        return cls(
            content_dir=Path(env.get("WIKI_DIR", DEFAULT_CONTENT_DIR)),
            site_title=env.get("WIKI_TITLE", defaults.site_title),
            language=env.get("WIKI_LANG", defaults.language),
            allow_html=allow_html,
            theme_css=env.get("WIKI_THEME_CSS", defaults.theme_css),
            cache_size=cache_size,
        )
