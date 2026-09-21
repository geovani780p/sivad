# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Adaptador de extracción usando Qwen 2.5 Vision a través de Ollama."""
import base64
import io
import json
import re

import requests
from PIL import Image

from app.domain.plantillas import obtener_plantilla
from app.ports.extractor_port import ExtractorPort

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO = "qwen2.5vl:7b"
RESOLUCIONES = [1280, 1600, 1024]

# repeat_penalty se mantiene en 1.0: en una respuesta JSON los tokens se
# repiten de forma legitima (nombres de campo, ceros), por lo que penalizar
# la repeticion induce al modelo a inventar valores distintos.
OPCIONES_MODELO = {
    "num_predict": 4096,
    "num_ctx": 8192,
    "temperature": 0,
    "repeat_penalty": 1.0,
}


def _esquema_respuesta(n_filas: int) -> dict:
    """Construye el JSON Schema que obliga al modelo a devolver n_filas exactas.

    Los votos en numero se solicitan como texto porque en el acta se escriben
    con ceros a la izquierda (por ejemplo 047), formato que no es un numero
    JSON valido.
    """
    return {
        "type": "object",
        "properties": {
            "resultados": {
                "type": "array",
                "minItems": n_filas,
                "maxItems": n_filas,
                "items": {
                    "type": "object",
                    "properties": {
                        "votos_letra": {"type": "string"},
                        "votos_numero": {"type": "string"},
                    },
                    "required": ["votos_letra", "votos_numero"],
                },
            }
        },
        "required": ["resultados"],
    }


def _normalizar_numero(valor) -> int | None:
    """Convierte el valor a entero; devuelve None si no es un numero valido."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor if valor >= 0 else None
    if isinstance(valor, str):
        solo_numeros = re.sub(r"[^\d]", "", valor)
        if not solo_numeros or len(solo_numeros) > 6:
            return None
        return int(solo_numeros)
    return None


def _asignar_por_posicion(datos: dict, filas_plantilla: list[str]) -> dict:
    """Asocia cada fila extraida con la etiqueta que le corresponde por posicion.

    La plantilla del proceso electoral define el orden de las filas, por lo que
    la etiqueta se determina por indice y no por el texto que devuelva el
    modelo. Esto evita desalineaciones silenciosas.
    """
    resultados = datos.get("resultados", []) if isinstance(datos, dict) else []
    asignados = []
    for indice, fila in enumerate(resultados):
        if indice >= len(filas_plantilla):
            break
        if not isinstance(fila, dict):
            fila = {}
        asignados.append({
            "partido": filas_plantilla[indice],
            "votos_letra": str(fila.get("votos_letra") or "").strip().lower(),
            "votos_numero": _normalizar_numero(fila.get("votos_numero")),
        })
    return {"resultados": asignados}


class QwenAdapter(ExtractorPort):
    """Implementación del ExtractorPort usando Qwen 2.5 Vision con Ollama local."""

    def _recortar_tabla(self, imagen_bytes: bytes, zona: dict) -> Image.Image:
        """Recorta la region de la tabla de resultados segun la plantilla."""
        img = Image.open(io.BytesIO(imagen_bytes)).convert("RGB")
        w, h = img.size
        caja = (
            int(w * zona["x1"]),
            int(h * zona["y1"]),
            int(w * zona["x2"]),
            int(h * zona["y2"]),
        )
        return img.crop(caja)

    def _redimensionar(self, img: Image.Image, max_px: int) -> bytes:
        """Ajusta la imagen a max_px en su lado mas largo y la codifica en JPEG."""
        w, h = img.size
        if max(w, h) > max_px:
            factor = max_px / max(w, h)
            img = img.resize((int(w * factor), int(h * factor)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue()

    def _construir_prompt(self, filas: list[str]) -> str:
        """Arma el prompt a partir de la lista de filas de la plantilla."""
        lista = " ".join(f"{i}.{p}" for i, p in enumerate(filas, 1))
        return (
            "Esta imagen es la tabla de resultados de un Acta de Escrutinio y Cómputo "
            f"mexicana. Tiene {len(filas)} filas, de arriba hacia abajo: {lista}. "
            "Lee cada fila en ese orden, de arriba hacia abajo, sin saltarte ninguna. "
            "Cada fila tiene el número de votos escrito a mano dos veces: "
            "con letra en la columna central y con dígitos en la columna derecha. "
            "La columna derecha tiene tres casillas, una por dígito, "
            "y se completa con ceros a la izquierda (por ejemplo 047). "
            "Un cero puede aparecer cruzado por una diagonal. "
            "Transcribe exactamente lo que está escrito: "
            "votos_letra es el texto manuscrito tal cual, "
            "votos_numero son los tres dígitos como texto. "
            "Si un renglón no tiene nada escrito, deja ambos campos como cadena vacía."
        )

    def _llamar_modelo(
        self, tabla: Image.Image, prompt: str, max_px: int, esquema: dict
    ) -> dict:
        """Envia la tabla recortada a Ollama y devuelve el JSON de respuesta."""
        imagen_b64 = base64.b64encode(self._redimensionar(tabla, max_px)).decode("utf-8")
        respuesta = requests.post(
            OLLAMA_URL,
            json={
                "model": MODELO,
                "prompt": prompt,
                "images": [imagen_b64],
                "stream": False,
                "format": esquema,
                "options": OPCIONES_MODELO,
            },
            timeout=300,
        )
        respuesta.raise_for_status()
        texto = re.sub(r"```json|```", "", respuesta.json()["response"].strip()).strip()
        return json.loads(texto)

    def extraer(self, imagen_bytes: bytes, eleccion: str) -> dict:
        """Extrae la tabla de resultados con reintentos a distintas resoluciones."""
        plantilla = obtener_plantilla(eleccion)
        filas = plantilla["filas"]
        tabla = self._recortar_tabla(imagen_bytes, plantilla["zona_tabla"])
        prompt = self._construir_prompt(filas)
        esquema = _esquema_respuesta(len(filas))

        mejor = {"resultados": []}
        for intento, max_px in enumerate(RESOLUCIONES, 1):
            try:
                datos = _asignar_por_posicion(
                    self._llamar_modelo(tabla, prompt, max_px, esquema), filas
                )
            except (json.JSONDecodeError, requests.RequestException, KeyError):
                continue
            if len(datos["resultados"]) == len(filas):
                datos["intentos"] = intento
                datos["completa"] = True
                datos["eleccion"] = eleccion
                return datos
            if len(datos["resultados"]) > len(mejor["resultados"]):
                mejor = datos

        mejor["intentos"] = len(RESOLUCIONES)
        mejor["completa"] = False
        mejor["eleccion"] = eleccion
        return mejor
