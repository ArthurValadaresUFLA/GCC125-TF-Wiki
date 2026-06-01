import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from wiki.services.markdown_service import MarkdownService
from wiki.services.pdf_document_service import PdfDocumentService
from wiki.services.pdf_renderer import WeasyPrintRenderer
from wiki.services.pdf_service import PdfService
from wiki.services.wiki_service import WikiService, WikiPageNotFoundError
from wiki.models.wiki_page import WikiPage


# --- Markdown Service ---
def test_markdown_service_rendering():
    service = MarkdownService()
    result = service.render("# Título\n[[Link Interno]]")

    assert 'id="titulo"' in result
    assert "Título" in result
    assert 'class="wikilink"' in result


# --- PDF Document Service ---
def test_pdf_document_service(mock_static_dir):
    service = PdfDocumentService(static_dir=mock_static_dir)
    html = service.build_html(title="Segurança <Script>", body="<div>Conteúdo</div>")

    assert "<title>Segurança &lt;Script&gt;</title>" in html
    assert 'href="file://' in html
    assert "markdown-body" in html


def test_pdf_document_service_missing_stylesheets(tmp_path):
    service = PdfDocumentService(static_dir=tmp_path)
    html = service.build_html("Vazio", "Corpo")
    assert '<link rel="stylesheet"' not in html


# --- WeasyPrint Renderer ---
@patch("wiki.services.pdf_renderer.HTML")
def test_weasyprint_renderer_calls_library(mock_html, tmp_path):
    renderer = WeasyPrintRenderer()
    html_file = tmp_path / "input.html"
    pdf_file = tmp_path / "output.pdf"
    html_file.write_text("<html></html>", encoding="utf-8")

    renderer.render(html_file, pdf_file)
    mock_html.assert_called_once_with(filename=str(html_file))
    mock_html.return_value.write_to.assert_called_once_with(str(pdf_file))


# --- PDF Service ---
def test_pdf_service_safe_file_name():
    service = PdfService(MagicMock(), MagicMock(), MagicMock(), Path("/tmp"))

    assert service._safe_file_name("  Nome Com Espaço !! ") == "nome-com-espaço"
    assert service._safe_file_name("Página/Testeó") == "página-testeó"
    assert service._safe_file_name("!!!???") == "document"


def test_pdf_service_generate_flow(tmp_path):
    mock_md = MagicMock()
    mock_md.render.return_value = "<p>HTML</p>"

    mock_doc = MagicMock()
    mock_doc.build_html.return_value = "<html></html>"

    mock_renderer = MagicMock()
    mock_renderer.render.side_effect = lambda html_file, pdf_file: pdf_file

    service = PdfService(
        markdown_service=mock_md,
        document_service=mock_doc,
        renderer=mock_renderer,
        temp_dir=tmp_path / "temps"
    )

    pdf_output = service.generate("Título Documento", "# Markdown")
    assert pdf_output.suffix == ".pdf"
    assert pdf_output.name == "título-documento.pdf"
    assert pdf_output.parent.exists()


# --- Wiki Service ---
def test_wiki_service_business_logic():
    mock_repo = MagicMock()
    service = WikiService(repository=mock_repo)
    fake_page = WikiPage(name="home", path=Path("home.md"))

    mock_repo.get_by_name.side_effect = lambda name: fake_page if name == "home" else None
    mock_repo.read.return_value = "Texto Lido"

    assert service.get_page("home") == fake_page
    assert service.get_existing_page("home") == fake_page
    assert service.read_page_by_name("home") == "Texto Lido"

    with pytest.raises(WikiPageNotFoundError):
        service.get_existing_page("inexistente")

    with pytest.raises(WikiPageNotFoundError):
        service.read_page_by_name("inexistente")