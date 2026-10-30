"""Comprueba el estampado, el estilo y la ocasión (lógica, búsqueda y API) y la explicación con IA.
Ejecutar desde la carpeta backend: .venv\Scripts\python pruebas\prueba_estilo.py"""
import os
import sqlite3
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

# Simula una base vieja: prendas sin las columnas estampado y estilo.
c = sqlite3.connect(base_datos.RUTA_BD)
c.execute("CREATE TABLE prendas (id INTEGER PRIMARY KEY, usuario_id INTEGER NOT NULL, url_imagen TEXT NOT NULL, "
          "categoria TEXT NOT NULL, subcategoria TEXT, color_principal TEXT NOT NULL, nivel_abrigo INTEGER NOT NULL, "
          "impermeable INTEGER DEFAULT 0, estado TEXT DEFAULT 'disponible', fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP)")
c.commit(); c.close()

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from servidor import busqueda, explicacion, ollama, principal  # noqa: E402
from servidor.logica import es_apta, hechos_de_ocasion, razonar_clima, se_recargan, ventajas_del_atuendo  # noqa: E402

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


def prenda(id, categoria, color, estampado="liso", estilo="casual", abrigo=2):
    return {"id": id, "categoria": categoria, "color_principal": color, "nivel_abrigo": abrigo, "impermeable": False,
            "estado": "disponible", "subcategoria": None, "estampado": estampado, "estilo": estilo}


# --- 1. Migración ---
cols = {r[1] for r in sqlite3.connect(base_datos.RUTA_BD).execute("PRAGMA table_info(prendas)")}
ok({"estampado", "estilo"} <= cols, "migración agrega estampado y estilo a prendas")

# --- 2. Reglas de la lógica ---
formal, deporte = razonar_clima(hechos_de_ocasion("formal"))[0], razonar_clima(hechos_de_ocasion("deporte"))[0]
ok(hechos_de_ocasion("diario") == set() and "ocasion_formal" in formal, "hechos de la ocasión")
ok(not es_apta(prenda(1, "calzado", "blanco", estilo="deportivo"), formal), "deportiva en ocasión formal: no apta")
ok(not es_apta(prenda(1, "parte_superior", "blanco", estilo="formal"), deporte), "formal para deporte: no apta")
ok(not es_apta(prenda(1, "parte_superior", "blanco"), formal), "casual en ocasión formal: no apta")
ok(es_apta(prenda(1, "parte_superior", "blanco"), set()), "casual en el día a día: apta")
ok(not es_apta(prenda(1, "accesorio", "negro"), formal), "accesorio casual en ocasión formal: no apto")
ok(es_apta(prenda(1, "accesorio", "negro", estilo="semiformal"), formal), "accesorio semiformal en ocasión formal: apto")
ok(es_apta(prenda(1, "accesorio", "negro", abrigo=1), razonar_clima({"frio"})[0]), "los accesorios no dependen del clima")
ok(es_apta(prenda(1, "parte_superior", "blanco", estilo="semiformal"), formal), "semiformal en ocasión formal: apta")
ok(not es_apta(prenda(1, "parte_superior", "blanco", estilo="semiformal"), deporte), "semiformal para deporte: no apta")
ok(not es_apta(prenda(1, "parte_superior", "blanco", estilo="urbano"), formal), "urbano en ocasión formal: no apta")
ok(es_apta(prenda(1, "parte_superior", "blanco", estilo="urbano"), deporte), "urbano para deporte: apta")
ok(es_apta(prenda(1, "parte_superior", "blanco", estilo="urbano"), set()), "urbano en el día a día: apta")

rayas, floral, lisa = prenda(1, "parte_superior", "blanco", "rayas"), prenda(2, "parte_inferior", "negro", "floral"), \
    prenda(3, "calzado", "negro")
ok(se_recargan(rayas, floral) and not se_recargan(rayas, lisa), "dos estampados se recargan; con una lisa, no")
ok(not se_recargan({"categoria": "calzado"}, {"categoria": "calzado"}), "prendas sin estampado guardado cuentan como lisas")
ok("Un solo estampado y lo demás liso: atuendo equilibrado" in ventajas_del_atuendo([rayas, lisa], set()),
   "ventaja con un solo estampado")
ok(not any("estampado" in v for v in ventajas_del_atuendo([rayas, floral], set())), "sin ventaja con dos estampados")
trajes = [prenda(1, "parte_superior", "blanco", estilo="formal"), prenda(2, "parte_inferior", "negro", estilo="formal")]
ok(any("formal" in v for v in ventajas_del_atuendo(trajes, formal)), "ventaja: todo formal en ocasión formal")
ok(not any("formal" in v for v in ventajas_del_atuendo(trajes, set())), "sin ocasión formal no hay esa ventaja")
mezcla = [prenda(1, "parte_superior", "blanco", estilo="semiformal"), prenda(2, "parte_inferior", "negro", estilo="formal")]
ok(any("formal" in v for v in ventajas_del_atuendo(mezcla, formal)), "ventaja: semiformal con formal cuenta como todo formal")

