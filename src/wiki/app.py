from flask import Flask

from wiki.config import get_config
from wiki.container import ServicesContainer
from wiki.repositories.wiki_repository import FileWikiRepository
from wiki.routes.wiki_routes import wiki_bp
from wiki.services.markdown_service import MarkdownService
from wiki.services.pdf_document_service import PdfDocumentService
from wiki.services.pdf_renderer import WeasyPrintRenderer
from wiki.services.pdf_service import PdfService
from wiki.services.wiki_service import WikiService


def create_app(config_object=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())

    register_extensions(app)
    register_context_processors(app)
    register_blueprints(app)

    return app


def register_extensions(app: Flask) -> None:
    markdown_service = MarkdownService()

    wiki_repository = FileWikiRepository(app.config["WIKI_DIR"])
    wiki_service = WikiService(repository=wiki_repository)

    pdf_document_service = PdfDocumentService(static_dir=app.config["STATIC_DIR"])

    pdf_renderer = WeasyPrintRenderer()

    pdf_service = PdfService(
        markdown_service=markdown_service,
        document_service=pdf_document_service,
        renderer=pdf_renderer,
        temp_dir=app.config["PDF_TEMP_DIR"],
    )

    # Armazenando todos os serviços em um único contêiner tipado
    app.extensions["services"] = ServicesContainer(
        markdown_service=markdown_service,
        wiki_service=wiki_service,
        pdf_service=pdf_service,
    )


def register_context_processors(app: Flask) -> None:
    @app.context_processor
    def inject_global_data():
        services: ServicesContainer = app.extensions["services"]
        return {
            "pages": services.wiki_service.list_pages(),
        }


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(wiki_bp)