"""A simple, thread-safe least-recently-used (LRU) cache."""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Generic, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    """A size-bounded mapping that evicts the least recently used entry when full.

    Recency is tracked on both reads and writes: fetching an existing key moves it to
    the "most recently used" end, so a cache under constant pressure keeps whatever is
    actually being requested rather than whatever was inserted first.

    The value for a missing key is computed **outside** the lock: two threads may end
    up computing the same key at the same time (duplicated, but harmless, work), yet
    neither thread is ever blocked waiting for another to finish an expensive
    computation such as rendering a page. This trades a small amount of redundant work
    for much better concurrency under load.

    Args:
        max_size: Maximum number of entries retained. Must be at least 1.

    Raises:
        ValueError: If ``max_size`` is less than 1.

    Example:
        >>> cache: LRUCache[str, int] = LRUCache(max_size=2)
        >>> cache.get_or_compute("a", lambda: 1)
        1
        >>> "a" in cache
        True
    """

    def __init__(self, max_size: int) -> None:
        if max_size < 1:
            raise ValueError("max_size must be greater than zero")
        self._max_size = max_size
        self._data: OrderedDict[K, V] = OrderedDict()
        self._lock = threading.Lock()

    def get_or_compute(self, key: K, factory: Callable[[], V]) -> V:
        """Return the cached value for ``key``, computing and storing it if absent.

        Args:
            key: Lookup key.
            factory: Zero-argument callable that produces the value when the key is
                not already cached. Only invoked on a cache miss.

        Returns:
            The value associated with ``key`` — either the cached one, or the one just
            produced by ``factory``.
        """
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]

        value = factory()

        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self._max_size:
                self._data.popitem(last=False)
        return value

    def clear(self) -> None:
        """Remove every entry from the cache."""
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        """Return how many entries are currently cached."""
        with self._lock:
            return len(self._data)

    def __contains__(self, key: object) -> bool:
        """Return whether ``key`` is cached, without affecting recency order."""
        with self._lock:
            return key in self._data
