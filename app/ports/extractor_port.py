# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Puerto (interfaz) para la extracción de datos de documentos."""
from abc import ABC, abstractmethod


class ExtractorPort(ABC):
    """Contrato que deben cumplir todos los adaptadores de extracción."""

    @abstractmethod
    def extraer(self, imagen_bytes: bytes, eleccion: str) -> dict:
        """Extrae los resultados de votacion de la imagen de un acta.

        Args:
            imagen_bytes: contenido de la imagen (JPG o PNG).
            eleccion: clave de la plantilla a usar, p. ej. "2024_presidencia".
        """
        ...
