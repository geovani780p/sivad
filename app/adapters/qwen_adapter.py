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

# Proporcion vertical de la tabla a partir de la cual se recorta la franja
# inferior que contiene las filas finales (no registrados, nulos y TOTAL).
# Se deja margen hacia arriba: el modelo ubica estas filas por su etiqueta
# impresa, por lo que incluir un renglon adicional no afecta la lectura.
INICIO_FRANJA_TOTALES = 0.75

# Filas finales comunes a todas las plantillas, con la etiqueta impresa en el acta
FILAS_FINALES = {
    "CANDIDATOS_NO_REGISTRADOS": "CANDIDATOS NO REGISTRADOS",
    "VOTOS_NULOS": "VOTOS NULOS",
    "TOTAL": "TOTAL",
}

_CAMPO_VOTOS = {
    "type": "object",
    "properties": {
        "votos_letra": {"type": "string"},
        "votos_numero": {"type": "string"},
    },
    "required": ["votos_letra", "votos_numero"],
}

# Esquema con campos nombrados: al no ser una lista, la respuesta no puede
# desfasarse de posicion como ocurre en la lectura de la tabla completa.
ESQUEMA_TOTALES = {
    "type": "object",
    "properties": {clave: _CAMPO_VOTOS for clave in FILAS_FINALES},
    "required": list(FILAS_FINALES),
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


def _aplicar_totales(datos: dict, totales: dict | None) -> dict:
    """Reemplaza las filas finales con la lectura dedicada y detecta desfases.

    Solo se reemplaza una fila cuando la lectura dedicada obtuvo un valor
    numerico. Se registra si la lectura principal presentaba el desfase de
    filas: el TOTAL de la lectura principal coincide con los VOTOS NULOS de
    la lectura dedicada, lo que indica que las filas se recorrieron un lugar.
    """
    datos["totales_verificados"] = False
    datos["desfase_detectado"] = False
    if not isinstance(totales, dict):
        return datos

    por_partido = {f["partido"]: f for f in datos["resultados"]}
    total_principal = por_partido.get("TOTAL", {}).get("votos_numero")

    lecturas = {}
    for clave in FILAS_FINALES:
        campo = totales.get(clave) if isinstance(totales.get(clave), dict) else {}
        lecturas[clave] = {
            "votos_letra": str(campo.get("votos_letra") or "").strip().lower(),
            "votos_numero": _normalizar_numero(campo.get("votos_numero")),
        }

    nulos_dedicado = lecturas["VOTOS_NULOS"]["votos_numero"]
    total_dedicado = lecturas["TOTAL"]["votos_numero"]
    datos["desfase_detectado"] = (
        total_principal is not None
        and total_dedicado is not None
        and total_principal != total_dedicado
        and total_principal == nulos_dedicado
    )

    for clave, lectura in lecturas.items():
        fila = por_partido.get(clave)
        if fila is not None and lectura["votos_numero"] is not None:
            fila["votos_letra"] = lectura["votos_letra"]
            fila["votos_numero"] = lectura["votos_numero"]
            fila["fuente"] = "lectura_dedicada"

    datos["totales_verificados"] = total_dedicado is not None
    return datos


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

    def _recortar_franja_totales(self, tabla: Image.Image) -> Image.Image:
        """Recorta la parte inferior de la tabla, donde estan las filas finales."""
        w, h = tabla.size
        return tabla.crop((0, int(h * INICIO_FRANJA_TOTALES), w, h))

    def _prompt_totales(self) -> str:
        """Prompt para leer las filas finales guiandose por su etiqueta impresa."""
        etiquetas = ", ".join(f'"{e}"' for e in FILAS_FINALES.values())
        return (
            "Esta imagen es la parte inferior de la tabla de resultados de un Acta "
            "de Escrutinio y Cómputo mexicana. Localiza las filas cuya etiqueta "
            f"impresa a la izquierda dice {etiquetas}. "
            "Guíate por esas etiquetas, no por la posición de las filas. "
            "Cada fila tiene el número de votos escrito a mano dos veces: "
            "con letra en la columna central y con dígitos en la columna derecha, "
            "en tres casillas con ceros a la izquierda (por ejemplo 467). "
            "Un cero puede aparecer cruzado por una diagonal. "
            "Transcribe exactamente lo escrito en cada una de esas tres filas: "
            "votos_letra es el texto manuscrito tal cual, "
            "votos_numero son los tres dígitos como texto."
        )

    def _leer_totales(self, tabla: Image.Image) -> dict | None:
        """Lee las filas finales en una llamada dedicada; None si falla."""
        franja = self._recortar_franja_totales(tabla)
        try:
            return self._llamar_modelo(
                franja, self._prompt_totales(), RESOLUCIONES[0], ESQUEMA_TOTALES
            )
        except (json.JSONDecodeError, requests.RequestException, KeyError):
            return None

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

    def _leer_tabla(self, tabla: Image.Image, filas: list[str]) -> dict:
        """Lee la tabla completa con reintentos a distintas resoluciones."""
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
                return datos
            if len(datos["resultados"]) > len(mejor["resultados"]):
                mejor = datos

        mejor["intentos"] = len(RESOLUCIONES)
        mejor["completa"] = False
        return mejor

    def extraer(self, imagen_bytes: bytes, eleccion: str) -> dict:
        """Extrae la tabla de resultados y verifica las filas finales por separado.

        1. Lectura principal de la tabla completa, asignando filas por posicion.
        2. Lectura dedicada de NO REGISTRADOS, NULOS y TOTAL, guiada por sus
           etiquetas impresas, que reemplaza esas filas de la lectura principal.
        """
        plantilla = obtener_plantilla(eleccion)
        filas = plantilla["filas"]
        tabla = self._recortar_tabla(imagen_bytes, plantilla["zona_tabla"])

        datos = self._leer_tabla(tabla, filas)
        datos["eleccion"] = eleccion
        if datos["completa"]:
            datos = _aplicar_totales(datos, self._leer_totales(tabla))
        else:
            datos["totales_verificados"] = False
            datos["desfase_detectado"] = False
        return datos
