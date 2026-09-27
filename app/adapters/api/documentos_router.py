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

# Proporcion minima de filas con confianza alta (letra y numero coinciden)
# para aprobar un acta sin revision humana. Evita validar actas en las que
# ninguna fila tuvo doble confirmacion aunque la suma haya cuadrado.
MIN_PROPORCION_ALTA = 0.5


def _motivos_revision(datos: dict, suma: dict, confianza: dict, n_filas: int) -> list[str]:
    """Devuelve la lista de razones por las que el acta requiere revision humana."""
    motivos = []
    if not datos.get("completa", False):
        motivos.append("El modelo no devolvio todas las filas del acta")
    if not suma["valida"]:
        motivos.append(suma["motivo"])
    if confianza["baja"] > 0:
        motivos.append(f"{confianza['baja']} fila(s) con letra y numero contradictorios")
    if n_filas and confianza["alta"] / n_filas < MIN_PROPORCION_ALTA:
        motivos.append(
            f"Solo {confianza['alta']} de {n_filas} filas con doble confirmacion "
            f"(minimo {int(MIN_PROPORCION_ALTA * 100)}%)"
        )
    return motivos


def _evaluar(datos: dict) -> dict:
    """Aplica el agente validador sobre los datos extraidos."""
    filas = reconciliar(datos.get("resultados", []))
    suma = validar_suma(filas)
    confianza = {
        "alta": sum(1 for f in filas if f["confianza"] == "alta"),
        "media": sum(1 for f in filas if f["confianza"] == "media"),
        "baja": sum(1 for f in filas if f["confianza"] == "baja"),
    }
    motivos = _motivos_revision(datos, suma, confianza, len(filas))
    return {
        "eleccion": datos.get("eleccion"),
        "resultados": filas,
        "completa": datos.get("completa", False),
        "intentos": datos.get("intentos", 1),
        "totales_verificados": datos.get("totales_verificados", False),
        "desfase_detectado": datos.get("desfase_detectado", False),
        "validacion": {
            "suma": suma,
            "confianza": confianza,
            "requiere_revision_humana": bool(motivos),
            "motivos_revision": motivos,
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
