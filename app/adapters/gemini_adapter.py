# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Adaptador de extracción usando Google Gemini."""
import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.ports.extractor_port import ExtractorPort

load_dotenv()


class GeminiAdapter(ExtractorPort):
    """Implementación del ExtractorPort usando la API de Google Gemini."""

    def __init__(self) -> None:
        """Inicializa el cliente de Gemini con la API key del entorno."""
        self._client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def extraer(self, imagen_bytes: bytes, tipo_documento: str) -> dict:
        """Extrae datos del documento usando Gemini Vision."""
        prompt = (
            "Eres un sistema de extracción de datos de documentos oficiales mexicanos. "
            f"Analiza la imagen y extrae todos los datos visibles del documento tipo: {tipo_documento}. "
            "Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional, sin markdown, sin ```json. "
            "Solo el JSON puro con los campos encontrados."
        )
        respuesta = self._client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                types.Part.from_bytes(data=imagen_bytes, mime_type="image/jpeg"),
                prompt,
            ],
        )
        texto = re.sub(r"```json|```", "", respuesta.text.strip()).strip()
        return json.loads(texto)
