"""Pruebas de la API con una base de MongoDB y una carpeta temporales (no tocan la base secrets_of_style).
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_api.py"""
import json
import os
import sys
import time
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pymongo.errors import WriteError  # noqa: E402
from servidor import base_datos, clima, principal  # noqa: E402

cliente = TestClient(principal.aplicacion)
bd = base_datos.bd()

# --- Colecciones, validación e índices ---
colecciones = {c["name"]: c["options"] for c in bd.command("listCollections")["cursor"]["firstBatch"]}
ok({"usuarios", "prendas", "atuendos", "votos_atuendo", "pruebas_atuendo", "climas", "contadores"} <= set(colecciones),
   "se crean las siete colecciones")
ok(all("$jsonSchema" in o.get("validator", {}) for o in colecciones.values()), "todas tienen validación $jsonSchema")
ok(bd.usuarios.index_information()["correo_unico"].get("unique"), "el correo tiene índice único")
ok(bd.votos_atuendo.index_information()["un_voto_por_atuendo"].get("unique"), "un voto por atuendo (índice único compuesto)")
principal.crear_colecciones()
ok(True, "crear las colecciones otra vez no falla (actualiza la validación)")
try:
    bd.prendas.insert_one({"_id": 999, "usuario_id": 1, "categoria": "sombrero", "nivel_abrigo": 9})
    rechazada = False
except WriteError:
    rechazada = True
ok(rechazada, "MongoDB rechaza una prenda que no cumple el esquema")

# --- Sesiones ---
r = cliente.post("/api/auth/registro", json={"correo": "a@b.com", "contraseña": "12345678"})
token = r.json()["token_acceso"]
h = {"Authorization": f"Bearer {token}"}
ok(r.status_code == 201 and token.count(".") == 3, "registro devuelve token de 4 partes")
r = cliente.get("/api/auth/yo", headers=h)
ok(r.status_code == 200 and "version_sesion" not in r.json(), f"token válido y /yo no expone versión {r.json()}")
token_login = cliente.post("/api/auth/login", json={"correo": "a@b.com", "contraseña": "12345678"}).json()["token_acceso"]
ok(cliente.get("/api/auth/yo", headers={"Authorization": f"Bearer {token_login}"}).status_code == 200, "login funciona")
ok(cliente.post("/api/auth/registro", json={"correo": "A@b.com ", "contraseña": "12345678"}).status_code == 409,
   "correo repetido (con mayúsculas o espacios) -> 409")
ok(cliente.post("/api/auth/login", json={"correo": {"$ne": ""}, "contraseña": {"$ne": ""}}).status_code == 422,
   "inyección NoSQL con operadores en el login -> 422")
ok(cliente.get("/api/prendas?categoria[$ne]=x", headers={"Authorization": f"Bearer {token_login}"}).json() == [],
   "un filtro con [$ne] se toma como texto, no como operador")
guardado = bd.usuarios.find_one({"correo": "a@b.com"})
ok(guardado["_id"] == 1 and guardado["perfil"]["version_foto"] == 0 and "contraseña" not in guardado,
   "el usuario se guarda con _id consecutivo, perfil embebido y solo el hash")
partes = token.split(".")
falso = ".".join([partes[0], partes[1], str(int(partes[2]) + 999), partes[3]])
ok(cliente.get("/api/auth/yo", headers={"Authorization": f"Bearer {falso}"}).status_code == 401, "token alterado -> 401")
ok(cliente.get("/api/auth/yo", headers={"Authorization": "Bearer 1.123.abc"}).status_code == 401, "token formato viejo -> 401")
ok(cliente.get("/api/auth/yo").status_code == 401, "sin token -> 401")
ok(cliente.post("/api/auth/cerrar-sesion", headers=h).status_code == 204, "cerrar sesión -> 204")
ok(cliente.get("/api/auth/yo", headers=h).status_code == 401, "token anterior ya no sirve")
ok(cliente.get("/api/auth/yo", headers={"Authorization": f"Bearer {token_login}"}).status_code == 401, "otro token anterior tampoco")
token2 = cliente.post("/api/auth/login", json={"correo": "a@b.com", "contraseña": "12345678"}).json()["token_acceso"]
h = {"Authorization": f"Bearer {token2}"}
ok(cliente.get("/api/auth/yo", headers=h).status_code == 200, "nuevo login funciona tras cerrar sesión")

