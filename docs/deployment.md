# Implantação

## Docker

```bash
docker build -t wiki .
docker run -d --name wiki -p 5000:5000 \
  -e WIKI_TITLE="Base de conhecimento" \
  -v /srv/base:/app/data:ro \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  wiki
```

A imagem tem três estágios: **assets** (baixa o tema), **builder** (instala as dependências a
partir do `uv.lock`) e **runtime** (só o ambiente virtual e o código, usuário sem privilégios).
Como a aplicação não escreve em disco, `--read-only` é seguro.

!!! note "Build precisa de internet"
    O estágio *assets* baixa o Pico CSS do jsDelivr. Em execução, a wiki não acessa a internet.

## Docker Compose

O `docker-compose.yml` do repositório já traz volume somente leitura e o endurecimento acima:

```bash
docker compose up --build
```

## Atrás de um proxy reverso

Publique a porta 5000 em uma interface interna e deixe o proxy (Nginx, Traefik, Caddy) cuidar
do TLS. Para autenticação, use a do proxy — a wiki não tem login.

## Saúde e logs

- `HEALTHCHECK` da imagem consulta `/`.
- Logs de acesso vão para o *stdout* (`docker logs wiki`).

## Ajuste de desempenho

`WEB_CONCURRENCY` (processos) × 4 *threads* atendem as requisições. Como o HTML é cacheado
pelo conteúdo do arquivo e respondido com `ETag`, edições no disco aparecem imediatamente e
navegadores só baixam o corpo quando algo mudou.
