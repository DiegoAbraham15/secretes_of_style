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

from servidor import base_datos, gpu, ollama
from servidor.aprendizaje import firma_de
from servidor.base_datos import consultar, consultar_uno, ejecutar

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


def borrar_pruebas(filas: list[dict]):
    for fila in filas:
        borrar_archivo(fila["ruta"])
        ejecutar("DELETE FROM pruebas_atuendo WHERE id = ?", (fila["id"],))


def foto_de(usuario_id: int) -> dict:
    return consultar_uno("SELECT foto_cuerpo, version_foto FROM perfiles WHERE usuario_id = ?", (usuario_id,)) or {}


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
    ejecutar("UPDATE perfiles SET foto_cuerpo = ? WHERE usuario_id = ?", (str(definitiva), usuario_id))


def borrar_foto(usuario_id: int):
    """Borra la foto y todas las pruebas. Subir la versión invalida lo que el hilo esté generando."""
    borrar_archivo(foto_de(usuario_id).get("foto_cuerpo"))
    borrar_pruebas(consultar("SELECT id, ruta FROM pruebas_atuendo WHERE usuario_id = ?", (usuario_id,)))
    shutil.rmtree(base_datos.CARPETA_PRIVADA / "pruebas" / str(usuario_id), ignore_errors=True)
    ejecutar("UPDATE perfiles SET foto_cuerpo = NULL, version_foto = version_foto + 1 WHERE usuario_id = ?", (usuario_id,))


def olvidar_prenda(usuario_id: int, prenda_id: int):
    """Al borrar una prenda se borran las pruebas donde aparece."""
    filas = consultar("SELECT id, ruta, firma FROM pruebas_atuendo WHERE usuario_id = ?", (usuario_id,))
    borrar_pruebas([f for f in filas if str(prenda_id) in f["firma"].split("-")])


def limpiar_viejas(usuario_id: int):
    filas = consultar(
        "SELECT id, ruta FROM pruebas_atuendo WHERE usuario_id = ? AND estado IN ('lista', 'error') "
        "ORDER BY fecha_uso DESC, id DESC LIMIT -1 OFFSET ?",
        (usuario_id, MAXIMO_PRUEBAS),
    )
    borrar_pruebas(filas)


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
        respuesta["delante"] = consultar_uno(
            "SELECT COUNT(*) AS n FROM pruebas_atuendo WHERE id < ? AND estado IN ('en_cola', 'procesando')",
            (prueba["id"],),
        )["n"]
    return respuesta


def pedir(usuario_id: int, prendas: list[dict]) -> dict:
    """Devuelve la prueba de estas prendas: la que ya existe o una nueva en la cola."""
    foto = foto_de(usuario_id)
    if not foto.get("foto_cuerpo"):
        raise HTTPException(409, "Primero sube tu foto")
    pasadas = pasadas_de(prendas)
    if not pasadas:
        raise HTTPException(422, "Este look no tiene prendas que se puedan vestir")
    firma = firma_de_pasadas(pasadas)
    clave = (usuario_id, firma, foto["version_foto"])
    prueba = consultar_uno("SELECT * FROM pruebas_atuendo WHERE usuario_id = ? AND firma = ? AND version_foto = ?", clave)
    if prueba is None:
        ejecutar("INSERT INTO pruebas_atuendo (usuario_id, firma, version_foto, pasos) VALUES (?, ?, ?, ?)",
                 (*clave, len(pasadas)))
        despertar.set()
    elif prueba["estado"] == "error":  # pedirla otra vez es reintentar
        ejecutar("UPDATE pruebas_atuendo SET estado = 'en_cola', error = NULL, paso = 0 WHERE id = ?", (prueba["id"],))
        despertar.set()
    else:
        ejecutar("UPDATE pruebas_atuendo SET fecha_uso = CURRENT_TIMESTAMP WHERE id = ?", (prueba["id"],))
    return consultar_estado(usuario_id, consultar_uno(
        "SELECT id FROM pruebas_atuendo WHERE usuario_id = ? AND firma = ? AND version_foto = ?", clave)["id"])


def buscar_prueba(usuario_id: int, prueba_id: int) -> dict:
    prueba = consultar_uno("SELECT * FROM pruebas_atuendo WHERE id = ? AND usuario_id = ?", (prueba_id, usuario_id))
    if prueba is None:
        raise HTTPException(404, "Prueba no encontrada")
    return prueba


def consultar_estado(usuario_id: int, prueba_id: int) -> dict:
    return estado_de(buscar_prueba(usuario_id, prueba_id))


