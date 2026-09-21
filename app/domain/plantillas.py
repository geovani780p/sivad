# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Plantillas de Actas de Escrutinio y Computo por proceso electoral.

Cada plantilla describe la estructura fija del acta de una eleccion:
    filas       - etiquetas de las filas de la tabla de resultados, en orden
    zona_tabla  - region de la imagen donde se ubica la tabla, en proporciones
                (0.0 a 1.0) del ancho y alto de la pagina completa

Las coaliciones de diputaciones se registran por distrito, por lo que las
plantillas de diputaciones pueden requerir variantes por distrito.
"""

PLANTILLAS_ACTA: dict[str, dict] = {
    "2024_presidencia": {
        "descripcion": "Eleccion presidencial 2024",
        "filas": [
            "PAN", "PRI", "PRD", "PVEM", "PT", "MC", "MORENA",
            "PAN-PRI-PRD", "PAN-PRI", "PAN-PRD", "PRI-PRD",
            "PVEM-PT-MORENA", "PVEM-PT", "PVEM-MORENA", "PT-MORENA",
            "CANDIDATOS_NO_REGISTRADOS", "VOTOS_NULOS", "TOTAL",
        ],
        "zona_tabla": {"x1": 0.32, "x2": 0.64, "y1": 0.11, "y2": 0.75},
    },
    "2021_diputaciones": {
        "descripcion": "Diputaciones federales 2021 (coaliciones varian por distrito)",
        "filas": [
            "PAN", "PRI", "PRD", "PVEM", "PT", "MC", "MORENA", "PES", "RSP", "FXM",
            "PVEM-PT-MORENA", "PVEM-PT", "PVEM-MORENA", "PT-MORENA",
            "CANDIDATOS_NO_REGISTRADOS", "VOTOS_NULOS", "TOTAL",
        ],
        "zona_tabla": {"x1": 0.32, "x2": 0.67, "y1": 0.08, "y2": 0.76},
    },
    "2018_presidencia": {
        "descripcion": "Eleccion presidencial 2018",
        "filas": [
            "PAN", "PRI", "PRD", "PVEM", "PT", "MC", "NA", "MORENA", "PES",
            "PAN-PRD-MC", "PAN-PRD", "PAN-MC", "PRD-MC",
            "PRI-PVEM-NA", "PRI-PVEM", "PRI-NA", "PVEM-NA",
            "PT-MORENA-PES", "PT-MORENA", "PT-PES", "MORENA-PES",
            "INDEPENDIENTE_1", "INDEPENDIENTE_2",
            "CANDIDATOS_NO_REGISTRADOS", "VOTOS_NULOS", "TOTAL",
        ],
        "zona_tabla": {"x1": 0.31, "x2": 0.66, "y1": 0.09, "y2": 0.81},
    },
    "2015_diputados": {
        "descripcion": "Diputados federales 2015 (coaliciones varian por distrito)",
        "filas": [
            "PAN", "PRI", "PRD", "PVEM", "PT", "MC", "NA", "MORENA",
            "HUMANISTA", "PES",
            "CANDIDATOS_NO_REGISTRADOS", "VOTOS_NULOS", "TOTAL",
        ],
        "zona_tabla": {"x1": 0.33, "x2": 0.68, "y1": 0.10, "y2": 0.77},
    },
}


def obtener_plantilla(eleccion: str) -> dict:
    """Devuelve la plantilla de una eleccion o lanza ValueError si no existe."""
    if eleccion not in PLANTILLAS_ACTA:
        disponibles = ", ".join(sorted(PLANTILLAS_ACTA))
        raise ValueError(
            f"Eleccion '{eleccion}' no registrada. Disponibles: {disponibles}"
        )
    return PLANTILLAS_ACTA[eleccion]
