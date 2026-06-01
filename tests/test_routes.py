from pathlib import Path
import pytest
from unittest.mock import MagicMock


def test_route_index(client, test_config):
    # Criar um arquivo markdown na pasta de testes para o repositório ler
    (test_config.WIKI_DIR / "tutorial.md").write_text("Conteúdo do Tutorial", encoding="utf-8")

    response = client.get("/")
    assert response.status_code == 200

    # O context processor injeta a listagem implicitamente no template
    # Validamos isso avaliando a chave retornada pelas variáveis globais de contexto do Flask
    from flask import template_rendered
    def inspect_context(sender, template, context, **extra):
        assert "pages" in context
        assert context["pages"][0].name == "tutorial"

    with template_rendered.connected_to(inspect_context, client.application):
        client.get("/")


def test_route_page_found_and_not_found(client, test_config):
    # Caso 1: 404 Página Inexistente
    response_404 = client.get("/pagina-que-nao-existe")
    assert response_404.status_code == 404

    # Caso 2: 200 Sucesso
    (test_config.WIKI_DIR / "contato.md").write_text("# Contato Fone", encoding="utf-8")
    response_200 = client.get("/contato")
    assert response_200.status_code == 200


def test_route_pdf_generation_delivery(client, test_config, app):
    # Configurando arquivo válido
    (test_config.WIKI_DIR / "relatorio.md").write_text("# Relatório Geral", encoding="utf-8")

    # Como não queremos disparar o motor do Weasyprint real no teste HTTP (evitar lentidão)
    # vamos interceptar o método render da instância que está rodando no app do Flask
    services = app.extensions["services"]

    def fake_render(html_file, pdf_file):
        pdf_file.write_text("FAKE PDF BINARY DATA", encoding="utf-8")
        return pdf_file

    services.pdf_service.renderer.render = fake_render

    # Dispara a requisição de download
    response = client.get("/relatorio/pdf")

    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == "attachment; filename=relatorio.pdf"
    assert response.data == b"FAKE PDF BINARY DATA"

    # Testa 404 para o PDF de página não existente
    response_404 = client.get("/pdf-inexistente/pdf")
    assert response_404.status_code == 404