"""Exceções específicas da aplicação."""

from __future__ import annotations


class WikiError(Exception):
    """Classe base de todas as exceções levantadas pela aplicação."""


class ConfigurationError(WikiError):
    """Configuração inválida ou incompleta (variável de ambiente, diretório etc.)."""


class ContentNotFoundError(WikiError, LookupError):
    """O conteúdo solicitado não existe ou não pode ser exposto (ex.: arquivo oculto)."""