# --- 3. La búsqueda castiga estampados y prendas que no van con la ocasión ---
problema = busqueda.preparar_problema(rayas, [rayas, floral, lisa], set())
ok(busqueda.costo_prenda([rayas], floral, problema) == busqueda.costo_prenda([rayas], {**floral, "estampado": "liso"}, problema)
   + busqueda.PENALIZACION_ESTAMPADOS, f"+{busqueda.PENALIZACION_ESTAMPADOS} por dos estampados")

base = prenda(1, "parte_superior", "blanco", estilo="formal")
armario = [base, prenda(2, "parte_inferior", "negro", estilo="formal"), prenda(3, "calzado", "negro", estilo="deportivo"),
           prenda(4, "calzado", "negro", estilo="formal")]
mejor = busqueda.recomendar(base, armario, formal, 1)["sugerencias"][0]
ok([e["prenda"]["id"] for e in mejor["elementos"]] == [1, 2, 4], "ocasión formal: elige los zapatos formales")

# La ocasión gana aunque el pantalón formal sea peor para el clima y el jeans esté en el tono ideal.
base = prenda(1, "parte_superior", "blanco", estilo="formal")
jeans = prenda(2, "parte_inferior", "mezclilla", abrigo=2)
vestir = prenda(3, "parte_inferior", "negro", estilo="formal", abrigo=5)
zapatos = prenda(4, "calzado", "negro", estilo="formal", abrigo=2)
gorra = prenda(5, "accesorio", "negro", abrigo=1)
reloj = prenda(6, "accesorio", "negro", estilo="semiformal", abrigo=1)
for clima, nombre in ((set(), "templado"), ({"calor"}, "calor"), ({"frio"}, "frío")):
    mejor = busqueda.recomendar(base, [base, jeans, vestir, zapatos], formal | clima, 1)["sugerencias"][0]
    ok(3 in [e["prenda"]["id"] for e in mejor["elementos"]], f"ocasión formal con {nombre}: pantalón formal, no jeans")
sin_formal = [base, jeans, zapatos]
mejor = busqueda.recomendar(base, sin_formal, formal, 1)["sugerencias"][0]
ok(2 in [e["prenda"]["id"] for e in mejor["elementos"]], "sin pantalón formal: arma el atuendo con lo que hay")


def accesorio_de(armario, hechos):
    elementos = busqueda.recomendar(base, armario, hechos, 1)["sugerencias"][0]["elementos"]
    return [e["prenda"]["id"] for e in elementos if e["prenda"]["categoria"] == "accesorio"]


ok(accesorio_de([base, vestir, zapatos, gorra, reloj], formal) == [6], "ocasión formal: el reloj, no la gorra")
ok(accesorio_de([base, vestir, zapatos, gorra], formal) == [], "ocasión formal solo con gorra: sin accesorio")
ok(accesorio_de([base, vestir, zapatos, gorra], set()) == [5], "día a día: la gorra sí se agrega")
ok(accesorio_de([base, vestir, zapatos, gorra, reloj], deporte) == [5], "deporte: la gorra, no el reloj semiformal")
mejor = busqueda.recomendar(base, armario, set(), 2)["sugerencias"]
ok(mejor[0]["costo"] == mejor[1]["costo"], "en el día a día los dos calzados cuestan lo mismo")

# --- 4. API ---
cliente = TestClient(principal.aplicacion)
token = cliente.post("/api/auth/registro", json={"correo": "a@b.com", "contraseña": "12345678"}).json()["token_acceso"]
h = {"Authorization": f"Bearer {token}"}
foto = png_de_color(240, 240, 240)
datos = {"categoria": "parte_superior", "color_principal": "blanco", "nivel_abrigo": "2", "estampado": "rayas", "estilo": "formal"}
r = cliente.post("/api/prendas", headers=h, data=datos, files={"imagen": ("a.png", foto)})
ok(r.status_code == 201 and r.json()["estampado"] == "rayas" and r.json()["estilo"] == "formal", "subir prenda con estampado y estilo")
r = cliente.post("/api/prendas", headers=h, data={**datos, "estampado": "cachemir"}, files={"imagen": ("a.png", foto)})
ok(r.status_code == 422, f"estampado desconocido: 422 ({r.status_code})")
r = cliente.post("/api/prendas", headers=h, files={"imagen": ("a.png", foto)},
                 data={"categoria": "parte_inferior", "color_principal": "negro", "nivel_abrigo": "3"})
