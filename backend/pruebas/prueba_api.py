"""Pruebas de la API con una base de datos y una carpeta temporales (no toca secrets_of_style.db).
Ejecutar desde la carpeta backend: .venv\Scripts\python pruebas\prueba_api.py"""
import os
import sys
import tempfile
import time
import urllib.error
from pathlib import Path

os.environ["CLAVE_SECRETA"] = "clave-de-prueba"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
temporal = Path(tempfile.mkdtemp())

from servidor import base_datos  # noqa: E402

base_datos.RUTA_BD = temporal / "prueba.db"
base_datos.CARPETA_ARCHIVOS = temporal / "archivos"

# Simula una base vieja: usuarios sin la columna version_sesion.
import sqlite3  # noqa: E402
c = sqlite3.connect(base_datos.RUTA_BD)
c.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, correo TEXT UNIQUE NOT NULL, "
          "contraseña_hash TEXT NOT NULL, fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP)")
c.commit(); c.close()

from fastapi.testclient import TestClient  # noqa: E402
from servidor import clima, principal  # noqa: E402

cliente = TestClient(principal.aplicacion)
ok = lambda cond, msg: print(("OK   " if cond else "FALLA"), msg)

# --- Migración ---
cols = {r[1] for r in sqlite3.connect(base_datos.RUTA_BD).execute("PRAGMA table_info(usuarios)")}
ok("version_sesion" in cols, "migración agrega version_sesion")

# --- Sesiones ---
r = cliente.post("/api/auth/registro", json={"correo": "a@b.com", "contraseña": "12345678"})
token = r.json()["token_acceso"]
h = {"Authorization": f"Bearer {token}"}
ok(r.status_code == 201 and token.count(".") == 3, "registro devuelve token de 4 partes")
r = cliente.get("/api/auth/yo", headers=h)
ok(r.status_code == 200 and "version_sesion" not in r.json(), f"token válido y /yo no expone versión {r.json()}")
token_login = cliente.post("/api/auth/login", json={"correo": "a@b.com", "contraseña": "12345678"}).json()["token_acceso"]
ok(cliente.get("/api/auth/yo", headers={"Authorization": f"Bearer {token_login}"}).status_code == 200, "login funciona")
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

# --- Clima ---
def falla(*a, **k):
    raise urllib.error.URLError("sin red")

real = clima.urllib.request.urlopen
clima.urllib.request.urlopen = falla
r = cliente.get("/api/clima?latitud=19.43&longitud=-99.13", headers=h)
ok(r.status_code == 502, "sin red y sin clima guardado -> 502")
reporte = {"temperatura_c": 20, "sensacion_termica_c": 19, "probabilidad_lluvia": 10, "descripcion": "Nublado",
           "hechos": [], "deducciones": []}
import json  # noqa: E402
base_datos.ejecutar("INSERT INTO climas VALUES (?, ?, ?)", ("19.43,-99.13", time.time() - 3 * 3600, json.dumps(reporte)))
r = cliente.get("/api/clima?latitud=19.43&longitud=-99.13", headers=h)
ok(r.status_code == 200 and r.json().get("minutos_desactualizado") == 180, f"sin red usa el guardado {r.json()}")
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
r = cliente.get("/api/clima?latitud=19.43&longitud=-99.13", headers=h)
ok(r.status_code == 200 and "minutos_desactualizado" not in r.json(), f"con red consulta de nuevo ({r.status_code}) {r.json().get('descripcion')}")
fila = base_datos.consultar_uno("SELECT consultado FROM climas WHERE clave = '19.43,-99.13'")
ok(time.time() - fila["consultado"] < 60, "clima nuevo queda guardado")
