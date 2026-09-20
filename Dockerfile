# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12
# Mesma minor exigida em [build-system] do pyproject.toml (uv_build>=0.12,<0.13)
ARG UV_VERSION=0.12

############################################################
# Stage 0 — uv: só fornece o binário do uv (não vai para a imagem final)
############################################################
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv


############################################################
# Stage 1 — assets: baixa o tema (Pico CSS) para servi-lo localmente
############################################################
FROM python:${PYTHON_VERSION}-slim AS assets

# Variante de cor do Pico (ex.: jade, azure, amber). Vazio = tema padrão.
ARG PICO_VARIANT=""

WORKDIR /assets
COPY scripts/fetch_assets.py ./
RUN python fetch_assets.py --dest /assets/vendor ${PICO_VARIANT:+--variant "$PICO_VARIANT"}


############################################################
# Stage 2 — builder: instala as dependências (exatamente as do uv.lock)
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

# Só os manifestos entram (via bind mount, sem criar layer): este passo só é refeito quando
# as dependências mudam. Flags:
#   --locked              falha se o uv.lock estiver desatualizado em relação ao pyproject;
#   --no-default-groups   ignora os grupos dev/docs (definidos em [tool.uv] default-groups);
#   --no-install-project  não instala o projeto: o código roda direto de /app/src.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-default-groups --no-install-project


############################################################
# Stage 3 — runtime: só o necessário para executar
############################################################
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH=/app/src \
    WIKI_DIR=/app/data \
    WEB_CONCURRENCY=2

WORKDIR /app

# Usuário sem privilégios + pasta de conteúdo (normalmente um volume montado)
RUN groupadd --system --gid 10001 wiki \
    && useradd --system --uid 10001 --gid wiki --no-create-home \
        --shell /usr/sbin/nologin wiki \
    && mkdir -p "$WIKI_DIR"

# Camadas ordenadas da que menos muda para a que mais muda
COPY --from=builder /app/.venv ./.venv
COPY --from=assets /assets/vendor ./src/wiki/static/vendor
COPY src ./src

USER wiki

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=2)"]

# Nº de workers via WEB_CONCURRENCY; threads atendem I/O sem multiplicar memória
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--threads", "4", \
     "--worker-tmp-dir", "/dev/shm", \
     "--access-logfile", "-", \
     "wiki:create_app()"]
