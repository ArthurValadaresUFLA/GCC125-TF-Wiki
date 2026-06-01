from pathlib import Path
import pytest
from wiki.models.wiki_page import WikiPage
from wiki.repositories.wiki_repository import FileWikiRepository


def test_wiki_page_title_property():
    page1 = WikiPage(name="meu-arquivo-de-notas", path=Path("dummy"))
    assert page1.title == "Meu Arquivo De Notas"

    page2 = WikiPage(name="outra_anotacao_longa", path=Path("dummy"))
    assert page2.title == "Outra Anotacao Longa"


def test_repository_directory_auto_creation(tmp_path):
    target_dir = tmp_path / "nova_pasta_automatica"
    assert not target_dir.exists()
    FileWikiRepository(target_dir)
    assert target_dir.exists()


def test_repository_get_by_name(tmp_path):
    repo = FileWikiRepository(tmp_path)

    # Caso 1: Página não existe no disco
    assert repo.get_by_name("inexistente") is None

    # Caso 2: É um diretório com o nome, não um arquivo válido
    (tmp_path / "pasta_teste.md").mkdir()
    assert repo.get_by_name("pasta_teste") is None

    # Caso 3: Arquivo markdown real válido
    file_path = tmp_path / "sobre.md"
    file_path.write_text("## Sobre mim", encoding="utf-8")
    page = repo.get_by_name("sobre")
    assert page is not None
    assert page.name == "sobre"
    assert page.path == file_path


def test_repository_list_all_filtering_and_sorting(tmp_path):
    repo = FileWikiRepository(tmp_path)

    # Criando arquivos fora de ordem alfabética
    (tmp_path / "zebra.md").write_text("Z", encoding="utf-8")
    (tmp_path / "abacate.md").write_text("A", encoding="utf-8")
    (tmp_path / "index.md").write_text("Index", encoding="utf-8")  # Deve ser ignorado

    pages = repo.list_all()
    assert len(pages) == 2
    assert pages[0].name == "abacate"
    assert pages[1].name == "zebra"


def test_repository_read_file(tmp_path):
    repo = FileWikiRepository(tmp_path)
    file_path = tmp_path / "teste.md"
    file_path.write_text("Conteúdo UTF-8: Áçê", encoding="utf-8")

    page = WikiPage(name="teste", path=file_path)
    assert repo.read(page) == "Conteúdo UTF-8: Áçê"