"""Pruebas del probador virtual con un motor falso: no necesitan GPU ni el motor encendido.
Usan una base de datos y carpetas temporales (no tocan secrets_of_style.db).
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_probador.py"""
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

os.environ["CLAVE_SECRETA"] = "clave-de-prueba"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
temporal = Path(tempfile.mkdtemp())

from fastapi import HTTPException  # noqa: E402

from servidor import base_datos  # noqa: E402

base_datos.RUTA_BD = temporal / "prueba.db"
base_datos.CARPETA_ARCHIVOS = temporal / "archivos"
base_datos.CARPETA_PRIVADA = temporal / "privado"

from fastapi.testclient import TestClient  # noqa: E402

from servidor import gpu, ollama, principal, probador  # noqa: E402

ok = lambda cond, msg: print(("OK   " if cond else "FALLA"), msg)  # noqa: E731
JPG = b"\xff\xd8\xff\xe0" + b"0" * 100

# --- Motor falso: copia la foto como resultado y anota cada llamada ---
llamadas, activos, maximo = [], [0], [0]
candado = threading.Lock()
comportamiento = {"valida": True, "apagado": False, "falla_vestir": False}


def motor_falso(ruta, datos=None, espera=300):
    if comportamiento["apagado"]:
        raise HTTPException(503, gpu.AVISO_APAGADO)
    llamadas.append((ruta, datos))
    if ruta == "/validar":
        return {"valida": comportamiento["valida"], "motivo": None if comportamiento["valida"] else "No se ven tus piernas."}
    if ruta == "/vestir":
        with candado:
            activos[0] += 1
            maximo[0] = max(maximo[0], activos[0])
        time.sleep(0.05)
        with candado:
            activos[0] -= 1
        if comportamiento["falla_vestir"]:
            raise HTTPException(503, "La GPU se quedó sin memoria")
        Path(datos["salida"]).write_bytes(JPG + datos["tipo"].encode())
        return {"segundos": 0.05}
    return {}


gemma_descargada = []
gpu.pedir_al_motor = motor_falso
ollama.descargar_modelo = lambda: gemma_descargada.append(1)


def vestidas():
    return [d for r, d in llamadas if r == "/vestir"]


def esperar(cliente, h, prueba_id):
    for _ in range(200):
        estado = cliente.get(f"/api/atuendos/probador/{prueba_id}", headers=h).json()
        if estado["estado"] in ("lista", "error"):
            return estado
        time.sleep(0.02)
    return estado


# --- Lo que no necesita servidor ---
sup = {"id": 1, "categoria": "parte_superior"}
inf = {"id": 2, "categoria": "parte_inferior"}
abr = {"id": 3, "categoria": "abrigo"}
zap = {"id": 4, "categoria": "calzado"}
acc = {"id": 5, "categoria": "accesorio"}
ok([p["id"] for p in probador.pasadas_de([sup, zap, inf, acc])] == [2, 1], "pasadas: primero la parte inferior y luego la superior")
ok([p["id"] for p in probador.pasadas_de([sup, inf, abr])] == [2, 3], "con abrigo se viste el abrigo, no la parte superior")
ok(probador.pasadas_de([zap, acc]) == [], "calzado y accesorios no se visten")

