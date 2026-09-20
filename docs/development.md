# Desenvolvimento

## Ambiente

```bash
uv sync                 # dependências (dev e docs incluídas)
make assets             # baixa o tema Pico para src/wiki/static/vendor
make run                # http://127.0.0.1:5000, usando examples/content
make run CONTENT=~/minhas-notas
```

`uv.lock` deve ser versionado; após alterar dependências rode `uv lock`.

## Qualidade

| Comando          | O que faz                                   |
|------------------|---------------------------------------------|
| `make test`      | `pytest` com cobertura                      |
| `make lint`      | `ruff check` e `ruff format --check`        |
| `make format`    | corrige e formata                           |
| `make typecheck` | `mypy --strict`                             |
| `make docs`      | gera esta documentação em `site/`           |
| `make docs-serve`| documentação com recarga automática         |

Convenções: tipagem completa, docstrings no estilo Google (em português), sem estado global,
dependências injetadas pelo construtor.

## Testes

Os testes usam `unittest.TestCase` (executados normalmente pelo `pytest`) e pastas temporárias
reais. O serviço é testado com um repositório em memória, mostrando o benefício da injeção de
dependência. Rotas são testadas com o *test client* do Flask.

## Estendendo

- **Novo motor de Markdown**: implemente `wiki.rendering.Renderer` e passe-o a `WikiService`.
- **Plugins do markdown-it** (rodapés, listas de tarefas…): `MarkdownItRenderer(plugins=[...])`.
- **Outra origem de conteúdo** (S3, Git…): implemente `wiki.repository.ContentRepository`.
