# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Puerto (interfaz) para la extracción de datos de documentos."""
from abc import ABC, abstractmethod


class ExtractorPort(ABC):
    """Contrato que deben cumplir todos los adaptadores de extracción."""

    @abstractmethod
    def extraer(self, imagen_bytes: bytes, tipo_documento: str) -> dict:
        """Extrae datos estructurados de la imagen de un documento."""
        ...
