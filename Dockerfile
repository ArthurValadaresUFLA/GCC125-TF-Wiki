# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12
# Mesma minor exigida em [build-system] do pyproject.toml (uv_build>=0.12,<0.13)
ARG UV_VERSION=0.12

# Stage 0 — uv: só fornece o binário do uv (não vai para a imagem final)
############################################################
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

############################################################
# Stage 1 — builder: instala as dependências (exatamente as do uv.lock)
############################################################
FROM python:${PYTHON_VERSION}-slim AS builder

COPY --from=uv /uv /bin/uv

# COMPILE_BYTECODE: gera .pyc na instalação (a imagem final não escreve bytecode);
# LINK_MODE=copy: o cache de build fica em outro filesystem, hardlinks não funcionam;
# PYTHON_DOWNLOADS=never: usa o Python da própria imagem base, sem baixar outro.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Mesmo caminho do stage final: o venv usa caminhos absolutos e não é relocável
WORKDIR /app

# Só os manifestos são copiados: esta layer (e a instalação abaixo) só é refeita quando as
# dependências mudam. COPY em vez de `--mount=type=bind`, que falha com "Permission denied"
# no Podman/Buildah (SELinux e user namespaces) e funciona igual no Docker.
COPY pyproject.toml uv.lock ./

# Flags:
#   --locked              falha se o uv.lock estiver desatualizado em relação ao pyproject;
#   --no-default-groups   ignora os grupos dev/docs (definidos em [tool.uv] default-groups);
#   --no-install-project  não instala o projeto: o código roda direto de /app/src.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --no-install-project

############################################################
# Stage 2 — runtime: só o necessário para executar
############################################################
FROM python:${PYTHON_VERSION}-slim AS runtime

# PicoCSS é baixado durante o build (não é versionado): mantenha PICO_VERSION em sincronia
# com o Makefile. A variante "classless" vira o pico.min.css que o app espera.
ARG PICO_VERSION=2.0.6
ARG PICO_FILE=pico.classless.min.css
ARG PICO_DIR=src/wiki/static/vendor/picocss

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH=/app/src \
    WIKI_DIR=/app/data \
    WEB_CONCURRENCY=2

WORKDIR /app

# Usuário sem privilégios + pasta de conteúdo (normalmente um volume montado)
RUN groupadd --gid 10001 wiki \
    && useradd --uid 10001 --gid wiki --no-create-home \
        --shell /usr/sbin/nologin wiki \
    && mkdir -p "$WIKI_DIR"

# Camadas ordenadas da que menos muda para a que mais muda
COPY --from=builder /app/.venv ./.venv
COPY src ./src
RUN chmod -R a+rX ./src

# ADD de URL é feito pelo próprio builder (Docker/Podman), sem precisar de curl na imagem.
# Para travar a integridade, acrescente --checksum=sha256:<hash> em cada ADD.
ADD --chmod=644 https://cdn.jsdelivr.net/npm/@picocss/pico@${PICO_VERSION}/css/${PICO_FILE} \
    ./${PICO_DIR}/pico.min.css
ADD --chmod=644 https://raw.githubusercontent.com/picocss/pico/main/LICENSE.md \
    ./${PICO_DIR}/LICENSE.md

USER wiki

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=2)"]

# Nº de workers via WEB_CONCURRENCY; threads atendem I/O sem multiplicar memória
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--threads", "4", \
     "--worker-tmp-dir", "/dev/shm", \
     "--control-socket", "/tmp/gunicorn.ctl", \
     "--access-logfile", "-", \
     "wiki:create_app()"]
