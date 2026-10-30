"""Comprueba la detección de prendas: limpieza de la respuesta, esquema, ruta de la API y, si Ollama
está abierto, una foto de verdad.
Ejecutar desde la carpeta backend: .venv\Scripts\python pruebas\prueba_vision.py"""
import os
import struct
import sys
import tempfile
import urllib.request
import zlib
from pathlib import Path

os.environ["CLAVE_SECRETA"] = "clave-de-prueba"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
temporal = Path(tempfile.mkdtemp())

from servidor import base_datos  # noqa: E402

base_datos.RUTA_BD = temporal / "prueba.db"
base_datos.CARPETA_ARCHIVOS = temporal / "archivos"

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from servidor import logica, ollama, principal, vision  # noqa: E402

fallas = 0


def ok(cond, msg):
    global fallas
    fallas += not cond
    print(("OK   " if cond else "FALLA"), msg)


def png_de_color(rojo, verde, azul, lado=64):
    """Un PNG de un solo color, armado a mano para no depender de Pillow."""
    def bloque(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))
    fila = b"\x00" + bytes([rojo, verde, azul]) * lado
    return (b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", lado, lado, 8, 2, 0, 0, 0))
            + bloque(b"IDAT", zlib.compress(fila * lado)) + bloque(b"IEND", b""))


# --- 1. Limpieza de la respuesta ---
valida = {"categoria": "calzado", "subcategoria": "botines", "color_principal": "cafe", "estampado": "liso",
          "estilo": "casual", "nivel_abrigo": 4, "impermeable": False}
ok(vision.limpiar_respuesta(valida) == {**valida, "subcategoria": "Botines"}, "respuesta válida pasa (con mayúscula inicial)")
r = vision.limpiar_respuesta({"categoria": "vestido", "color_principal": "turquesa", "estampado": "cachemir",
                              "estilo": "punk", "nivel_abrigo": 7, "subcategoria": "x" * 80})
ok(r["categoria"] is None and r["color_principal"] is None, "categoría y color fuera del catálogo: None")
ok(r["estampado"] is None and r["estilo"] is None, "estampado y estilo fuera del catálogo: None")
ok(r["nivel_abrigo"] == 5 and len(r["subcategoria"]) == 60, f"abrigo limitado a 5 y tipo a 60 letras ({r['nivel_abrigo']})")
r = vision.limpiar_respuesta({"nivel_abrigo": True, "impermeable": "sí", "subcategoria": "  "})
ok(r["nivel_abrigo"] is None and r["impermeable"] is False and r["subcategoria"] is None, "valores de otro tipo: None o False")

# --- 2. El esquema usa los mismos catálogos que la API ---
propiedades = vision.ESQUEMA["properties"]
ok(propiedades["categoria"]["enum"] == principal.CATEGORIAS, "categorías del esquema = principal.CATEGORIAS")
ok(set(propiedades["color_principal"]["enum"]) == principal.COLORES, "colores del esquema = principal.COLORES")
ok(propiedades["estampado"]["enum"] == logica.ESTAMPADOS and propiedades["estilo"]["enum"] == logica.ESTILOS,
   "estampados y estilos del esquema = los de la lógica")
ok(all(c in vision.INSTRUCCIONES for c in principal.CATEGORIAS + logica.ESTAMPADOS + logica.ESTILOS),
   "las instrucciones explican todas las categorías, estampados y estilos")

# --- 3. API (con un detector falso) ---
cliente = TestClient(principal.aplicacion)
token = cliente.post("/api/auth/registro", json={"correo": "a@b.com", "contraseña": "12345678"}).json()["token_acceso"]
h = {"Authorization": f"Bearer {token}"}
foto = {"imagen": ("prenda.png", png_de_color(220, 30, 30), "image/png")}

principal.detectar_prenda = lambda contenido: vision.limpiar_respuesta(valida)
r = cliente.post("/api/prendas/analizar", headers=h, files=foto)
ok(r.status_code == 200 and r.json()["categoria"] == "calzado", f"/api/prendas/analizar ({r.status_code})")
r = cliente.post("/api/prendas/analizar", headers=h, files={"imagen": ("x.jpg", b"no soy una imagen", "image/jpeg")})
ok(r.status_code == 415, f"archivo que no es imagen: 415 ({r.status_code})")
r = cliente.post("/api/prendas/analizar", files=foto)
ok(r.status_code == 401, f"sin sesión: 401 ({r.status_code})")
ok(cliente.get("/api/prendas", headers=h).json() == [], "analizar no guarda la prenda")


def sin_ollama(contenido):
    raise HTTPException(503, "La detección automática no está disponible; llena los datos a mano")


principal.detectar_prenda = sin_ollama
r = cliente.post("/api/prendas/analizar", headers=h, files=foto)
ok(r.status_code == 503 and "a mano" in r.json()["detail"], f"Ollama cerrado: 503 ({r.status_code})")

# --- 4. Ollama de verdad (se salta si no está abierto) ---
try:
    urllib.request.urlopen(f"{ollama.URL_OLLAMA}/api/version", timeout=2)
except OSError:
    print("SALTA Ollama no está abierto: no se prueba el modelo real")
else:
    try:
        r = vision.detectar_prenda(png_de_color(220, 30, 30))
        ok(r["color_principal"] == "rojo" and r["categoria"] in principal.CATEGORIAS, f"modelo real con una imagen roja {r}")
    except HTTPException as e:
        ok(False, f"modelo real: {e.detail} (¿falta ollama pull {ollama.MODELO}?)")

print("\nFALLAS:", fallas)
