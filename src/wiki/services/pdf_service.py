import re
import tempfile
from pathlib import Path

from wiki.services.markdown_service import MarkdownService
from wiki.services.pdf_document_service import PdfDocumentService
from wiki.interfaces import IPdfRenderer


class PdfService:
    def __init__(
            self,
            markdown_service: MarkdownService,
            document_service: PdfDocumentService,
            renderer: IPdfRenderer,  # Dependência da Interface (abstração)
            temp_dir: Path,
    ):
        self.markdown_service = markdown_service
        self.document_service = document_service
        self.renderer = renderer
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, title: str, markdown_content: str) -> Path:
        html_content = self.markdown_service.render(markdown_content)
        document = self.document_service.build_html(title=title, body=html_content)

        file_name = self._safe_file_name(title)
        output_dir = Path(
            tempfile.mkdtemp(prefix="document-", dir=self.temp_dir)
        )

        html_file = output_dir / f"{file_name}.html"
        pdf_file = output_dir / f"{file_name}.pdf"

        html_file.write_text(document, encoding="utf-8")

        return self.renderer.render(html_file=html_file, pdf_file=pdf_file)

    def _safe_file_name(self, value: str) -> str:
        normalized = value.strip().lower()
        normalized = re.sub(r"[^\w.-]+", "-", normalized, flags=re.UNICODE)
        return normalized.strip("-.") or "document"