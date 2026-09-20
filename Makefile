.DEFAULT_GOAL := help
CONTENT ?= examples/content

.PHONY: help install assets pygments run test typecheck \
        docs docs-serve docker-build docker-run

help:  ## Lista os comandos
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-13s %s\n", $$1, $$2}'

install:  ## Instala dependências (dev e docs), baixa o tema e instala os hooks
	uv sync
	$(MAKE) assets
	$(MAKE) hooks

assets:  ## Baixa o tema Pico CSS para src/wiki/static/vendor (VARIANT=jade para trocar a cor)
	uv run --no-project python scripts/fetch_assets.py $(if $(VARIANT),--variant $(VARIANT))

pygments:  ## Regenera o CSS de realce de código (LIGHT=... DARK=...)
	uv run python scripts/generate_pygments_css.py $(if $(LIGHT),--light $(LIGHT)) $(if $(DARK),--dark $(DARK))

run:  ## Servidor de desenvolvimento em http://127.0.0.1:5000 (CONTENT=pasta)
	WIKI_DIR=$(CONTENT) uv run flask --app "wiki:create_app" run --debug

test:  ## Testes com cobertura
	uv run pytest

typecheck:  ## Verificação de tipos (mypy), sem passar pelo pre-commit
	uv run mypy

docs:  ## Gera a documentação em site/
	uv run mkdocs build --strict

docs-serve:  ## Documentação com recarga automática em http://127.0.0.1:8000
	uv run mkdocs serve

docker-build:  ## Constrói a imagem
	docker build -t wiki .

docker-run:  ## Executa a imagem publicando $(CONTENT) em http://localhost:5000
	docker run --rm -p 5000:5000 -v "$(CURDIR)/$(CONTENT):/app/data:ro" wiki
