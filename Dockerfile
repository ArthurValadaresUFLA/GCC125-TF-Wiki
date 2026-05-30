FROM python:3.11-slim

# Instalar wkhtmltopdf (dependência do sistema operacional)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar os arquivos de build
COPY README.md ./
COPY src/ ./src/
COPY wsgi.py ./
COPY pyproject.toml ./

# Instalar dependências da aplicação
RUN pip install --no-cache-dir .

# Configurar variáveis de ambiente padrão para o Container
ENV FLASK_ENV=production
ENV PYTHONPATH=/app/src
ENV WIKI_DIR=/app/data
ENV PDF_TEMP_DIR=/tmp/wiki-pdf

# Criar os diretórios necessários
RUN mkdir -p /app/data /tmp/wiki-pdf

EXPOSE 5000

# Executar a aplicação usando Gunicorn para concorrência
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:app"]