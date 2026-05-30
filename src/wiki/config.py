import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

    # Resolvendo diretórios de forma robusta
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    WIKI_DIR = Path(os.getenv("WIKI_DIR", BASE_DIR / "wiki_data")).expanduser()
    STATIC_DIR = Path(__file__).resolve().parent / "static"
    PDF_TEMP_DIR = Path(os.getenv("PDF_TEMP_DIR", "/tmp/wiki-pdf")).expanduser()

    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "5000"))

    JSON_SORT_KEYS = False

class DevelopmentConfig(Config):
    DEBUG = True
    ENV = "development"

class ProductionConfig(Config):
    DEBUG = False
    ENV = "production"

class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    ENV = "testing"

def get_config():
    environment = os.getenv("FLASK_ENV", "production")
    configs = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    return configs.get(environment, ProductionConfig)