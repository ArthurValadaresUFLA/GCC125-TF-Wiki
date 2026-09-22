.DEFAULT_GOAL := help
CONTENT ?= examples/content

CONTAINER_VIRT ?= docker

PRE_COMMIT ?= pre-commit

PICO_VERSION ?= 2.0.6
PICO_SRC_DIR := src/wiki/static/vendor/picocss

# Alvo-arquivo: só roda update-vendor se o CSS dessa versão ainda não existir
$(PICO_SRC_DIR)/v$(PICO_VERSION)/pico.min.css:
	$(MAKE) update-vendor PICO_VERSION=$(PICO_VERSION)

PYGMENTS_LIGHT ?= default
PYGMENTS_DARK  ?= github-dark
PYGMENTS_SEL   ?= .highlight
PYGMENTS_OUT   := src/wiki/static/css/pygments.css

ACT_IMAGE      := catthehacker/ubuntu:act-latest
ACT_FULL_IMAGE := catthehacker/ubuntu:full-latest   # necessário p/ docker-publish (docker cli, gh cli, unzip)
ACT_SECRETS    := $(if $(wildcard .secrets),--secret-file .secrets,)

.PHONY: ci-list ci-lint ci-test ci-test-all ci-build-pkg ci-python ci-docker \
		help install pygments run test typecheck docs \
		docs-serve docker-build docker-run update-vendor

help:  ## Lista os comandos
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-13s %s\n", $$1, $$2}'

install: update-vendor pygments ## Instala dependências (dev e docs), baixa o tema e instala os hooks
	uv sync
	$(PRE_COMMIT) install

update-vendor:
	mkdir -p $(PICO_DEST)
	curl -sSL https://cdn.jsdelivr.net/npm/@picocss/pico@$(PICO_VERSION)/css/pico.min.css -o $(PICO_DEST)/pico.min.css
	curl -sSL https://cdn.jsdelivr.net/npm/@picocss/pico@$(PICO_VERSION)/css/pico.classless.min.css -o $(PICO_DEST)/pico.classless.min.css
	curl -sSL https://cdn.jsdelivr.net/npm/@picocss/pico@$(PICO_VERSION)/css/pico.fluid.min.css -o $(PICO_DEST)/pico.fluid.min.css
	curl -sSL https://cdn.jsdelivr.net/npm/@picocss/pico@$(PICO_VERSION)/css/pico.fluid.classless.min.css -o $(PICO_DEST)/pico.fluid.classless.min.css
	curl -sSL https://raw.githubusercontent.com/picocss/pico/main/LICENSE.md -o $(PICO_DEST)/LICENSE.md

pygments:
	@{ \
		echo "/* Gerado via 'make pygments' — claro: $(PYGMENTS_LIGHT), escuro: $(PYGMENTS_DARK). */"; \
		echo "/* Não edite à mão; gere novamente com \`make pygments\`. */"; \
		echo ""; \
		uv run pygmentize -S $(PYGMENTS_LIGHT) -f html -a $(PYGMENTS_SEL) | grep -F '$(PYGMENTS_SEL)'; \
		echo ""; \
		echo "@media screen and (prefers-color-scheme: dark) {"; \
		uv run pygmentize -S $(PYGMENTS_DARK) -f html -a $(PYGMENTS_SEL) | grep -F '$(PYGMENTS_SEL)' | sed 's/^/  /'; \
		echo "}"; \
	} > $(PYGMENTS_OUT)
	@echo "escrito: $(PYGMENTS_OUT)"

run:  ## Servidor de desenvolvimento em http://127.0.0.1:5000 (CONTENT=pasta)
	WIKI_DIR=$(CONTENT) uv run flask --app "wiki:create_app" run --debug

docs:  ## Gera a documentação em site/
	uv run mkdocs build --strict

docs-serve:  ## Documentação com recarga automática em http://127.0.0.1:8000
	uv run mkdocs serve

docker-build: $(PICO_SRC_DIR)/v$(PICO_VERSION)/pico.min.css  ## Garante o PicoCSS antes de buildar a imagem
	$(CONTAINER_VIRT) build --build-arg PICO_VERSION=$(PICO_VERSION) -t wiki .

docker-run:  ## Executa a imagem publicando $(CONTENT) em http://localhost:5000
	$(CONTAINER_VIRT) run --rm -p 5000:5000 -v "$(CURDIR)/$(CONTENT):/app/data:ro" wiki

ci: ci-lint ci-test ci-build-pkg ci-python ci-docker

ci-list:  ## Lista os workflows/jobs disponíveis
	act -l

ci-lint:  ## Job "lint" (mesmos hooks do pre-commit)
	act pull_request -W .github/workflows/python-package.yml -j lint \
		-P ubuntu-latest=$(ACT_IMAGE)

ci-test:  ## Job "test"
	act pull_request -W .github/workflows/python-package.yml -j test \
		--matrix python-version:3.12 -P ubuntu-latest=$(ACT_IMAGE)

ci-build-pkg:  ## Job "build" (sdist/wheel + smoke import)
	act pull_request -W .github/workflows/python-package.yml -j build \
		-P ubuntu-latest=$(ACT_IMAGE)

ci-python: ci-lint ci-test ci-build-pkg  ## Os 3 jobs do python-package.yml

ci-docker:  ## build-and-push-image (login/push/release pulados sob act)
	act push -W .github/workflows/docker-publish.yml -j build-and-push-image \
		-P ubuntu-latest=$(ACT_FULL_IMAGE) $(ACT_SECRETS)
