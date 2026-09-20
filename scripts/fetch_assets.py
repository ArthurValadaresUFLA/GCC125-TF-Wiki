#!/usr/bin/env python3
"""Baixa o tema Pico CSS e o salva em ``static/vendor`` (assets "vendorizados").

O tema é servido pela própria wiki, sem depender de CDN em tempo de execução. O
Dockerfile executa este script durante o *build*; em desenvolvimento use ``make assets``.

Uso::

    python scripts/fetch_assets.py                    # tema padrão
    python scripts/fetch_assets.py --variant jade     # variante de cor do Pico
    python scripts/fetch_assets.py --version 2.1.1

Variantes de cor: amber, azure, blue, fuchsia, green, grey, indigo, jade, lime, orange,
pink, pumpkin, purple, red, sand, slate, violet, yellow, zinc.

Usa apenas a biblioteca padrão. O arquivo é sempre gravado como
``pico.classless.min.css`` — o nome que ``WIKI_THEME_CSS`` espera por padrão —, qualquer
que seja a variante escolhida.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

PICO_VERSION = "2.1.1"
CDN_URL = "https://cdn.jsdelivr.net/npm/@picocss/pico@{version}/css/{filename}"
OUTPUT_NAME = "pico.classless.min.css"
DEFAULT_DEST = Path(__file__).resolve().parent.parent / "src/wiki/static/vendor"
TIMEOUT_SECONDS = 30


def remote_filename(variant: str | None) -> str:
    """Nome do arquivo no pacote npm do Pico para a variante de cor pedida."""
    return f"pico.classless.{variant}.min.css" if variant else OUTPUT_NAME


def download(url: str) -> bytes:
    """Baixa ``url`` e devolve o conteúdo, validando que a resposta não é vazia.

    Raises:
        SystemExit: Se a requisição falhar ou o corpo vier vazio.
    """
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            body: bytes = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise SystemExit(f"falha ao baixar {url}: {error}") from error
    if not body:
        raise SystemExit(f"resposta vazia de {url}")
    return body


def main() -> None:
    """Ponto de entrada da linha de comando."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="pasta de destino")
    parser.add_argument("--version", default=PICO_VERSION, help="versão do Pico (padrão: %(default)s)")
    parser.add_argument("--variant", default=None, help="variante de cor, ex.: jade")
    args = parser.parse_args()

    url = CDN_URL.format(version=args.version, filename=remote_filename(args.variant))
    body = download(url)

    args.dest.mkdir(parents=True, exist_ok=True)
    target = args.dest / OUTPUT_NAME
    target.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    print(f"{url}\n  -> {target} ({len(body)} bytes, sha256={digest})", file=sys.stderr)


if __name__ == "__main__":
    main()
