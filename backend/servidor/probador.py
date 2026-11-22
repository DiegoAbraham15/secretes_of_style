"""Probador virtual: viste la foto de la persona con las prendas de un look.

La IA (CatVTON) corre en el motor (backend/motor), un programa aparte con su propio Python. Aquí está la
parte del servidor:
  Pasadas   qué prendas se visten y en qué orden. CatVTON cambia una prenda por pasada y la reemplaza, no la
            pone encima: primero la parte inferior y luego el abrigo o, si no hay, la parte superior. El
            calzado y los accesorios no se generan.
  Cola      un hilo atiende las pruebas de una en una, porque la GPU solo alcanza para una.
  Caché     cada resultado se guarda con la firma de las prendas vestidas y la versión de la foto. Los looks
            que comparten pantalón reutilizan esa pasada; cambiar de foto invalida todo lo anterior.
  Privacidad la foto y los resultados van a backend/privado, que no se sirve como /archivos: la app los pide
            con su sesión.
"""

import shutil
import threading
import time
import uuid
from pathlib import Path

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from servidor import base_datos, gpu, ollama
from servidor.aprendizaje import firma_de
from servidor.base_datos import ahora, bd, como_dict, siguiente_id

MAXIMO_PRUEBAS = 40  # por persona; al pasar se borran las de uso más viejo
ESPERA_VALIDAR = 120
ESPERA_VESTIR = 300
TIPO_DE_PASADA = {"parte_inferior": "lower", "parte_superior": "upper", "abrigo": "upper"}

despertar = threading.Event()
hilo = None


# ------------------------------------------------
# 1. PASADAS
# ------------------------------------------------

def pasadas_de(prendas: list[dict]) -> list[dict]:
    """Las prendas que se visten, en orden. Con abrigo, la parte superior queda debajo y no se viste."""
    por_categoria = {p["categoria"]: p for p in prendas}
    arriba = por_categoria.get("abrigo") or por_categoria.get("parte_superior")
    return [p for p in (por_categoria.get("parte_inferior"), arriba) if p]


def firma_de_pasadas(pasadas: list[dict]) -> str:
    return firma_de([p["id"] for p in pasadas])


# ------------------------------------------------
# 2. ARCHIVOS PRIVADOS
# ------------------------------------------------

def carpeta(*partes) -> Path:
    ruta = base_datos.CARPETA_PRIVADA.joinpath(*partes)
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def borrar_archivo(ruta: str | None):
    if ruta:
        Path(ruta).unlink(missing_ok=True)


def leer_prueba(filtro: dict, **opciones) -> dict | None:
    """Una prueba de la colección pruebas_atuendo, con id en lugar de _id."""
    return como_dict(bd().pruebas_atuendo.find_one(filtro, **opciones))


def pruebas_de(usuario_id: int) -> list[dict]:
    return [como_dict(p) for p in bd().pruebas_atuendo.find({"usuario_id": usuario_id}, {"ruta": 1, "firma": 1})]


def borrar_pruebas(filas: list[dict]):
    for fila in filas:
        borrar_archivo(fila["ruta"])
        bd().pruebas_atuendo.delete_one({"_id": fila["id"]})


def foto_de(usuario_id: int) -> dict:
    """foto_cuerpo y version_foto, del perfil embebido en el usuario."""
    usuario = bd().usuarios.find_one({"_id": usuario_id}, {"perfil.foto_cuerpo": 1, "perfil.version_foto": 1})
    return (usuario or {}).get("perfil", {})


def guardar_foto(usuario_id: int, contenido: bytes, extension: str):
    """Valida la foto con el motor y, si sirve, reemplaza la anterior y todo lo generado con ella."""
    temporal = carpeta("cuerpos") / f"revision_{uuid.uuid4().hex}{extension}"
    temporal.write_bytes(contenido)
    try:
        revision = gpu.pedir_al_motor("/validar", {"foto": str(temporal)}, ESPERA_VALIDAR)
    except HTTPException:
        temporal.unlink(missing_ok=True)
        raise
    if not revision["valida"]:
        temporal.unlink(missing_ok=True)
        raise HTTPException(422, revision["motivo"])
    borrar_foto(usuario_id)
    definitiva = temporal.with_name(f"{usuario_id}_{uuid.uuid4().hex}{extension}")
    temporal.rename(definitiva)
    bd().usuarios.update_one({"_id": usuario_id}, {"$set": {"perfil.foto_cuerpo": str(definitiva)}})


