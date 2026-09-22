.DEFAULT_GOAL := help
CONTENT ?= examples/content

CONTAINER_VIRT ?= docker

PRE_COMMIT ?= pre-commit

PICO_VERSION ?= 2.0.6
PICO_VARIANT   ?= classless
PICO_BASE_DIR  ?= src/wiki/static/vendor/picocss
PICO_VENDOR_FILE := $(PICO_BASE_DIR)/pico.min.css
PICO_DEST      := $(PICO_BASE_DIR)/v$(PICO_VERSION)
PICO_CHECKSUMS := $(PICO_DEST)/picocss-checksums.txt

PYGMENTS_LIGHT ?= default
PYGMENTS_DARK  ?= github-dark
PYGMENTS_SEL   ?= .highlight
PYGMENTS_OUT   := src/wiki/static/css/pygments.css

ACT_IMAGE      := catthehacker/ubuntu:act-latest
ACT_FULL_IMAGE := catthehacker/ubuntu:full-latest   # necessário p/ docker-publish (docker cli, gh cli, unzip)
ACT_SECRETS    := $(if $(wildcard .secrets),--secret-file .secrets,)

$(PICO_VENDOR_FILE):
	$(MAKE) assets


.PHONY: ci-list ci-lint ci-test ci-test-all ci-build-pkg ci-python ci-docker \
		help install pygments run test typecheck docs \
		docs-serve docker-build docker-run update-vendor

help:  ## Lista os comandos
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-13s %s\n", $$1, $$2}'

install: update-vendor select-vendor-variant pygments ## Instala dependências (dev e docs), baixa o tema e instala os hooks
	uv sync
	$(PRE_COMMIT) install

update-vendor:  ## Baixa e valida os arquivos do PicoCSS (checksum obrigatório)
	@mkdir -p $(PICO_DEST)
	@for f in pico.min.css pico.classless.min.css pico.fluid.classless.min.css; do \
		echo "Baixando $$f..."; \
		curl -fsSL "https://cdn.jsdelivr.net/npm/@picocss/pico@$(PICO_VERSION)/css/$$f" -o "$(PICO_DEST)/$$f"; \
	done
	@echo "Baixando LICENSE ..."; \
	curl -fsSL https://raw.githubusercontent.com/picocss/pico/main/LICENSE.md -o $(PICO_DEST)/LICENSE.md;

select-vendor-variant:  ## Copia a variante escolhida (PICO_VARIANT) para pico.min.css final
	@SRC="$(PICO_DEST)/pico$(if $(PICO_VARIANT),.$(PICO_VARIANT),).min.css"; \
	if [ ! -f "$$SRC" ]; then echo "Variante inválida: $(PICO_VARIANT)" >&2; exit 1; fi; \
	echo "Variante selecionada: $(PICO_VARIANT)"; \
	cp "$$SRC" "$(PICO_BASE_DIR)/pico.min.css";

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
	@echo "Escrito: $(PYGMENTS_OUT)"

assets: update-vendor select-vendor-variant pygments ## Baixa + seleciona a variante do PicoCSS e gera o pygments

run: assets ## Servidor de desenvolvimento em http://127.0.0.1:5000 (CONTENT=pasta)
	WIKI_DIR=$(CONTENT) uv run flask --app "wiki:create_app" run --debug

docs:  ## Gera a documentação em site/
	uv run mkdocs build --strict

docs-serve:  ## Documentação com recarga automática em http://127.0.0.1:8000
	uv run mkdocs serve

docker-build: $(PICO_VENDOR_FILE)  ## Garante o PicoCSS antes de buildar a imagem
	$(CONTAINER_VIRT) build --build-arg PICO_VENDOR_FILE=$(PICO_VENDOR_FILE) -t wiki .

docker-run:  ## Executa a imagem publicando $(CONTENT) em http://localhost:5000
	$(CONTAINER_VIRT) run --rm -p 5000:5000 -v "$(CURDIR)/$(CONTENT):/app/data:ro,Z" wiki

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
