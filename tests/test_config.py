"""Tests for wiki.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from wiki.config import DEFAULT_THEME_CSS, Settings
from wiki.exceptions import ConfigurationError


def test_defaults() -> None:
    settings = Settings.from_env({})
    assert settings.content_dir == Path("data")
    assert settings.site_title == "Wiki"
    assert settings.language == "en-GB"
    assert settings.allow_html is False
    assert settings.theme_css == DEFAULT_THEME_CSS
    assert settings.cache_size == 128


def test_reads_all_variables() -> None:
    settings = Settings.from_env(
        {
            "WIKI_DIR": "/srv/docs",
            "WIKI_TITLE": "Base",
            "WIKI_LANG": "fr",
            "WIKI_ALLOW_HTML": "yes",
            "WIKI_THEME_CSS": "https://cdn.example/theme.css",
            "WIKI_CACHE_SIZE": "8",
        }
    )
    assert settings.content_dir == Path("/srv/docs")
    assert settings.site_title == "Base"
    assert settings.language == "fr"
    assert settings.allow_html is True
    assert settings.theme_is_remote is True
    assert settings.cache_size == 8


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("TRUE", True),
        ("on", True),
        ("0", False),
        ("OFF", False),
    ],
)
def test_boolean_spellings(raw: str, expected: bool) -> None:
    settings = Settings.from_env({"WIKI_ALLOW_HTML": raw})
    assert settings.allow_html is expected


def test_invalid_boolean() -> None:
    with pytest.raises(ConfigurationError):
        Settings.from_env({"WIKI_ALLOW_HTML": "maybe"})


@pytest.mark.parametrize("raw", ["abc", "0", "-3"])
def test_invalid_cache_size(raw: str) -> None:
    with pytest.raises(ConfigurationError):
        Settings.from_env({"WIKI_CACHE_SIZE": raw})


def test_local_theme_is_not_remote() -> None:
    assert Settings(content_dir=Path("x")).theme_is_remote is False


def test_direct_construction_rejects_invalid_cache_size() -> None:
    with pytest.raises(ConfigurationError):
        Settings(content_dir=Path("x"), cache_size=0)


def test_direct_construction_rejects_empty_theme_css() -> None:
    with pytest.raises(ConfigurationError):
        Settings(content_dir=Path("x"), theme_css="")