def borrar_foto(usuario_id: int):
    """Borra la foto y todas las pruebas. Subir la versión invalida lo que el hilo esté generando."""
    borrar_archivo(foto_de(usuario_id).get("foto_cuerpo"))
    borrar_pruebas(pruebas_de(usuario_id))
    shutil.rmtree(base_datos.CARPETA_PRIVADA / "pruebas" / str(usuario_id), ignore_errors=True)
    bd().usuarios.update_one({"_id": usuario_id}, {"$set": {"perfil.foto_cuerpo": None}, "$inc": {"perfil.version_foto": 1}})


def olvidar_prenda(usuario_id: int, prenda_id: int):
    """Al borrar una prenda se borran las pruebas donde aparece."""
    borrar_pruebas([f for f in pruebas_de(usuario_id) if str(prenda_id) in f["firma"].split("-")])


def limpiar_viejas(usuario_id: int):
    """Deja solo las MAXIMO_PRUEBAS terminadas de uso más reciente."""
    viejas = (bd().pruebas_atuendo.find({"usuario_id": usuario_id, "estado": {"$in": ["lista", "error"]}}, {"ruta": 1})
              .sort([("fecha_uso", -1), ("_id", -1)]).skip(MAXIMO_PRUEBAS))
    borrar_pruebas([como_dict(p) for p in viejas])


# ------------------------------------------------
# 3. PEDIR Y CONSULTAR
# ------------------------------------------------

def estado_de(prueba: dict) -> dict:
    """Lo que ve la app: en qué va la prueba y, cuando está lista, de dónde bajar la imagen."""
    respuesta = {
        "id": prueba["id"],
        "estado": prueba["estado"],
        "paso": prueba["paso"],
        "pasos": prueba["pasos"],
        "vestidas": [int(i) for i in prueba["firma"].split("-")],
        "error": prueba["error"],
        "segundos": prueba["segundos"],
        "url": None,
        "delante": 0,
    }
    if prueba["estado"] == "lista":
        # El nombre del archivo va en la URL: si el id se reutiliza, el teléfono no muestra la imagen vieja de su caché.
        respuesta["url"] = f"/api/atuendos/probador/{prueba['id']}/imagen?v={Path(prueba['ruta']).stem}"
    if prueba["estado"] == "en_cola":
        # Cuántas pruebas se atienden antes que esta (de cualquier persona: la GPU es una sola).
        respuesta["delante"] = bd().pruebas_atuendo.count_documents(
            {"_id": {"$lt": prueba["id"]}, "estado": {"$in": ["en_cola", "procesando"]}})
    return respuesta


def pedir(usuario_id: int, prendas: list[dict]) -> dict:
    """Devuelve la prueba de estas prendas: la que ya existe o una nueva en la cola."""
    foto = foto_de(usuario_id)
    if not foto.get("foto_cuerpo"):
        raise HTTPException(409, "Primero sube tu foto")
    pasadas = pasadas_de(prendas)
    if not pasadas:
        raise HTTPException(422, "Este look no tiene prendas que se puedan vestir")
    clave = {"usuario_id": usuario_id, "firma": firma_de_pasadas(pasadas), "version_foto": foto["version_foto"]}
    prueba = leer_prueba(clave)
    if prueba is None:
        try:
            bd().pruebas_atuendo.insert_one({
                "_id": siguiente_id("pruebas_atuendo"), **clave, "estado": "en_cola", "paso": 0, "pasos": len(pasadas),
                "ruta": None, "segundos": None, "error": None, "fecha_creacion": ahora(), "fecha_uso": ahora(),
            })
        except DuplicateKeyError:
            pass  # otra petición igual la creó al mismo tiempo (índice único usuario_id + firma + version_foto)
        despertar.set()
    elif prueba["estado"] == "error":  # pedirla otra vez es reintentar
        marcar(prueba["id"], estado="en_cola", error=None, paso=0)
        despertar.set()
    else:
        marcar(prueba["id"], fecha_uso=ahora())
    return consultar_estado(usuario_id, leer_prueba(clave, projection={"_id": 1})["id"])


def buscar_prueba(usuario_id: int, prueba_id: int) -> dict:
    prueba = leer_prueba({"_id": prueba_id, "usuario_id": usuario_id})
    if prueba is None:
        raise HTTPException(404, "Prueba no encontrada")
    return prueba


def consultar_estado(usuario_id: int, prueba_id: int) -> dict:
    return estado_de(buscar_prueba(usuario_id, prueba_id))


def ruta_de_imagen(usuario_id: int, prueba_id: int) -> Path:
    prueba = buscar_prueba(usuario_id, prueba_id)
    if prueba["estado"] != "lista" or not prueba["ruta"] or not Path(prueba["ruta"]).is_file():
        raise HTTPException(404, "La imagen todavía no está lista")
    marcar(prueba_id, fecha_uso=ahora())
    return Path(prueba["ruta"])


