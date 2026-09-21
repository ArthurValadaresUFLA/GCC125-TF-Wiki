"""Configuração da aplicação, lida de variáveis de ambiente.

Toda a configuração é feita na criação do container, por variáveis com o prefixo
``WIKI_``. A classe :class:`Settings` é imutável e não depende do Flask, o que a torna
fácil de instanciar em testes.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from wiki.exceptions import ConfigurationError

DEFAULT_CONTENT_DIR = "data"
DEFAULT_THEME_CSS = "vendor/picocss/current/pico.min.css"

_TRUE_VALUES = frozenset({"1", "true", "yes", "on", "sim"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off", "nao", "não"})


def _parse_bool(name: str, raw: str) -> bool:
    """Converte texto em booleano, aceitando as grafias mais comuns.

    Args:
        name: Nome da variável (usado na mensagem de erro).
        raw: Valor bruto lido do ambiente.

    Returns:
        O valor booleano correspondente.

    Raises:
        ConfigurationError: Se o texto não for uma grafia booleana conhecida.
    """
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ConfigurationError(f"{name}: valor booleano inválido: {raw!r}")


def _parse_positive_int(name: str, raw: str) -> int:
    """Converte texto em inteiro estritamente positivo.

    Args:
        name: Nome da variável (usado na mensagem de erro).
        raw: Valor bruto lido do ambiente.

    Returns:
        O inteiro correspondente.

    Raises:
        ConfigurationError: Se o texto não for um inteiro maior que zero.
    """
    try:
        value = int(raw)
    except ValueError:
        raise ConfigurationError(f"{name}: esperado um inteiro, recebido {raw!r}") from None
    if value < 1:
        raise ConfigurationError(f"{name}: o valor deve ser maior que zero")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Parâmetros de execução da aplicação.

    Attributes:
        content_dir: Pasta com os arquivos ``.md`` e os demais arquivos publicados.
        site_title: Título exibido no cabeçalho e na aba do navegador.
        language: Código de idioma do atributo ``lang`` do HTML.
        allow_html: Se ``True``, HTML cru dentro do Markdown é preservado. Por padrão é
            escapado, o que é o comportamento seguro para conteúdo não confiável.
        theme_css: Folha de estilo do tema. Pode ser um caminho relativo à pasta
            ``static`` ou uma URL ``http(s)://`` completa.
        cache_size: Quantidade máxima de páginas renderizadas mantidas em memória.
    """

    content_dir: Path
    site_title: str = "Wiki"
    language: str = "pt-BR"
    allow_html: bool = False
    theme_css: str = DEFAULT_THEME_CSS
    cache_size: int = 128

    def __post_init__(self) -> None:
        """Valida invariantes que independem da origem dos valores."""
        if self.cache_size < 1:
            raise ConfigurationError("cache_size deve ser maior que zero")
        if not self.theme_css:
            raise ConfigurationError("theme_css não pode ser vazio")

    @property
    def theme_is_remote(self) -> bool:
        """Indica se o tema é carregado de uma URL externa."""
        return self.theme_css.startswith(("http://", "https://"))

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Constrói as configurações a partir de variáveis de ambiente.

        Variáveis reconhecidas: ``WIKI_DIR``, ``WIKI_TITLE``, ``WIKI_LANG``,
        ``WIKI_ALLOW_HTML``, ``WIKI_THEME_CSS`` e ``WIKI_CACHE_SIZE``.

        Args:
            environ: Mapeamento de onde ler os valores. Por padrão, ``os.environ``.

        Returns:
            Uma instância validada de :class:`Settings`.

        Raises:
            ConfigurationError: Se algum valor for inválido.
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
