"""Testes de wiki.cache."""

from __future__ import annotations

import unittest

from wiki.cache import LRUCache


class LRUCacheTests(unittest.TestCase):
    """Comportamento do cache LRU."""

    def test_invalid_size(self) -> None:
        with self.assertRaises(ValueError):
            LRUCache[str, int](0)

    def test_computes_only_once(self) -> None:
        cache: LRUCache[str, int] = LRUCache(2)
        calls: list[str] = []

        def factory() -> int:
            calls.append("x")
            return 42

        self.assertEqual(cache.get_or_compute("a", factory), 42)
        self.assertEqual(cache.get_or_compute("a", factory), 42)
        self.assertEqual(len(calls), 1)

    def test_evicts_least_recently_used(self) -> None:
        cache: LRUCache[str, int] = LRUCache(2)
        cache.get_or_compute("a", lambda: 1)
        cache.get_or_compute("b", lambda: 2)
        cache.get_or_compute("a", lambda: 1)  # "a" vira o mais recente
        cache.get_or_compute("c", lambda: 3)  # expulsa "b"
        self.assertIn("a", cache)
        self.assertIn("c", cache)
        self.assertNotIn("b", cache)
        self.assertEqual(len(cache), 2)

    def test_caches_none_values(self) -> None:
        cache: LRUCache[str, str | None] = LRUCache(2)
        calls: list[str] = []

        def factory() -> None:
            calls.append("x")

        cache.get_or_compute("a", factory)
        cache.get_or_compute("a", factory)
        self.assertEqual(len(calls), 1)

    def test_clear(self) -> None:
        cache: LRUCache[str, int] = LRUCache(2)
        cache.get_or_compute("a", lambda: 1)
        cache.clear()
        self.assertEqual(len(cache), 0)


if __name__ == "__main__":
    unittest.main()
