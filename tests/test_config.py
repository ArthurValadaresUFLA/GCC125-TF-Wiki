import os
from unittest.mock import patch
import pytest
from wiki.config import env_bool, get_config, DevelopmentConfig, ProductionConfig, TestingConfig

def test_env_bool_parsing():
    # Testando variações de caminhos verdadeiros
    with patch.dict(os.environ, {"FLASK_TEST_VAR": " True "}):
        assert env_bool("FLASK_TEST_VAR") is True
    with patch.dict(os.environ, {"FLASK_TEST_VAR": "1"}):
        assert env_bool("FLASK_TEST_VAR") is True
    with patch.dict(os.environ, {"FLASK_TEST_VAR": "yes"}):
        assert env_bool("FLASK_TEST_VAR") is True
    with patch.dict(os.environ, {"FLASK_TEST_VAR": "on"}):
        assert env_bool("FLASK_TEST_VAR") is True

    # Testando falsos e nulos
    with patch.dict(os.environ, {"FLASK_TEST_VAR": "false"}):
        assert env_bool("FLASK_TEST_VAR") is False
    assert env_bool("VARIAVEL_INEXISTENTE", default=True) is True

def test_get_config_environment_selection():
    with patch.dict(os.environ, {"FLASK_ENV": "development"}):
        assert get_config() == DevelopmentConfig
    with patch.dict(os.environ, {"FLASK_ENV": "testing"}):
        assert get_config() == TestingConfig
    with patch.dict(os.environ, {"FLASK_ENV": "production"}):
        assert get_config() == ProductionConfig
    with patch.dict(os.environ, {"FLASK_ENV": "qualquer_outra_coisa"}):
        assert get_config() == ProductionConfig