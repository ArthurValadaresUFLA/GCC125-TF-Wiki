# Wiki

Serviço web pequeno que publica uma **pasta** de arquivos como uma wiki:

- cada `.md` vira uma página HTML, com realce de código (Pygments), tabelas, índice "Nesta página"
  e modo escuro automático;
- os demais arquivos (planilhas, PDFs, imagens…) são listados como **downloads**;
- qualquer página pode ser baixada como **`.md`** ou como **PDF** (gerado pelo navegador com
  `@media print`, sem bibliotecas de PDF no servidor).

Sem banco de dados, sem login, sem estado: a pasta é a única fonte da verdade.

## Rotas

| Rota            | O que faz                                                                        |
|-----------------|----------------------------------------------------------------------------------|
| `/`             | Índice: páginas (agrupadas por pasta) e arquivos para download                   |
| `/<nome>`       | Exibe `<nome>.md`; se não houver página, baixa o arquivo `<nome>`                |

Exemplos: `/guia/instalacao` (página), `/guia/instalacao.md` (Markdown original),
`/dados/vendas.csv` (download).

## Início rápido

### Docker

```bash
uv lock                      # gera/atualiza o uv.lock (uma vez, após mudar dependências)
docker build -t wiki .
docker run --rm -p 5000:5000 -v "$PWD/examples/content:/app/data:ro" wiki
```

Abra <http://localhost:5000>. Para publicar a sua pasta, troque o caminho antes de `:/app/data`.
Trocar a cor do tema: `docker build --build-arg PICO_VARIANT=jade -t wiki .`

### Docker Compose

```bash
docker compose up --build
```

### Local (desenvolvimento)

```bash
uv sync
make assets        # baixa o tema (Pico CSS) para src/wiki/static/vendor
make run           # http://127.0.0.1:5000 com examples/content
make run CONTENT=~/minhas-notas
```

## Configuração

Tudo por variáveis de ambiente, definidas ao criar o container:

| Variável          | Padrão                          | Descrição |
|-------------------|---------------------------------|-----------|
| `WIKI_DIR`        | `data` (`/app/data` na imagem)  | Pasta publicada (monte como volume `:ro`) |
| `WIKI_TITLE`      | `Wiki`                          | Título do site |
| `WIKI_LANG`       | `pt-BR`                         | Atributo `lang` do HTML |
| `WIKI_ALLOW_HTML` | `false`                         | Preserva HTML cru dentro do Markdown |
| `WIKI_THEME_CSS`  | `vendor/pico.classless.min.css` | Tema: caminho em `static/` ou URL `https://…` |
| `WIKI_CACHE_SIZE` | `128`                           | Páginas renderizadas mantidas em memória |
| `WEB_CONCURRENCY` | `2` (imagem)                    | *Workers* do Gunicorn |

## Regras do conteúdo

- **Página** = arquivo terminado em `.md`. O título é o primeiro `# Título` (ou o nome do arquivo).
- **Ordem** por pasta e nome de arquivo — prefixe com `01-`, `02-` para controlar.
- **Links entre páginas** funcionam como no GitHub: `[x](outra.md)`, `[x](../guia/y.md#secao)`.
- **Imagens** relativas (`![x](img/a.png)`) funcionam.
- **Downloads** = qualquer arquivo que não seja `.md`.
- **Nunca publicados**: nomes iniciados por `.` (`.git`, `.env`), e links simbólicos que apontem
  para fora da pasta.
- Suporte a Markdown: CommonMark + tabelas + ~~tachado~~. Rodapés e listas de tarefas não são
  incluídos, mas podem ser adicionados com plugins do `markdown-it` (ver *Estendendo*).

## Impressão e PDF (`@media print`)

Ao **Salvar como PDF**, em qualquer página, o layout de impressão:

- remove cabeçalho, rodapé, índice e botões;
- força fundo branco e texto preto (mesmo com o navegador em modo escuro);
- evita títulos órfãos e não parte tabelas, citações e imagens no meio;
- repete o cabeçalho das tabelas em cada folha e quebra linhas de código longas;
- imprime a URL ao lado dos links externos;
- usa o título da página como nome sugerido do arquivo PDF.

As regras estão em [`src/wiki/static/css/wiki.css`](src/wiki/static/css/wiki.css), seção 3.

## Estrutura

```
src/wiki/
├── app.py          # application factory + composition root
├── config.py       # Settings (WIKI_*)
├── views.py        # 3 rotas (class-based views)
├── service.py      # WikiService (Facade)
├── repository.py   # ContentRepository / FileSystemRepository + segurança de caminhos
├── rendering.py    # Renderer / MarkdownItRenderer / CachedRenderer
├── cache.py        # LRUCache thread-safe
├── security.py     # CSP e cabeçalhos
├── models.py       # objetos de valor imutáveis
├── exceptions.py
├── static/         # wiki.css (inclui @media print), pygments.css, wiki.js
└── templates/      # base, index, page, error
```

Padrões aplicados: *Application Factory*, *Repository*, *Strategy* (`Renderer`), *Decorator*
(`CachedRenderer`), *Facade* (`WikiService`), injeção de dependência e objetos de valor. Detalhes,
diagramas e o fluxo de uma requisição em [`docs/architecture.md`](docs/architecture.md).

## Segurança

- Bloqueio de *path traversal*, arquivos ocultos e *symlinks* que escapam da pasta.
- Downloads sempre como anexo (`Content-Disposition: attachment`) e com `nosniff`.
- HTML dentro do Markdown é escapado por padrão; a CSP proíbe scripts e estilos inline
  (mesmo com `WIKI_ALLOW_HTML=true`).
- Imagem roda como usuário sem privilégios; com Compose, também com sistema de arquivos
  somente leitura e sem *capabilities*.
- **Não há autenticação**: se o conteúdo é privado, proteja a wiki no proxy reverso.

## Desenvolvimento

```bash
make test        # pytest + cobertura
make lint        # ruff
make typecheck   # mypy --strict
make docs        # documentação (MkDocs Material + mkdocstrings) em site/
make docs-serve  # http://127.0.0.1:8000
make help        # lista tudo
```

### Estendendo

- **Outro motor de Markdown**: implemente `wiki.rendering.Renderer`.
- **Plugins do markdown-it** (rodapés, task lists…): `MarkdownItRenderer(plugins=[...])`.
- **Outra origem de conteúdo** (S3, Git…): implemente `wiki.repository.ContentRepository`.

## Limitações conhecidas

- Arquivos `.MD` (maiúsculo) são tratados como downloads, não como páginas.
- Pastas simbólicas não são listadas no índice.
