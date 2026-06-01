# Servidor Web Wiki - GCC125

Servidor web desenvolvido para o trabalho de instalação e configuração da disciplina GCC125@Hermes.

## Sobre o Projeto

Este projeto consiste em um sistema de Wiki leve e dinâmico, baseado em arquivos Markdown. A aplicação lê arquivos Markdown locais, renderiza-os como páginas HTML e oferece a funcionalidade de exportação nativa de relatórios ou páginas da Wiki para o formato PDF. O projeto foi construído priorizando a separação de responsabilidades (Serviços, Repositórios, Rotas), alta cobertura de testes e automação de entrega contínua.

### Tecnologias Utilizadas

* **Backend:** Python 3.11+ e Flask
* **Gerenciamento de Pacotes:** Poetry
* **Processamento de Documentos:** Markdown e WeasyPrint (renderização de PDFs)
* **Testes:** Pytest com pytest-cov
* **Infraestrutura:** Docker e GitHub Container Registry (GHCR)
* **CI/CD:** GitHub Actions

---

## Pré-requisitos

Para rodar e modificar este projeto localmente, você precisará ter instalado em sua máquina:

* Python 3.11 ou superior
* Pipx (recomendado para instalar o Poetry isoladamente)
* Poetry (gerenciador de dependências e ambientes virtuais)
* Docker (para testes de container e build)
* Bibliotecas de sistema necessárias para o WeasyPrint (Pango, cairo, GDK-PixBuf). *Nota: O Docker resolve estas dependências automaticamente no ambiente de produção.*

---

## Ambiente de Desenvolvimento (Setup Local)

O ambiente de desenvolvimento é gerenciado inteiramente pelo Poetry, o que garante a consistência das dependências.

**1. Clonar o repositório:**

```bash
git clone https://github.com/ArthurValadaresUFLA/GCC125-TF-Wiki.git
cd gcc-tf-wiki

```

**2. Instalar dependências da aplicação e de desenvolvimento:**

```bash
poetry install

```

**3. Executar o servidor de desenvolvimento:**

```bash
# Definindo as variáveis de ambiente necessárias
export FLASK_ENV=development
export FLASK_APP=src/wiki/app.py

# Iniciando a aplicação
poetry run flask run --host=0.0.0.0 --port=5000

```

Acesse a aplicação em `http://localhost:5000`.

---

## Estrutura do Projeto

A arquitetura do projeto segue um padrão modularizado, garantindo fácil manutenção e testes limpos.

```text
├── src/
│   └── wiki/
│       ├── models/        # Entidades e modelos de dados (ex: WikiPage)
│       ├── repositories/  # Acesso aos dados no disco (ex: FileWikiRepository)
│       ├── routes/        # Blueprints e endpoints da API Flask
│       ├── services/      # Regras de negócio (Markdown, PDF, WeasyPrint)
│       ├── static/        # Arquivos estáticos (CSS)
│       └── templates/     # Templates HTML (Jinja2)
├── tests/                 # Suíte de testes unitários isolados
├── wiki_data/             # Diretório padrão onde os arquivos .md da Wiki são armazenados
├── pyproject.toml         # Configuração do Poetry e metadados do projeto
└── Dockerfile             # Receita para a construção da imagem da aplicação

```

---

## Testes e Cobertura

O projeto possui uma suíte de testes unitários focados na validação das lógicas de serviço, mapeamento de arquivos locais e processamento do WeasyPrint.

Para executar a suíte de testes e gerar o relatório de cobertura de código no terminal, utilize:

```bash
poetry run pytest --cov=src/wiki tests/ --cov-report=term-missing

```

---

## Executando com Docker

Você pode rodar a aplicação através de containers Docker, isolando a infraestrutura e evitando a necessidade de instalar dependências complexas (como as bibliotecas C do WeasyPrint) na sua máquina local.

### 1. Utilizando a Imagem Oficial (Docker Pull)

O repositório está configurado com um pipeline de CI/CD que compila e publica a imagem Docker no GitHub Container Registry (GHCR) toda a vez que alterações são mescladas na branch `master`.

Para baixar e executar a imagem mais recente do servidor:

```bash
# 1. Baixe a imagem gerada pelo GitHub Actions
docker pull ghcr.io/seu-usuario/seu-repositorio:latest

# 2. Execute o container mapeando a pasta local da wiki
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/wiki_data:/app/wiki_data \
  --name wiki-server \
  ghcr.io/seu-usuario/seu-repositorio:latest

```

### 2. Compilando Localmente (Docker Build)

Caso tenha modificado o código e precise gerar a imagem do zero na sua própria máquina, execute:

```bash
# Construir a imagem localmente nomeando-a como "wiki-local"
docker build -t wiki-local .

# Executar a imagem recém-construída
docker run -p 5000:5000 -v $(pwd)/wiki_data:/app/wiki_data wiki-local

```

### Variáveis de Ambiente Suportadas

Durante a execução da aplicação ou do container, você pode customizar os comportamentos injetando as seguintes variáveis de ambiente:

* `FLASK_ENV`: Define o modo da aplicação (`development`, `testing` ou `production`).
* `APP_HOST`: IP onde o servidor ouvirá as conexões (Padrão: `0.0.0.0`).
* `APP_PORT`: Porta de execução do Flask (Padrão: `5000`).
* `WIKI_DIR`: Caminho absoluto do diretório contendo os arquivos Markdown (Padrão: `pasta_raiz/wiki_data`).
* `PDF_TEMP_DIR`: Diretório temporário para conversão dos PDFs (Padrão: `/tmp/wiki-pdf`).