# --- Imágenes ---
datos = {"categoria": "parte_superior", "color_principal": "negro", "nivel_abrigo": "2", "impermeable": "false"}
jpg = b"\xff\xd8\xff\xe0" + b"0" * 100
r = cliente.post("/api/prendas", headers=h, data=datos, files={"imagen": ("foto.png", jpg)})
ok(r.status_code == 201 and r.json()["url_imagen"].endswith(".jpg"), f"JPG con nombre .png se guarda como .jpg ({r.status_code})")
r = cliente.post("/api/prendas", headers=h, data=datos, files={"imagen": ("virus.jpg", b"<script>alert(1)</script>")})
ok(r.status_code == 415, f"archivo que no es imagen -> 415 ({r.status_code}) {r.json()}")
heic = b"\x00\x00\x00\x18ftypheic" + b"0" * 50
r = cliente.post("/api/prendas", headers=h, data=datos, files={"imagen": ("a.heic", heic)})
ok(r.status_code == 201 and r.json()["url_imagen"].endswith(".heic"), "HEIC aceptado")
webp = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"0" * 50
r = cliente.post("/api/prendas", headers=h, data=datos, files={"imagen": ("a.webp", webp)})
ok(r.status_code == 201 and r.json()["url_imagen"].endswith(".webp"), "WEBP aceptado")
grande = b"\xff\xd8\xff" + b"0" * (8 * 1024 * 1024)
r = cliente.post("/api/prendas", headers=h, data=datos, files={"imagen": ("g.jpg", grande)})
ok(r.status_code == 413, f"imagen de más de 8 MB -> 413 ({r.status_code})")

# --- CORS ---
for origen, debe in [("http://localhost:8081", True), ("http://192.168.1.50:8081", True),
                     ("http://172.20.0.3:8081", True), ("https://sitio-malo.com", False),
                     ("http://192.168.1.50.malo.com", False)]:
    r = cliente.options("/api/prendas", headers={"Origin": origen, "Access-Control-Request-Method": "GET"})
    permitido = r.headers.get("access-control-allow-origin") == origen
    ok(permitido == debe, f"CORS {origen} -> {'permitido' if permitido else 'bloqueado'}")

# --- Perfil: solo lo que usa la app (la foto del probador) ---
ok(set(cliente.get("/api/perfil", headers=h).json()) == {"usuario_id", "version_foto", "tiene_foto"},
   "el perfil trae la versión de la foto y si hay foto")
ok(cliente.put("/api/perfil", headers=h, json={"altura_cm": 170}).status_code == 405, "ya no se edita altura ni peso")
ok(cliente.post("/api/perfil/rostro", headers=h).status_code == 404, "ya no existe la foto del rostro")
ok(cliente.get("/api/clima?latitud=19.43&longitud=-99.13", headers=h).status_code == 404,
   "el clima ya no es una ruta aparte: llega dentro de /api/recomendaciones")


# --- Clima (clima.py, lo usa POST /api/recomendaciones) ---
def falla(*a, **k):
    raise urllib.error.URLError("sin red")


def consultar_clima():
    """(200, reporte) o (código de error, None), como lo vería la ruta de recomendaciones."""
    try:
        return 200, clima.obtener_clima(19.43, -99.13)
    except HTTPException as error:
        return error.status_code, None


clima.urllib.request.urlopen = falla
estado, _ = consultar_clima()
ok(estado == 502, "sin red y sin clima guardado -> 502")
reporte = {"temperatura_c": 20, "sensacion_termica_c": 19, "probabilidad_lluvia": 10, "descripcion": "Nublado",
           "hechos": [], "deducciones": []}
bd.climas.insert_one({"_id": "19.43,-99.13", "consultado": time.time() - 3 * 3600, "reporte": reporte})
estado, guardado = consultar_clima()
ok(estado == 200 and guardado.get("minutos_desactualizado") == 180, f"sin red usa el guardado {guardado}")
class RespuestaFija:
    """Imita la respuesta de Open-Meteo para que la prueba no dependa de internet."""
    def __init__(self, *args, **kwargs):
        self.cuerpo = json.dumps({
            'current': {'temperature_2m': 20, 'apparent_temperature': 19, 'weather_code': 3},
            'hourly': {'precipitation_probability': [10, 5, 0, 0, 0, 0]},
        }).encode('utf-8')

    def read(self):
        return self.cuerpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


clima.urllib.request.urlopen = RespuestaFija
estado, nuevo = consultar_clima()
ok(estado == 200 and "minutos_desactualizado" not in nuevo, f"con red consulta de nuevo ({estado}) {nuevo.get('descripcion')}")
fila = bd.climas.find_one({"_id": "19.43,-99.13"})
ok(time.time() - fila["consultado"] < 60, "clima nuevo queda guardado")

terminar()
