# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Adaptador HTTP para el recurso documentos."""
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.adapters.qwen_adapter import QwenAdapter
from app.agents.validador import reconciliar, validar_suma
from app.domain.documento import Documento
from app.domain.plantillas import PLANTILLAS_ACTA

router = APIRouter()
_extractor = QwenAdapter()

_RESPONSES = {
    400: {"description": "Archivo no permitido o eleccion no registrada."},
    500: {"description": "Error interno al procesar el documento."},
}


def _evaluar(datos: dict) -> dict:
    """Aplica el agente validador sobre los datos extraidos."""
    filas = reconciliar(datos.get("resultados", []))
    suma = validar_suma(filas)
    confianza = {
        "alta": sum(1 for f in filas if f["confianza"] == "alta"),
        "media": sum(1 for f in filas if f["confianza"] == "media"),
        "baja": sum(1 for f in filas if f["confianza"] == "baja"),
    }
    requiere_revision = (
        not datos.get("completa", False)
        or not suma["valida"]
        or confianza["baja"] > 0
    )
    return {
        "eleccion": datos.get("eleccion"),
        "resultados": filas,
        "completa": datos.get("completa", False),
        "intentos": datos.get("intentos", 1),
        "validacion": {
            "suma": suma,
            "confianza": confianza,
            "requiere_revision_humana": requiere_revision,
        },
    }


@router.get("/elecciones")
def listar_elecciones() -> dict:
    """Devuelve las elecciones con plantilla registrada."""
    return {
        clave: {"descripcion": p["descripcion"], "filas": len(p["filas"])}
        for clave, p in PLANTILLAS_ACTA.items()
    }


@router.post("/validar", responses=_RESPONSES)
async def validar_documento(
    archivo: Annotated[UploadFile, File(description="Imagen del acta (JPG o PNG)")],
    eleccion: Annotated[
        str, Query(description="Clave de la eleccion, ver GET /documentos/elecciones")
    ] = "2024_presidencia",
) -> dict:
    """Recibe la imagen de un acta, extrae los resultados y los valida."""
    if archivo.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Solo se aceptan imágenes JPG o PNG")
    if eleccion not in PLANTILLAS_ACTA:
        raise HTTPException(
            status_code=400,
            detail=f"Eleccion no registrada. Disponibles: {', '.join(PLANTILLAS_ACTA)}",
        )
    imagen_bytes = await archivo.read()
    try:
        extraidos = _extractor.extraer(imagen_bytes, eleccion)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el documento: {exc}",
        ) from exc

    documento = Documento(
        tipo=eleccion,
        nombre_archivo=archivo.filename or "",
        datos_extraidos=_evaluar(extraidos),
    )
    return {
        "eleccion": documento.tipo,
        "archivo": documento.nombre_archivo,
        "datos_extraidos": documento.datos_extraidos,
    }
