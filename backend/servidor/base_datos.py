"""Base de datos MongoDB con pymongo.

La conexión se lee de backend/.env (o de las variables de entorno):
    MONGO_URI   p. ej. mongodb://127.0.0.1:27017 o, en Atlas, mongodb+srv://usuario:clave@cluster.mongodb.net
    MONGO_BD    nombre de la base (por defecto secrets_of_style)

Colecciones (ver esquemas.py): usuarios (con perfil, preferencias y pesos embebidos), prendas, atuendos
(con sus elementos embebidos), votos_atuendo, pruebas_atuendo, climas y contadores.
"""

import atexit
import os
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient, ReturnDocument

from servidor.esquemas import ESQUEMAS, INDICES

CARPETA_BACKEND = Path(__file__).resolve().parent.parent
CARPETA_ARCHIVOS = CARPETA_BACKEND / "archivos_subidos"
# Fotos del cuerpo y resultados del probador. No se sirve como /archivos: solo se entrega con sesión.
CARPETA_PRIVADA = CARPETA_BACKEND / "privado"
RUTA_ENV = CARPETA_BACKEND / ".env"


def leer_env():
    """Carga backend/.env (líneas CLAVE=valor) sin pisar las variables que ya existen."""
    if RUTA_ENV.exists():
        for linea in RUTA_ENV.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip())


leer_env()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
NOMBRE_BD = os.getenv("MONGO_BD", "secrets_of_style")

cliente = None


def bd():
    """La base de datos. El cliente se crea una sola vez y lo comparten todos los hilos (es seguro)."""
    global cliente
    if cliente is None:
        cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, appname="secrets_of_style")
    return cliente[NOMBRE_BD]


def usar_base_de_prueba():
    """Para las pruebas: una base con nombre único que se borra al terminar. No toca secrets_of_style."""
    global NOMBRE_BD
    NOMBRE_BD = f"{NOMBRE_BD}_prueba_{os.getpid()}_{datetime.now():%H%M%S%f}"
    atexit.register(lambda: bd().client.drop_database(NOMBRE_BD))


def crear_colecciones():
    """Crea las colecciones con su validación ($jsonSchema) y sus índices. Si ya existen, actualiza la validación."""
    base = bd()
    existentes = set(base.list_collection_names())
    for nombre, esquema in ESQUEMAS.items():
        validacion = {"$jsonSchema": esquema}
        if nombre in existentes:
            base.command("collMod", nombre, validator=validacion, validationLevel="strict", validationAction="error")
        else:
            base.create_collection(nombre, validator=validacion, validationLevel="strict", validationAction="error")
    for nombre, indices in INDICES.items():
        for campos, opciones in indices:
            base[nombre].create_index(campos, **opciones)


def siguiente_id(coleccion: str) -> int:
    """El siguiente número de la colección. $inc es atómico: dos peticiones a la vez nunca reciben el mismo."""
    contador = bd().contadores.find_one_and_update(
        {"_id": coleccion}, {"$inc": {"valor": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return contador["valor"]


def ahora() -> datetime:
    """Fecha y hora en UTC (MongoDB guarda las fechas en UTC)."""
    return datetime.now(timezone.utc)


def como_dict(documento: dict | None) -> dict | None:
    """Documento → lo que responde la API: _id pasa a id y las fechas a texto 'AAAA-MM-DD HH:MM:SS' (UTC)."""
    if documento is None:
        return None
    resultado = {"id": documento["_id"]} if "_id" in documento else {}
    for campo, valor in documento.items():
        if campo != "_id":
            resultado[campo] = valor.strftime("%Y-%m-%d %H:%M:%S") if isinstance(valor, datetime) else valor
    return resultado
