# Wiki

Serviço web pequeno e de uma página só: aponte-o para uma **pasta** e ele publica

- cada arquivo `.md` como uma página HTML (com realce de código, tabelas e índice);
- todos os outros arquivos (planilhas, PDFs, imagens…) como **downloads**.

## As rotas

| Rota            | O que faz                                                                    |
|-----------------|------------------------------------------------------------------------------|
| `/`             | Índice: páginas (agrupadas por pasta) e arquivos para baixar                 |
| `/<nome>`       | Exibe `<nome>.md`; se não houver página, baixa o arquivo `<nome>`            |

Para baixar o Markdown original use o nome completo, com extensão: `/guia/instalacao.md`.

## Por que o PDF sai do navegador?

O layout de impressão é definido em CSS (`@media print`) e o próprio navegador gera o PDF.
Isso elimina o WeasyPrint (bibliotecas nativas, dezenas de MB, processamento lento no
servidor) e mantém a imagem Docker pequena. Veja [Arquitetura](architecture.md#impressao-e-pdf).

## Começando

```bash
docker build -t wiki .
docker run --rm -p 5000:5000 -v "$PWD/examples/content:/app/data:ro" wiki
```

Próximos passos: [configuração](configuration.md), [implantação](deployment.md) e
[desenvolvimento](development.md).
