# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Entidad principal del dominio: Documento."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Documento:
    """Representa un documento oficial procesado por SIVAD."""

    tipo: str
    nombre_archivo: str
    datos_extraidos: dict[str, Any] = field(default_factory=dict)

    def es_valido(self) -> bool:
        """Verifica que el documento tenga datos extraídos."""
        return bool(self.datos_extraidos)
