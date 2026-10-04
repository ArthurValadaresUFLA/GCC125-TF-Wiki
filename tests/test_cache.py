"""Tests for wiki.cache."""

from __future__ import annotations

import pytest

from wiki.cache import LRUCache


def test_invalid_size() -> None:
    with pytest.raises(ValueError):
        LRUCache[str, int](0)


def test_computes_only_once() -> None:
    cache: LRUCache[str, int] = LRUCache(2)
    calls: list[str] = []

    def factory() -> int:
        calls.append("x")
        return 42

    assert cache.get_or_compute("a", factory) == 42
    assert cache.get_or_compute("a", factory) == 42
    assert len(calls) == 1


def test_evicts_least_recently_used() -> None:
    cache: LRUCache[str, int] = LRUCache(2)
    cache.get_or_compute("a", lambda: 1)
    cache.get_or_compute("b", lambda: 2)
    cache.get_or_compute("a", lambda: 1)  # "a" becomes the most recently used
    cache.get_or_compute("c", lambda: 3)  # evicts "b"
    assert "a" in cache
    assert "c" in cache
    assert "b" not in cache
    assert len(cache) == 2


def test_caches_none_values() -> None:
    cache: LRUCache[str, str | None] = LRUCache(2)
    calls: list[str] = []

    def factory() -> None:
        calls.append("x")

    cache.get_or_compute("a", factory)
    cache.get_or_compute("a", factory)
    assert len(calls) == 1


def test_clear() -> None:
    cache: LRUCache[str, int] = LRUCache(2)
    cache.get_or_compute("a", lambda: 1)
    cache.clear()
    assert len(cache) == 0
