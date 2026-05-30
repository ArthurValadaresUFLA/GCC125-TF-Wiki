from wiki.models.wiki_page import WikiPage
from wiki.interfaces import IWikiRepository

class WikiPageNotFoundError(LookupError):
    pass

class WikiService:
    # Agora depende de uma Interface e não de uma implementação direta
    def __init__(self, repository: IWikiRepository):
        self.repository = repository

    def get_page(self, name: str) -> WikiPage | None:
        return self.repository.get_by_name(name)

    def get_existing_page(self, name: str) -> WikiPage:
        page = self.get_page(name)
        if page is None:
            raise WikiPageNotFoundError(f"Página não encontrada: {name}")
        return page

    def list_pages(self) -> list[WikiPage]:
        return self.repository.list_all()

    def read_page(self, page: WikiPage) -> str:
        return self.repository.read(page)

    def read_page_by_name(self, name: str) -> str:
        page = self.get_existing_page(name)
        return self.read_page(page)