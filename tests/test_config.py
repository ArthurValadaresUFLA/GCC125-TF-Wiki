"""Testes de wiki.config."""

from __future__ import annotations

import unittest
from pathlib import Path

from wiki.config import DEFAULT_THEME_CSS, Settings
from wiki.exceptions import ConfigurationError


class SettingsFromEnvTests(unittest.TestCase):
    """Leitura de variáveis de ambiente."""

    def test_defaults(self) -> None:
        settings = Settings.from_env({})
        self.assertEqual(settings.content_dir, Path("data"))
        self.assertEqual(settings.site_title, "Wiki")
        self.assertEqual(settings.language, "pt-BR")
        self.assertFalse(settings.allow_html)
        self.assertEqual(settings.theme_css, DEFAULT_THEME_CSS)
        self.assertEqual(settings.cache_size, 128)

    def test_reads_all_variables(self) -> None:
        settings = Settings.from_env(
            {
                "WIKI_DIR": "/srv/docs",
                "WIKI_TITLE": "Base",
                "WIKI_LANG": "en",
                "WIKI_ALLOW_HTML": "yes",
                "WIKI_THEME_CSS": "https://cdn.example/tema.css",
                "WIKI_CACHE_SIZE": "8",
            }
        )
        self.assertEqual(settings.content_dir, Path("/srv/docs"))
        self.assertEqual(settings.site_title, "Base")
        self.assertEqual(settings.language, "en")
        self.assertTrue(settings.allow_html)
        self.assertTrue(settings.theme_is_remote)
        self.assertEqual(settings.cache_size, 8)

    def test_boolean_spellings(self) -> None:
        for raw, expected in [("1", True), ("TRUE", True), ("on", True), ("0", False), ("Não", False)]:
            with self.subTest(raw=raw):
                self.assertIs(Settings.from_env({"WIKI_ALLOW_HTML": raw}).allow_html, expected)

    def test_invalid_boolean(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings.from_env({"WIKI_ALLOW_HTML": "talvez"})

    def test_invalid_cache_size(self) -> None:
        for raw in ["abc", "0", "-3"]:
            with self.subTest(raw=raw), self.assertRaises(ConfigurationError):
                Settings.from_env({"WIKI_CACHE_SIZE": raw})

    def test_local_theme_is_not_remote(self) -> None:
        self.assertFalse(Settings(content_dir=Path("x")).theme_is_remote)

    def test_direct_construction_is_validated(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(content_dir=Path("x"), cache_size=0)
        with self.assertRaises(ConfigurationError):
            Settings(content_dir=Path("x"), theme_css="")


if __name__ == "__main__":
    unittest.main()
