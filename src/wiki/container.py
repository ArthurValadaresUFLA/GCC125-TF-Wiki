from dataclasses import dataclass
from wiki.services.markdown_service import MarkdownService
from wiki.services.pdf_service import PdfService
from wiki.services.wiki_service import WikiService

@dataclass
class ServicesContainer:
    """Contêiner de serviços para facilitar o autocompletar e garantir tipagem nas Rotas."""
    markdown_service: MarkdownService
    wiki_service: WikiService
    pdf_service: PdfService