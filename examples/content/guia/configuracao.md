# Configuração

Toda a configuração é feita por variáveis de ambiente.

| Variável          | Padrão                          | Descrição                         |
|-------------------|---------------------------------|-----------------------------------|
| `WIKI_DIR`        | `data`                          | Pasta com os arquivos publicados  |
| `WIKI_TITLE`      | `Wiki`                          | Título do site                    |
| `WIKI_ALLOW_HTML` | `false`                         | Preserva HTML cru no Markdown     |
| `WIKI_THEME_CSS`  | `vendor/pico.classless.min.css` | Tema (caminho estático ou URL)    |

## Segurança

Arquivos e pastas que começam com ponto (`.git`, `.env`) **nunca** são publicados.

```json
{ "allow_html": false, "cache_size": 128 }
```

Próximo passo: [instalação](instalacao.md).
