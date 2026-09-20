# Configuração

Toda a configuração é feita por **variáveis de ambiente**, definidas ao criar o container.

| Variável          | Padrão                          | Descrição |
|-------------------|---------------------------------|-----------|
| `WIKI_DIR`        | `data` (`/app/data` na imagem)  | Pasta com os arquivos publicados. Monte-a como volume somente leitura. |
| `WIKI_TITLE`      | `Wiki`                          | Título do cabeçalho e da aba do navegador. |
| `WIKI_LANG`       | `pt-BR`                         | Valor do atributo `lang` do HTML. |
| `WIKI_ALLOW_HTML` | `false`                         | `true` preserva HTML cru dentro do Markdown. |
| `WIKI_THEME_CSS`  | `vendor/pico.classless.min.css` | Tema: caminho relativo a `static/` ou URL `http(s)://`. |
| `WIKI_CACHE_SIZE` | `128`                           | Páginas renderizadas mantidas em memória. |
| `WEB_CONCURRENCY` | `2` (na imagem)                 | Número de *workers* do Gunicorn. |

Valores booleanos aceitam `1/true/yes/on/sim` e `0/false/no/off/nao`.

## Regras do conteúdo

- **Páginas**: arquivos terminados em `.md` (minúsculo). O título é o primeiro `# Título`;
  sem ele, usa-se o nome do arquivo.
- **Ordem**: por pasta e depois por nome de arquivo (use `01-intro.md`, `02-uso.md` para controlar).
- **Links entre páginas**: `[texto](outra.md)` e `[texto](../guia/x.md#secao)` viram links para
  a página; links absolutos (`https://…`) não são alterados.
- **Imagens**: caminhos relativos (`![x](img/foto.png)`) funcionam e são carregadas sob demanda.
- **Downloads**: todo arquivo que não termina em `.md` aparece na seção "Arquivos para download".
- **Ocultos**: nomes iniciados por `.` (`.git`, `.env`…) nunca são publicados.
- **Links simbólicos**: para arquivos, só se o destino estiver dentro da pasta; pastas
  simbólicas não são listadas.

## Tema e cores

O visual usa o [Pico CSS](https://picocss.com) (*classless*), com modo escuro automático.

=== "Trocar a cor no build"

    ```bash
    docker build --build-arg PICO_VARIANT=jade -t wiki .
    ```

=== "Usar outro tema por URL"

    ```bash
    docker run -e WIKI_THEME_CSS=https://cdn.jsdelivr.net/npm/water.css@2/out/water.css …
    ```

    A política de segurança libera automaticamente apenas a origem informada.

Para ajustes finos, edite `src/wiki/static/css/wiki.css` (sobrescreva variáveis `--pico-*`).
O realce de código é regenerado com `make pygments LIGHT=friendly DARK=monokai`.

!!! warning "WIKI_ALLOW_HTML"
    Com `true`, o HTML escrito nos Markdown é publicado como está. Mesmo assim a CSP bloqueia
    `<script>` e atributos `style` inline, mas só habilite se os autores dos arquivos forem confiáveis.
