# src/wiki/services/pdf_renderer.py
from pathlib import Path
from weasyprint import HTML
from wiki.interfaces import IPdfRenderer


class WeasyPrintRenderer(IPdfRenderer):
    """Renderizador moderno de PDF usando WeasyPrint (sem subprocess)."""

    def render(self, html_file: Path, pdf_file: Path) -> Path:
        # O WeasyPrint lê o arquivo HTML e gera o PDF nativamente
        HTML(filename=str(html_file)).write_to(str(pdf_file))
        return pdf_file