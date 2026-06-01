import pytest
from pathlib import Path
from wiki.app import create_app
from wiki.config import TestingConfig


@pytest.fixture
def mock_static_dir(tmp_path):
    """Cria uma estrutura temporária de arquivos CSS para teste."""
    static_path = tmp_path / "static"
    css_path = static_path / "css"
    css_path.mkdir(parents=True)

    # Criando os arquivos CSS esperados pela aplicação
    (css_path / "app.css").write_text("body { margin: 0; }", encoding="utf-8")
    (css_path / "markdown.css").write_text(".markdown-body { color: #333; }", encoding="utf-8")
    (css_path / "pygments.css").write_text(".code { color: red; }", encoding="utf-8")

    return static_path


@pytest.fixture
def test_config(tmp_path, mock_static_dir):
    """Gera um objeto de configuração apontando para diretórios isolados."""
    config = TestingConfig()
    config.WIKI_DIR = tmp_path / "wiki_data"
    config.PDF_TEMP_DIR = tmp_path / "wiki_pdf"
    config.STATIC_DIR = mock_static_dir

    config.WIKI_DIR.mkdir(parents=True, exist_ok=True)
    config.PDF_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return config


@pytest.fixture
def app(test_config):
    """Instancia o servidor Flask de testes."""
    return create_app(test_config)


@pytest.fixture
def client(app):
    """Retorna um cliente HTTP do Flask pronto para disparar requisições."""
    return app.test_client()