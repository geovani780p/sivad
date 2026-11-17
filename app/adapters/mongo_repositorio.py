# Copyright (C) 2026 INE - Instituto Nacional Electoral
# SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
"""Adaptador de almacenamiento de actas en MongoDB."""
import hashlib
import os
from datetime import datetime, timezone

import gridfs
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING, MongoClient

from app.ports.repositorio_port import RepositorioActasPort

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
BASE_DATOS = "sivad"
COLECCION_ACTAS = "actas"
COLECCION_IMAGENES = "imagenes"
LIMITE_MAXIMO = 200


def _a_object_id(acta_id: str) -> ObjectId | None:
    """Convierte el identificador recibido a ObjectId; None si no es valido."""
    try:
        return ObjectId(acta_id)
    except (InvalidId, TypeError):
        return None


def _serializar(documento: dict) -> dict:
    """Convierte los tipos propios de MongoDB a tipos compatibles con JSON."""
    resultado = dict(documento)
    resultado["id"] = str(resultado.pop("_id"))
    resultado["imagen_id"] = str(resultado["imagen_id"])
    resultado["fecha_procesamiento"] = resultado["fecha_procesamiento"].isoformat()
    return resultado


class MongoRepositorio(RepositorioActasPort):
    """Implementacion del RepositorioActasPort sobre MongoDB y GridFS."""

    def __init__(self, url: str = MONGO_URL) -> None:
        """Prepara la conexion; MongoDB no se contacta hasta la primera operacion."""
        self._cliente = MongoClient(url, serverSelectionTimeoutMS=5000)
        base = self._cliente[BASE_DATOS]
        self._actas = base[COLECCION_ACTAS]
        self._imagenes = gridfs.GridFS(base, collection=COLECCION_IMAGENES)
        self._indices_listos = False

    def _asegurar_indices(self) -> None:
        """Crea los indices la primera vez que se usa el repositorio."""
        if not self._indices_listos:
            self._actas.create_index([("fecha_procesamiento", DESCENDING)])
            self._actas.create_index("hash_sha256")
            self._indices_listos = True

    def guardar(self, acta: dict, imagen_bytes: bytes, nombre_archivo: str) -> str:
        """Guarda la imagen en GridFS y el resultado en la coleccion de actas."""
        self._asegurar_indices()
        hash_sha256 = hashlib.sha256(imagen_bytes).hexdigest()
        imagen_id = self._imagenes.put(
            imagen_bytes, filename=nombre_archivo, hash_sha256=hash_sha256
        )
        documento = {
            **acta,
            "archivo": nombre_archivo,
            "hash_sha256": hash_sha256,
            "imagen_id": imagen_id,
            "fecha_procesamiento": datetime.now(timezone.utc),
        }
        try:
            return str(self._actas.insert_one(documento).inserted_id)
        except Exception:
            # Si el resultado no se pudo guardar, no se deja la imagen huerfana
            self._imagenes.delete(imagen_id)
            raise

    def obtener(self, acta_id: str) -> dict | None:
        """Devuelve un acta guardada, o None si no existe."""
        oid = _a_object_id(acta_id)
        if oid is None:
            return None
        documento = self._actas.find_one({"_id": oid})
        return _serializar(documento) if documento else None

    def obtener_imagen(self, acta_id: str) -> bytes | None:
        """Devuelve la imagen original de un acta, o None si no existe."""
        oid = _a_object_id(acta_id)
        if oid is None:
            return None
        documento = self._actas.find_one({"_id": oid}, {"imagen_id": 1})
        if documento is None:
            return None
        try:
            return self._imagenes.get(documento["imagen_id"]).read()
        except gridfs.errors.NoFile:
            return None

    def listar(self, limite: int = 50) -> list[dict]:
        """Devuelve un resumen de las actas mas recientes, sin filas ni imagenes."""
        self._asegurar_indices()
        limite = max(1, min(limite, LIMITE_MAXIMO))
        cursor = (
            self._actas.find({}, {"resultados": 0})
            .sort([("fecha_procesamiento", DESCENDING), ("_id", DESCENDING)])
            .limit(limite)
        )
        return [_serializar(documento) for documento in cursor]
