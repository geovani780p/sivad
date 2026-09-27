# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Agente validador: convierte votos en letra a numero y verifica la suma del acta.

Este modulo no utiliza inteligencia artificial. Todas sus operaciones son
deterministas, por lo que su resultado es siempre reproducible y auditable.
"""
import difflib
import re
import unicodedata

# Unidades y numeros irregulares del espanol
_UNIDADES = {
    "cero": 0, "uno": 1, "una": 1, "un": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20, "veintiuno": 21, "veintiun": 21, "veintiuna": 21,
    "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
}

_DECENAS = {
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
    "setenta": 70, "ochenta": 80, "noventa": 90,
}

_CENTENAS = {
    "cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200,
    "trescientos": 300, "trescientas": 300, "cuatrocientos": 400,
    "cuatrocientas": 400, "quinientos": 500, "quinientas": 500,
    "seiscientos": 600, "seiscientas": 600, "setecientos": 700,
    "setecientas": 700, "ochocientos": 800, "ochocientas": 800,
    "novecientos": 900, "novecientas": 900,
}

_VOCABULARIO = {**_UNIDADES, **_DECENAS, **_CENTENAS, "mil": 1000}

# Prefijos que en la escritura manual suelen separarse de su raiz,
# p. ej. "veinti tres" o "dos cientos"
_PREFIJOS_PEGABLES = ("veinti", "dieci", "dos", "tres", "cuatro", "quinien",
                    "seis", "siete", "ocho", "nove")


def _normalizar(texto) -> str:
    """Quita acentos, signos y espacios sobrantes; devuelve minusculas."""
    texto = str(texto or "").lower().strip()
    sin_acentos = unicodedata.normalize("NFD", texto)
    limpio = "".join(c for c in sin_acentos if unicodedata.category(c) != "Mn")
    limpio = re.sub(r"[^a-z\s]", " ", limpio)
    return re.sub(r"\s+", " ", limpio).strip()


def _unir_prefijos(palabras: list[str]) -> list[str]:
    """Une prefijos separados por error de escritura: 'veinti tres' -> 'veintitres'."""
    unidas = []
    i = 0
    while i < len(palabras):
        actual = palabras[i]
        if (
            i + 1 < len(palabras)
            and actual not in _VOCABULARIO
            and actual.startswith(_PREFIJOS_PEGABLES)
        ):
            candidato = actual + palabras[i + 1]
            if candidato in _VOCABULARIO:
                unidas.append(candidato)
                i += 2
                continue
        # Caso "dos cientos" -> "doscientos": el primer termino si es valido
        if i + 1 < len(palabras):
            candidato = actual + palabras[i + 1]
            if candidato in _CENTENAS:
                unidas.append(candidato)
                i += 2
                continue
        unidas.append(actual)
        i += 1
    return unidas


def _corregir_palabra(palabra: str) -> str | None:
    """Corrige faltas de ortografia contra el vocabulario numerico."""
    if palabra in _VOCABULARIO:
        return palabra
    coincidencias = difflib.get_close_matches(palabra, _VOCABULARIO, n=1, cutoff=0.75)
    return coincidencias[0] if coincidencias else None


def letra_a_numero(texto) -> int | None:
    """Convierte un numero escrito en letra a entero.

    Tolera faltas de ortografia, separaciones incorrectas y formas coloquiales
    comunes en la escritura manual de las actas:
        "cuatrocientos sesenta y siete" -> 467
        "veinti tres"                   -> 23
        "dos cientos"                   -> 200
        "quiace"                        -> 15
        "tres treinta y cinco"          -> 335  (centena coloquial)

    Devuelve None si el texto no representa un numero reconocible.
    """
    normalizado = _normalizar(texto)
    if not normalizado:
        return None

    palabras = [p for p in normalizado.split() if p not in ("y", "")]
    if not palabras:
        return None

    palabras = _unir_prefijos(palabras)

    total = 0
    parcial = 0
    encontro_algo = False

    for palabra in palabras:
        termino = _corregir_palabra(palabra)
        if termino is None:
            return None
        if termino == "mil":
            parcial = parcial if parcial else 1
            total += parcial * 1000
            parcial = 0
        elif termino in _CENTENAS:
            parcial += _CENTENAS[termino]
        else:
            valor = _DECENAS.get(termino, _UNIDADES.get(termino, 0))
            # Centena coloquial: en espanol correcto una unidad nunca precede a
            # una decena, por lo que "tres treinta" solo puede significar 330.
            if valor >= 10 and 1 <= parcial <= 9:
                parcial *= 100
            parcial += valor
        encontro_algo = True

    return total + parcial if encontro_algo else None


def validar_suma(resultados: list[dict]) -> dict:
    """Verifica que la suma de las filas coincida con la fila TOTAL del acta.

    Recibe la lista de filas extraidas y devuelve un diccionario con el
    resultado de la validacion, sin modificar los datos de entrada.
    """
    filas_suma = [f for f in resultados if f.get("partido") != "TOTAL"]
    fila_total = next((f for f in resultados if f.get("partido") == "TOTAL"), None)

    if fila_total is None:
        return {
            "valida": False,
            "motivo": "El acta no contiene fila TOTAL",
            "suma_calculada": None,
            "total_declarado": None,
            "diferencia": None,
        }

    valores = [f.get("votos_numero") for f in filas_suma]
    if any(v is None for v in valores):
        faltantes = sum(1 for v in valores if v is None)
        return {
            "valida": False,
            "motivo": f"{faltantes} fila(s) sin valor numerico",
            "suma_calculada": None,
            "total_declarado": fila_total.get("votos_numero"),
            "diferencia": None,
        }

    suma = sum(valores)
    total = fila_total.get("votos_numero")

    if total is None:
        return {
            "valida": False,
            "motivo": "La fila TOTAL no tiene valor numerico",
            "suma_calculada": suma,
            "total_declarado": None,
            "diferencia": None,
        }

    diferencia = suma - total
    return {
        "valida": diferencia == 0,
        "motivo": "Suma correcta" if diferencia == 0 else "La suma no coincide con el total",
        "suma_calculada": suma,
        "total_declarado": total,
        "diferencia": diferencia,
    }


def reconciliar(resultados: list[dict]) -> list[dict]:
    """Compara los votos en letra contra los votos en numero de cada fila.

    Agrega a cada fila los campos 'votos_letra_numero' y 'confianza':
        alta  - letra y numero coinciden
        media - solo se pudo leer una de las dos fuentes
        baja  - letra y numero no coinciden
    """
    reconciliados = []
    for fila in resultados:
        desde_letra = letra_a_numero(fila.get("votos_letra"))
        desde_numero = fila.get("votos_numero")

        if desde_letra is not None and desde_numero is not None:
            confianza = "alta" if desde_letra == desde_numero else "baja"
        elif desde_letra is not None or desde_numero is not None:
            confianza = "media"
        else:
            confianza = "baja"

        reconciliados.append({
            **fila,
            "votos_letra_numero": desde_letra,
            "confianza": confianza,
        })
    return reconciliados
