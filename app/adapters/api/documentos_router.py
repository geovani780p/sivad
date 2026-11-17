# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Adaptador HTTP para el recurso documentos."""
import logging
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile

from app.adapters.mongo_repositorio import MongoRepositorio
from app.adapters.qwen_adapter import MODELO, VERSION_PROMPT, QwenAdapter
from app.agents.validador import reconciliar, validar_suma
from app.domain.documento import Documento
from app.domain.plantillas import PLANTILLAS_ACTA
from app.ports.repositorio_port import RepositorioActasPort

logger = logging.getLogger(__name__)

router = APIRouter()
_extractor = QwenAdapter()
_repositorio: RepositorioActasPort = MongoRepositorio()

_RESPONSES = {
    400: {"description": "Archivo no permitido o eleccion no registrada."},
    500: {"description": "Error interno al procesar el documento."},
}
_RESPONSES_ACTA = {404: {"description": "No existe un acta con ese identificador."}}

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


def _guardar(evaluacion: dict, imagen_bytes: bytes, nombre_archivo: str) -> str | None:
    """Guarda el acta procesada; devuelve su identificador o None si falla.

    Una falla de la base de datos no impide entregar el resultado de la
    extraccion, pero queda registrada y se informa en la respuesta.
    """
    revision = evaluacion["validacion"]["requiere_revision_humana"]
    acta = {
        **evaluacion,
        "estado": "revision_humana" if revision else "validada",
        "modelo": MODELO,
        "version_prompt": VERSION_PROMPT,
    }
    try:
        return _repositorio.guardar(acta, imagen_bytes, nombre_archivo)
    except Exception:
        logger.exception("No se pudo guardar el acta %s en la base de datos", nombre_archivo)
        return None


def _tipo_imagen(imagen_bytes: bytes) -> str:
    """Identifica si la imagen es PNG o JPEG a partir de sus primeros bytes."""
    return "image/png" if imagen_bytes.startswith(b"\x89PNG") else "image/jpeg"


@router.get("/elecciones")
def listar_elecciones() -> dict:
    """Devuelve las elecciones con plantilla registrada."""
    return {
        clave: {"descripcion": p["descripcion"], "filas": len(p["filas"])}
        for clave, p in PLANTILLAS_ACTA.items()
    }


@router.post("/validar", responses=_RESPONSES)
def validar_documento(
    archivo: Annotated[UploadFile, File(description="Imagen del acta (JPG o PNG)")],
    eleccion: Annotated[
        str, Query(description="Clave de la eleccion, ver GET /documentos/elecciones")
    ] = "2024_presidencia",
) -> dict:
    """Recibe la imagen de un acta, extrae los resultados, los valida y los guarda."""
    if archivo.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Solo se aceptan imágenes JPG o PNG")
    if eleccion not in PLANTILLAS_ACTA:
        raise HTTPException(
            status_code=400,
            detail=f"Eleccion no registrada. Disponibles: {', '.join(PLANTILLAS_ACTA)}",
        )
    imagen_bytes = archivo.file.read()
    nombre_archivo = archivo.filename or ""
    try:
        extraidos = _extractor.extraer(imagen_bytes, eleccion)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el documento: {exc}",
        ) from exc

    evaluacion = _evaluar(extraidos)
    acta_id = _guardar(evaluacion, imagen_bytes, nombre_archivo)

    documento = Documento(
        tipo=eleccion,
        nombre_archivo=nombre_archivo,
        datos_extraidos=evaluacion,
    )
    return {
        "id": acta_id,
        "guardado": acta_id is not None,
        "eleccion": documento.tipo,
        "archivo": documento.nombre_archivo,
        "datos_extraidos": documento.datos_extraidos,
    }


@router.get("/actas")
def listar_actas(
    limite: Annotated[
        int, Query(ge=1, le=200, description="Cantidad maxima de actas a devolver")
    ] = 50,
) -> list[dict]:
    """Devuelve las actas procesadas mas recientes, sin filas ni imagenes."""
    return _repositorio.listar(limite)


@router.get("/actas/{acta_id}", responses=_RESPONSES_ACTA)
def obtener_acta(acta_id: str) -> dict:
    """Devuelve el resultado completo de un acta guardada."""
    acta = _repositorio.obtener(acta_id)
    if acta is None:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    return acta


@router.get("/actas/{acta_id}/imagen", responses=_RESPONSES_ACTA)
def obtener_imagen_acta(acta_id: str) -> Response:
    """Devuelve la imagen original con la que se proceso el acta."""
    imagen = _repositorio.obtener_imagen(acta_id)
    if imagen is None:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    return Response(content=imagen, media_type=_tipo_imagen(imagen))
