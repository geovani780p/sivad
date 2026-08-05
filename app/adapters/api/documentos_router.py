# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Adaptador HTTP para el recurso documentos."""
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.adapters.gemini_adapter import GeminiAdapter
from app.domain.documento import Documento

router = APIRouter()
_extractor = GeminiAdapter()

_RESPONSES = {
    400: {"description": "Tipo de archivo no permitido. Solo JPG o PNG."},
    500: {"description": "Error interno al procesar el documento con Gemini."},
}


@router.post("/validar", responses=_RESPONSES)
async def validar_documento(
    archivo: Annotated[UploadFile, File(description="Imagen del documento oficial")],
    tipo_documento: str = "credencial de elector",
) -> dict:
    """Recibe una imagen y devuelve los datos extraídos del documento."""
    if archivo.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=400,
            detail="Solo se aceptan imágenes JPG o PNG",
        )
    imagen_bytes = await archivo.read()
    try:
        datos = _extractor.extraer(imagen_bytes, tipo_documento)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el documento: {exc}",
        ) from exc

    documento = Documento(
        tipo=tipo_documento,
        nombre_archivo=archivo.filename or "",
        datos_extraidos=datos,
    )
    return {
        "tipo_documento": documento.tipo,
        "archivo": documento.nombre_archivo,
        "datos_extraidos": documento.datos_extraidos,
    }