# ------------------------------------------------
# 4. COLA
# ------------------------------------------------

def iniciar():
    """Lo que se quedó a medias al apagar el servidor vuelve a la cola, y arranca el hilo."""
    global hilo
    bd().pruebas_atuendo.update_many({"estado": "procesando"}, {"$set": {"estado": "en_cola", "paso": 0}})
    if hilo is None or not hilo.is_alive():
        hilo = threading.Thread(target=trabajar, name="probador", daemon=True)
        hilo.start()
    despertar.set()


def trabajar():
    while True:
        despertar.wait(timeout=60)
        despertar.clear()
        # La más vieja en cola primero (el _id es consecutivo); el índice cola_del_probador hace rápida la búsqueda.
        while (prueba := leer_prueba({"estado": "en_cola"}, sort=[("_id", 1)])):
            procesar(prueba)


def marcar(prueba_id: int, **campos):
    bd().pruebas_atuendo.update_one({"_id": prueba_id}, {"$set": campos})


def guardar_parcial(prueba: dict, pasadas: list[dict], ruta: Path):
    """El resultado de una pasada intermedia (p. ej. solo el pantalón) queda como prueba, para reutilizarla."""
    clave = {"usuario_id": prueba["usuario_id"], "firma": firma_de_pasadas(pasadas), "version_foto": prueba["version_foto"]}
    anterior = leer_prueba(clave)
    if anterior:
        borrar_archivo(anterior["ruta"])  # su archivo ya no existía o se reemplaza
        marcar(anterior["id"], estado="lista", ruta=str(ruta), paso=len(pasadas), error=None)
    else:
        bd().pruebas_atuendo.insert_one({
            "_id": siguiente_id("pruebas_atuendo"), **clave, "estado": "lista", "paso": len(pasadas),
            "pasos": len(pasadas), "ruta": str(ruta), "segundos": None, "error": None,
            "fecha_creacion": ahora(), "fecha_uso": ahora(),
        })


def procesar(prueba: dict):
    borrar_archivo(prueba["ruta"])  # si se reintenta, la imagen anterior se reemplaza
    marcar(prueba["id"], estado="procesando", paso=0, ruta=None)
    usuario_id = prueba["usuario_id"]
    inicio = time.time()
    try:
        foto = foto_de(usuario_id)
        if foto.get("version_foto") != prueba["version_foto"] or not foto.get("foto_cuerpo"):
            raise HTTPException(409, "Cambiaste tu foto: pide la prueba otra vez")
        prendas = [como_dict(bd().prendas.find_one({"_id": int(i), "usuario_id": usuario_id}))
                   for i in prueba["firma"].split("-")]
        if None in prendas:
            raise HTTPException(404, "Una de las prendas ya no está en tu armario")
        pasadas = pasadas_de(prendas)
        actual = foto["foto_cuerpo"]
        with gpu.turno:
            ollama.descargar_modelo()
            for numero in range(1, len(pasadas) + 1):
                hecha = leer_prueba({"usuario_id": usuario_id, "firma": firma_de_pasadas(pasadas[:numero]),
                                     "version_foto": prueba["version_foto"], "estado": "lista"})
                if hecha and hecha["ruta"] and Path(hecha["ruta"]).is_file():
                    actual = hecha["ruta"]  # esa pasada ya se hizo para otro look
                else:
                    salida = carpeta("pruebas", str(usuario_id)) / f"{uuid.uuid4().hex}.jpg"
                    prenda = base_datos.CARPETA_ARCHIVOS / pasadas[numero - 1]["url_imagen"].removeprefix("/archivos/")
                    gpu.pedir_al_motor("/vestir", {
                        "foto": str(actual), "prenda": str(prenda), "salida": str(salida),
                        "tipo": TIPO_DE_PASADA[pasadas[numero - 1]["categoria"]],
                    }, ESPERA_VESTIR)
                    actual = str(salida)
                    if numero < len(pasadas):
                        guardar_parcial(prueba, pasadas[:numero], salida)
                marcar(prueba["id"], paso=numero)
        if leer_prueba({"_id": prueba["id"]}) is None:
            return  # se borró la foto mientras se generaba
        marcar(prueba["id"], estado="lista", ruta=actual, segundos=round(time.time() - inicio, 1))
    except HTTPException as error:
        marcar(prueba["id"], estado="error", error=error.detail)
    except Exception as error:  # que un fallo inesperado no detenga la cola
        marcar(prueba["id"], estado="error", error=f"No se pudo generar la imagen ({type(error).__name__})")
    limpiar_viejas(usuario_id)
