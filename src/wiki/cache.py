"""Cache LRU (*least recently used*) simples e seguro para uso com várias threads."""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Generic, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    """Dicionário de tamanho limitado que descarta o item menos usado recentemente.

    O cálculo do valor ausente acontece **fora** do lock: duas threads podem calcular a
    mesma chave ao mesmo tempo (trabalho duplicado, porém inofensivo), mas nenhuma
    fica bloqueada esperando a outra terminar uma renderização.

    Args:
        max_size: Número máximo de itens mantidos. Deve ser maior que zero.

    Raises:
        ValueError: Se ``max_size`` for menor que 1.
    """

    def __init__(self, max_size: int) -> None:
        if max_size < 1:
            raise ValueError("max_size deve ser maior que zero")
        self._max_size = max_size
        self._data: OrderedDict[K, V] = OrderedDict()
        self._lock = threading.Lock()

    def get_or_compute(self, key: K, factory: Callable[[], V]) -> V:
        """Devolve o valor em cache ou o calcula com ``factory`` e o armazena.

        Args:
            key: Chave de busca.
            factory: Função sem argumentos que produz o valor quando a chave não existe.

        Returns:
            O valor associado à chave.
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
        """Remove todos os itens."""
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        """Quantidade de itens atualmente armazenados."""
        with self._lock:
            return len(self._data)

    def __contains__(self, key: object) -> bool:
        """Diz se a chave está em cache, sem alterar a ordem de uso."""
        with self._lock:
            return key in self._data