def ruta_de_imagen(usuario_id: int, prueba_id: int) -> Path:
    prueba = buscar_prueba(usuario_id, prueba_id)
    if prueba["estado"] != "lista" or not prueba["ruta"] or not Path(prueba["ruta"]).is_file():
        raise HTTPException(404, "La imagen todavía no está lista")
    ejecutar("UPDATE pruebas_atuendo SET fecha_uso = CURRENT_TIMESTAMP WHERE id = ?", (prueba_id,))
    return Path(prueba["ruta"])


# ------------------------------------------------
# 4. COLA
# ------------------------------------------------

def iniciar():
    """Lo que se quedó a medias al apagar el servidor vuelve a la cola, y arranca el hilo."""
    global hilo
    ejecutar("UPDATE pruebas_atuendo SET estado = 'en_cola', paso = 0 WHERE estado = 'procesando'")
    if hilo is None or not hilo.is_alive():
        hilo = threading.Thread(target=trabajar, name="probador", daemon=True)
        hilo.start()
    despertar.set()


def trabajar():
    while True:
        despertar.wait(timeout=60)
        despertar.clear()
        while (prueba := consultar_uno("SELECT * FROM pruebas_atuendo WHERE estado = 'en_cola' ORDER BY id LIMIT 1")):
            procesar(prueba)


def marcar(prueba_id: int, **campos):
    asignaciones = ", ".join(f"{columna} = ?" for columna in campos)
    ejecutar(f"UPDATE pruebas_atuendo SET {asignaciones} WHERE id = ?", (*campos.values(), prueba_id))


def guardar_parcial(prueba: dict, pasadas: list[dict], ruta: Path):
    """El resultado de una pasada intermedia (p. ej. solo el pantalón) queda como prueba, para reutilizarla."""
    anterior = consultar_uno("SELECT ruta FROM pruebas_atuendo WHERE usuario_id = ? AND firma = ? AND version_foto = ?",
                             (prueba["usuario_id"], firma_de_pasadas(pasadas), prueba["version_foto"]))
    if anterior:
        borrar_archivo(anterior["ruta"])  # su archivo ya no existía o se reemplaza
    ejecutar(
        "INSERT INTO pruebas_atuendo (usuario_id, firma, version_foto, estado, paso, pasos, ruta) "
        "VALUES (?, ?, ?, 'lista', ?, ?, ?) ON CONFLICT (usuario_id, firma, version_foto) "
        "DO UPDATE SET estado = 'lista', ruta = excluded.ruta, paso = excluded.paso, error = NULL",
        (prueba["usuario_id"], firma_de_pasadas(pasadas), prueba["version_foto"], len(pasadas), len(pasadas), str(ruta)),
    )


def procesar(prueba: dict):
    borrar_archivo(prueba["ruta"])  # si se reintenta, la imagen anterior se reemplaza
    marcar(prueba["id"], estado="procesando", paso=0, ruta=None)
    usuario_id = prueba["usuario_id"]
    inicio = time.time()
    try:
        foto = foto_de(usuario_id)
        if foto.get("version_foto") != prueba["version_foto"] or not foto.get("foto_cuerpo"):
            raise HTTPException(409, "Cambiaste tu foto: pide la prueba otra vez")
        prendas = [consultar_uno("SELECT * FROM prendas WHERE id = ? AND usuario_id = ?", (int(i), usuario_id))
                   for i in prueba["firma"].split("-")]
        if None in prendas:
            raise HTTPException(404, "Una de las prendas ya no está en tu armario")
        pasadas = pasadas_de(prendas)
        actual = foto["foto_cuerpo"]
        with gpu.turno:
            ollama.descargar_modelo()
            for numero in range(1, len(pasadas) + 1):
                hecha = consultar_uno(
                    "SELECT ruta FROM pruebas_atuendo WHERE usuario_id = ? AND firma = ? AND version_foto = ? "
                    "AND estado = 'lista'", (usuario_id, firma_de_pasadas(pasadas[:numero]), prueba["version_foto"]))
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
        if consultar_uno("SELECT id FROM pruebas_atuendo WHERE id = ?", (prueba["id"],)) is None:
            return  # se borró la foto mientras se generaba
        marcar(prueba["id"], estado="lista", ruta=actual, segundos=round(time.time() - inicio, 1))
    except HTTPException as error:
        marcar(prueba["id"], estado="error", error=error.detail)
    except Exception as error:  # que un fallo inesperado no detenga la cola
        marcar(prueba["id"], estado="error", error=f"No se pudo generar la imagen ({type(error).__name__})")
    limpiar_viejas(usuario_id)