with TestClient(principal.aplicacion) as cliente:  # "with" arranca el hilo de la cola
    def cuenta(correo):
        token = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "12345678"}).json()["token_acceso"]
        return {"Authorization": f"Bearer {token}"}

    def prenda(h, categoria):
        datos = {"categoria": categoria, "color_principal": "negro", "nivel_abrigo": "2", "impermeable": "false"}
        return cliente.post("/api/prendas", headers=h, data=datos, files={"imagen": ("p.jpg", JPG)}).json()["id"]

    h = cuenta("a@b.com")
    otro = cuenta("c@d.com")
    playera, playera2, pantalon, tenis, tenis2, chamarra, falda = (prenda(h, c) for c in (
        "parte_superior", "parte_superior", "parte_inferior", "calzado", "calzado", "abrigo", "parte_inferior"))

    # --- Foto ---
    perfil = cliente.get("/api/perfil", headers=h).json()
    ok(perfil["tiene_foto"] is False and "foto_cuerpo" not in perfil, "el perfil dice si hay foto sin mostrar la ruta")
    r = cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [playera, pantalon]})
    ok(r.status_code == 409, f"sin foto -> 409 {r.json()}")

    comportamiento["valida"] = False
    r = cliente.post("/api/perfil/foto", headers=h, files={"imagen": ("yo.jpg", JPG)})
    cuerpos = base_datos.CARPETA_PRIVADA / "cuerpos"
    ok(r.status_code == 422 and "piernas" in r.json()["detail"], f"foto que no sirve -> 422 con el motivo {r.json()}")
    ok(not any(cuerpos.iterdir()), "la foto rechazada no se queda en disco")
    comportamiento["valida"] = True

    comportamiento["apagado"] = True
    r = cliente.post("/api/perfil/foto", headers=h, files={"imagen": ("yo.jpg", JPG)})
    ok(r.status_code == 503 and "motor" in r.json()["detail"], "motor apagado -> 503 con aviso")
    ok(not any(cuerpos.iterdir()), "con el motor apagado tampoco queda la foto")
    comportamiento["apagado"] = False

    heic = b"\x00\x00\x00\x18ftypheic" + b"0" * 50
    ok(cliente.post("/api/perfil/foto", headers=h, files={"imagen": ("yo.heic", heic)}).status_code == 415, "HEIC -> 415")
    ok(cliente.post("/api/perfil/foto", files={"imagen": ("yo.jpg", JPG)}).status_code == 401, "subir foto sin sesión -> 401")

    r = cliente.post("/api/perfil/foto", headers=h, files={"imagen": ("yo.jpg", JPG)})
    ok(r.status_code == 200 and r.json()["tiene_foto"], "foto válida guardada")
    fotos = list(cuerpos.iterdir())
    ok(len(fotos) == 1 and not fotos[0].is_relative_to(base_datos.CARPETA_ARCHIVOS), "la foto queda en privado, fuera de /archivos")
    ok(cliente.get(f"/archivos/../privado/cuerpos/{fotos[0].name}").status_code == 404, "la foto no se alcanza por /archivos")
    r = cliente.get("/api/perfil/foto", headers=h)
    ok(r.status_code == 200 and r.content == JPG, "la persona puede ver su foto")
    ok(cliente.get("/api/perfil/foto").status_code == 401, "ver la foto sin sesión -> 401")
    ok(cliente.get("/api/perfil/foto", headers=otro).status_code == 404, "otra cuenta no ve la foto -> 404")

    # --- Un look ---
    ok(cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [tenis]}).status_code == 422,
       "look sin prendas que vestir -> 422")
    ok(cliente.post("/api/atuendos/probador", headers=otro, json={"prenda_ids": [playera]}).status_code == 404,
       "prenda de otra cuenta -> 404")
    r = cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [playera, pantalon, tenis]})
    prueba = r.json()
    ok(r.status_code == 200 and prueba["estado"] in ("en_cola", "procesando") and prueba["pasos"] == 2,
       f"el look entra a la cola con 2 pasadas {prueba}")
    ok(prueba["vestidas"] == sorted([playera, pantalon]), "los tenis no se visten")
    final = esperar(cliente, h, prueba["id"])
    ok(final["estado"] == "lista" and final["url"], f"la prueba termina {final}")
    ok([d["tipo"] for d in vestidas()] == ["lower", "upper"], "se viste primero el pantalón y luego la playera")
    ok(vestidas()[1]["foto"] == vestidas()[0]["salida"], "la segunda pasada parte del resultado de la primera")
    ok(len(gemma_descargada) >= 1, "antes de vestir se saca a Gemma de la GPU")
    r = cliente.get(final["url"], headers=h)
    ok(r.status_code == 200 and r.content.startswith(JPG), "la imagen se baja con sesión")
    ok(cliente.get(final["url"]).status_code == 401, "la imagen sin sesión -> 401")
    ok(cliente.get(final["url"], headers=otro).status_code == 404, "la imagen con otra cuenta -> 404")

    # --- Caché ---
    antes = len(vestidas())
    r = cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [playera, pantalon, tenis]}).json()
    ok(r["estado"] == "lista" and r["id"] == prueba["id"] and len(vestidas()) == antes, "pedir el mismo look no genera otra vez")
    r = cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [pantalon, playera, tenis2]}).json()
    ok(r["id"] == prueba["id"], "otro calzado da la misma imagen")
    r = cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [playera2, pantalon]}).json()
    final2 = esperar(cliente, h, r["id"])
    ok(final2["estado"] == "lista" and len(vestidas()) == antes + 1, "otro look con el mismo pantalón reutiliza esa pasada")
    r = cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [playera, pantalon, chamarra]}).json()
    ok(esperar(cliente, h, r["id"])["estado"] == "lista" and vestidas()[-1]["tipo"] == "upper"
       and str(chamarra) in r["vestidas"].__str__(), "con chamarra se viste la chamarra encima del pantalón")

    # --- Una a la vez ---
    ids = [cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [p]}).json()["id"]
           for p in (playera, playera2, chamarra, pantalon)]
    ok(all(esperar(cliente, h, i)["estado"] == "lista" for i in ids) and maximo[0] == 1, "la cola viste un look a la vez")

    # --- Turno de la GPU ---
    ollama.ESPERA_TURNO = 0.1
    with gpu.turno:
        try:
            ollama.preguntar("hola", "aviso")
            ok(False, "Gemma debió esperar su turno")
        except HTTPException as e:
            ok(e.status_code == 503 and e.detail == ollama.AVISO_OCUPADA, "si el probador tiene la GPU, Gemma avisa que está ocupada")
    ok(not gpu.turno.locked(), "el turno se libera")

    # --- Errores ---
    comportamiento["falla_vestir"] = True
    r = cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [playera2, falda]}).json()
    fallida = esperar(cliente, h, r["id"])
    ok(fallida["estado"] == "error" and "memoria" in fallida["error"], f"si el motor falla queda el error {fallida['error']}")
    ok(not gpu.turno.locked(), "un error libera el turno de la GPU")
    comportamiento["falla_vestir"] = False
    r = cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [playera2, falda]}).json()
    ok(r["id"] == fallida["id"] and esperar(cliente, h, r["id"])["estado"] == "lista", "pedirla otra vez la reintenta")

    # --- Lo que se quedó a medias al apagar ---
    url_vieja = esperar(cliente, h, prueba["id"])["url"]
    base_datos.ejecutar("UPDATE pruebas_atuendo SET estado = 'procesando' WHERE id = ?", (prueba["id"],))
    probador.iniciar()
    retomada = esperar(cliente, h, prueba["id"])
    ok(retomada["estado"] == "lista", "al arrancar se retoma lo que quedó procesando")
    ok(retomada["url"] != url_vieja, "la imagen nueva tiene otra URL, para que el teléfono no muestre la de su caché")

    # --- Borrar una prenda borra sus pruebas ---
    rutas_playera2 = [f["ruta"] for f in base_datos.consultar("SELECT ruta, firma FROM pruebas_atuendo")
                      if str(playera2) in f["firma"].split("-")]
    ok(cliente.delete(f"/api/prendas/{playera2}", headers=h).status_code == 204, "se borra una prenda")
    quedan = [f for f in base_datos.consultar("SELECT firma FROM pruebas_atuendo") if str(playera2) in f["firma"].split("-")]
    ok(not quedan and not any(Path(r).exists() for r in rutas_playera2 if r), "sus pruebas y archivos se borran")

    # --- Límite por persona ---
    probador.MAXIMO_PRUEBAS = 2
    r = cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [playera, falda]}).json()
    esperar(cliente, h, r["id"])
    # El hilo borra las viejas justo después de marcar "lista": se le da un momento para terminar.
    for _ in range(50):
        total = base_datos.consultar_uno("SELECT COUNT(*) AS n FROM pruebas_atuendo WHERE usuario_id = 1")["n"]
        if total <= 2:
            break
        time.sleep(0.1)
    archivos = list((base_datos.CARPETA_PRIVADA / "pruebas" / "1").iterdir())
    ok(total == 2 and len(archivos) == 2, f"se conservan solo las más recientes ({total} filas, {len(archivos)} archivos)")
    probador.MAXIMO_PRUEBAS = 40

    # --- Cambiar o borrar la foto ---
    viejas = base_datos.consultar("SELECT id, ruta FROM pruebas_atuendo WHERE usuario_id = 1")
    cliente.post("/api/perfil/foto", headers=h, files={"imagen": ("yo2.jpg", JPG)})
    ok(len(list(cuerpos.iterdir())) == 1, "la foto nueva reemplaza a la anterior")
    ok(not base_datos.consultar("SELECT id FROM pruebas_atuendo WHERE usuario_id = 1")
       and not any(Path(f["ruta"]).exists() for f in viejas if f["ruta"]), "cambiar de foto borra lo generado con la anterior")
    antes = len(vestidas())
    r = cliente.post("/api/atuendos/probador", headers=h, json={"prenda_ids": [playera, pantalon]}).json()
    ok(esperar(cliente, h, r["id"])["estado"] == "lista" and len(vestidas()) == antes + 2, "con la foto nueva se genera de nuevo")
    r = cliente.delete("/api/perfil/foto", headers=h)
    ok(r.status_code == 200 and r.json()["tiene_foto"] is False, "borrar la foto")
    ok(cliente.get("/api/perfil/foto", headers=h).status_code == 404, "sin foto, ver la foto -> 404")
    ok(not any(cuerpos.iterdir()) and not (base_datos.CARPETA_PRIVADA / "pruebas" / "1").exists()
       and not base_datos.consultar("SELECT id FROM pruebas_atuendo WHERE usuario_id = 1"), "no queda nada de la persona en privado")
