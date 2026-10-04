# Instalação

## Com Docker

```bash
docker build -t wiki .
docker run -d --name wiki -p 5000:5000 \
  -e WIKI_TITLE="Minha Wiki" \
  -v /caminho/dos/markdowns:/app/data:ro \
  wiki
```

Abra <http://localhost:5000>.

## Sem Docker

```bash
uv sync
make assets
WIKI_DIR=examples/content make run
```

Volte à [página inicial](../bem-vindo.md) ou veja a [configuração](configuracao.md).
