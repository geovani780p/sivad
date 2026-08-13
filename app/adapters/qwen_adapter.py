# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Adaptador de extracción usando Qwen 2.5 Vision a través de Ollama."""
import base64
import json
import re

import requests

from app.ports.extractor_port import ExtractorPort

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO = "qwen2.5vl:7b"


class QwenAdapter(ExtractorPort):
    """Implementación del ExtractorPort usando Qwen 2.5 Vision con Ollama local."""

    def extraer(self, imagen_bytes: bytes, tipo_documento: str) -> dict:
        """Extrae datos del documento usando Qwen Vision de forma local."""
        imagen_b64 = base64.b64encode(imagen_bytes).decode("utf-8")
        prompt = (
            "Eres un sistema de extracción de datos de documentos oficiales mexicanos. "
            f"Analiza la imagen y extrae todos los datos visibles del documento tipo: {tipo_documento}. "
            "Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional, sin markdown, sin ```json. "
            "Solo el JSON puro con los campos encontrados."
        )
        respuesta = requests.post(
            OLLAMA_URL,
            json={
                "model": MODELO,
                "prompt": prompt,
                "images": [imagen_b64],
                "stream": False,
            },
            timeout=120,
        )
        respuesta.raise_for_status()
        texto = re.sub(r"```json|```", "", respuesta.json()["response"].strip()).strip()
        return json.loads(texto)
