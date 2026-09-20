#!/usr/bin/env python3
"""Gera ``pygments.css``: realce de código com tema claro e escuro.

O tema claro vale por padrão; o escuro é ativado por ``prefers-color-scheme: dark``
(somente em ``screen``, para que a impressão continue sempre clara).

Uso::

    python scripts/generate_pygments_css.py                       # padrão
    python scripts/generate_pygments_css.py --light friendly --dark monokai

A lista de estilos disponíveis está em https://pygments.org/styles/
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pygments.formatters import HtmlFormatter

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "src/wiki/static/css/pygments.css"


def _scoped_rules(css: str, selector: str) -> str:
    """Mantém só as regras do bloco de código, descartando as globais (``pre``, números de linha)."""
    return "\n".join(line for line in css.splitlines() if line.startswith(selector))


def build_css(light: str, dark: str, selector: str = ".highlight") -> str:
    """Monta o CSS com os dois estilos.

    Args:
        light: Nome do estilo do Pygments para o tema claro.
        dark: Nome do estilo do Pygments para o tema escuro.
        selector: Classe do bloco de código gerado pelo renderizador.

    Returns:
        O conteúdo completo do arquivo CSS.
    """
    light_css = _scoped_rules(HtmlFormatter(style=light).get_style_defs(selector), selector)
    dark_css = _scoped_rules(HtmlFormatter(style=dark).get_style_defs(selector), selector)
    dark_indented = "\n".join(f"  {line}" if line else line for line in dark_css.splitlines())
    return (
        f"/* Gerado por scripts/generate_pygments_css.py — claro: {light}, escuro: {dark}. */\n"
        f"/* Não edite à mão; gere novamente com `make pygments`. */\n\n"
        f"{light_css}\n\n"
        f"@media screen and (prefers-color-scheme: dark) {{\n{dark_indented}\n}}\n"
    )


def main() -> None:
    """Ponto de entrada da linha de comando."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--light", default="default", help="estilo claro (padrão: %(default)s)")
    parser.add_argument("--dark", default="github-dark", help="estilo escuro (padrão: %(default)s)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="arquivo de saída")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_css(args.light, args.dark), encoding="utf-8")
    print(f"escrito: {args.output}")


if __name__ == "__main__":
    main()
