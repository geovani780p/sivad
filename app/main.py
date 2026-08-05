# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Punto de entrada de SIVAD."""
from fastapi import FastAPI

from app.adapters.api.documentos_router import router as documentos_router

app = FastAPI(
    title="SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos",
    description="API para la validacion y extraccion de documentos oficiales",
    version="1.0.0",
)

app.include_router(documentos_router, prefix="/documentos", tags=["Documentos"])


@app.get("/")
def root() -> dict:
    """Health check raíz."""
    return {"message": "SIVAD activo", "version": "1.0.0"}


@app.get("/health")
def health() -> dict:
    """Health check."""
    return {"status": "ok"}