ok(r.json()["estampado"] == "liso" and r.json()["estilo"] == "casual", "sin mandarlos: liso y casual")
r = cliente.patch("/api/prendas/2/estilo", headers=h, json={"estampado": "cuadros", "estilo": "deportivo"})
ok(r.status_code == 200 and r.json()["estampado"] == "cuadros", "corregir estampado y estilo")
ok(cliente.patch("/api/prendas/2/estilo", headers=h, json={"estampado": "liso", "estilo": "x"}).status_code == 422,
   "estilo desconocido: 422")
cliente.post("/api/prendas", headers=h, files={"imagen": ("a.png", foto)},
             data={"categoria": "calzado", "color_principal": "negro", "nivel_abrigo": "3"})

# La IA vuelve a mirar la foto guardada (con un detector falso que no reconoce el estilo).
principal.detectar_prenda = lambda contenido: {"estampado": "floral", "estilo": None}
r = cliente.post("/api/prendas/3/detectar-estilo", headers=h)
ok(r.status_code == 200 and r.json()["estampado"] == "floral" and r.json()["estilo"] == "casual",
   f"detectar estilo: cambia el estampado y deja el estilo que no reconoció ({r.status_code})")
ok(cliente.post("/api/prendas/99/detectar-estilo", headers=h).status_code == 404, "detectar estilo de una prenda ajena: 404")
cliente.patch("/api/prendas/3/estilo", headers=h, json={"estampado": "liso", "estilo": "casual"})

principal.obtener_clima = lambda lat, lon: {"temperatura_c": 20, "sensacion_termica_c": 20, "probabilidad_lluvia": 0,
                                            "descripcion": "Despejado", "hechos": [], "deducciones": []}
pedido = {"prenda_base_id": 1, "latitud": 19.4, "longitud": -99.1}
r = cliente.post("/api/recomendaciones", headers=h, json={**pedido, "ocasion": "formal"})
ok(r.status_code == 200 and r.json()["ocasion"] == "formal", f"/api/recomendaciones con ocasión ({r.status_code})")
ok(cliente.post("/api/recomendaciones", headers=h, json={**pedido, "ocasion": "boda"}).status_code == 422, "ocasión desconocida: 422")
ok(cliente.post("/api/recomendaciones", headers=h, json=pedido).json()["ocasion"] == "diario", "sin ocasión: diario")

# --- 5. Explicación ---
prendas = [principal.buscar_prenda(i, {"id": 1}) for i in (1, 2, 3)]
clima = principal.obtener_clima(0, 0)
lineas = explicacion.hechos_para_explicar(prendas, clima, "formal")
ok(lineas[0].startswith("Clima: despejado, 20 °C") and "Ocasión: una ocasión formal." in lineas, "hechos: clima y ocasión")
ok(any("Una prenda deportiva no va en una ocasión formal" in l for l in lineas), "hechos: la regla que no se cumple")
ok(any("recargado" in l for l in lineas), "hechos: rayas con cuadros se recargan")
ok(any("no todas las prendas son de estilo formal" in l for l in lineas), "hechos: no todo es formal")
ok(not any("no todas" in l for l in explicacion.hechos_para_explicar(mezcla, clima, "formal")),
   "hechos: semiformal cumple con la ocasión formal")
ok(not any("Problema" in l for l in explicacion.hechos_para_explicar(prendas[2:], clima, "diario")),
   "una prenda casual en el día a día no tiene problemas")

principal.explicar_atuendo = lambda prendas, clima, ocasion: f"{len(prendas)} prendas para {ocasion}"
pedido = {"prenda_ids": [1, 2, 3], "latitud": 19.4, "longitud": -99.1, "ocasion": "formal"}
r = cliente.post("/api/recomendaciones/explicacion", headers=h, json=pedido)
ok(r.status_code == 200 and r.json()["explicacion"] == "3 prendas para formal", f"/api/recomendaciones/explicacion ({r.status_code})")
ok(cliente.post("/api/recomendaciones/explicacion", headers=h, json={**pedido, "prenda_ids": [1, 99]}).status_code == 404,
   "prenda que no existe: 404")
ok(cliente.post("/api/recomendaciones/explicacion", headers=h, json={**pedido, "prenda_ids": []}).status_code == 422,
   "sin prendas: 422")

# Ollama de verdad (se salta si no está abierto).
try:
    urllib.request.urlopen(f"{ollama.URL_OLLAMA}/api/version", timeout=2)
except OSError:
    print("SALTA Ollama no está abierto: no se prueba el modelo real")
else:
    try:
        texto = explicacion.explicar_atuendo(prendas, clima, "formal")
        ok(20 < len(texto) < 900 and "\n-" not in texto, f"modelo real redacta un párrafo: {texto[:80]}…")
    except HTTPException as e:
        ok(False, f"modelo real: {e.detail} (¿falta ollama pull {ollama.MODELO}?)")

print("\nFALLAS:", fallas)
