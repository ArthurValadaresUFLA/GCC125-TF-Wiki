from flask import Blueprint, abort, current_app, render_template, send_file
from wiki.container import ServicesContainer

wiki_bp = Blueprint("wiki", __name__)

def get_services() -> ServicesContainer:
    # Helper para recuperar serviços mantendo a tipagem limpa
    return current_app.extensions["services"]

@wiki_bp.route("/")
def index():
    wiki_service = get_services().wiki_service
    return render_template("index.html", pages=wiki_service.list_pages())

@wiki_bp.route("/<page_name>")
def page(page_name: str):
    services = get_services()
    wiki_page = services.wiki_service.get_page(page_name)

    if wiki_page is None:
        abort(404)

    markdown_content = services.wiki_service.read_page(wiki_page)
    html = services.markdown_service.render(markdown_content)

    return render_template("page.html", page=wiki_page, content=html)

@wiki_bp.route("/<page_name>/pdf")
def page_pdf(page_name: str):
    services = get_services()
    wiki_page = services.wiki_service.get_page(page_name)

    if wiki_page is None:
        abort(404)

    markdown_content = services.wiki_service.read_page(wiki_page)
    pdf_path = services.pdf_service.generate(
        title=wiki_page.title,
        markdown_content=markdown_content,
    )

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f"{wiki_page.name}.pdf",
    )