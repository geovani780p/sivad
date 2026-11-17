# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Puerto (interfaz) para el almacenamiento de actas procesadas."""
from abc import ABC, abstractmethod


class RepositorioActasPort(ABC):
    """Contrato que deben cumplir todos los adaptadores de almacenamiento."""

    @abstractmethod
    def guardar(self, acta: dict, imagen_bytes: bytes, nombre_archivo: str) -> str:
        """Guarda el resultado y la imagen de un acta; devuelve su identificador."""
        ...

    @abstractmethod
    def obtener(self, acta_id: str) -> dict | None:
        """Devuelve un acta guardada, o None si no existe."""
        ...

    @abstractmethod
    def obtener_imagen(self, acta_id: str) -> bytes | None:
        """Devuelve la imagen original de un acta, o None si no existe."""
        ...

    @abstractmethod
    def listar(self, limite: int = 50) -> list[dict]:
        """Devuelve las actas mas recientes, sin incluir las imagenes."""
        ...
