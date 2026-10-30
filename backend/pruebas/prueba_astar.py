"""Comprueba que A* devuelve los atuendos más baratos (contra fuerza bruta), los otros algoritmos y la API.
Ejecutar desde la carpeta backend: .venv\Scripts\python pruebas\prueba_astar.py"""
import itertools
import os
import random
import sys
import tempfile
from pathlib import Path

os.environ["CLAVE_SECRETA"] = "clave-de-prueba"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
temporal = Path(tempfile.mkdtemp())

from servidor import base_datos  # noqa: E402

base_datos.RUTA_BD = temporal / "prueba.db"
base_datos.CARPETA_ARCHIVOS = temporal / "archivos"

from fastapi.testclient import TestClient  # noqa: E402
from servidor import algoritmos, busqueda, principal  # noqa: E402
from servidor.logica import ESTILOS
from servidor.logica import hechos_de_ocasion, razonar_clima  # noqa: E402

fallas = 0


def ok(cond, msg):
    global fallas
    fallas += not cond
    print(("OK   " if cond else "FALLA"), msg)


COLORES = list(busqueda.TONO)
CATEGORIAS = ["parte_superior", "parte_inferior", "calzado", "abrigo", "accesorio"]


def armario_al_azar(semilla, n=14):
    r = random.Random(semilla)
    return [
        {"id": i, "categoria": r.choice(CATEGORIAS), "color_principal": r.choice(COLORES),
         "nivel_abrigo": r.randint(1, 5), "impermeable": r.random() < 0.3,
         "estado": r.choice(["disponible"] * 5 + ["en_lavado"]), "subcategoria": None,
         "estampado": r.choice(["liso"] * 3 + ["rayas", "floral"]), "estilo": r.choice(ESTILOS)}
        for i in range(1, n + 1)
    ]


def hechos_al_azar(semilla):
    """Un clima y una ocasión al azar, con las deducciones de la lógica."""
    r = random.Random(semilla)
    clima = r.choice([{"frio"}, {"calor"}, {"lluvia"}, {"frio", "lluvia"}, set()])
    hechos, _ = razonar_clima(clima | hechos_de_ocasion(r.choice(["diario", "formal", "deporte"])))
    return hechos


def costo_optimo(conjunto, problema):
    """El menor costo de armar ese atuendo, probando todos los órdenes en que se agregan las prendas."""
    mejor = None
    for orden in itertools.permutations(conjunto):
        atuendo, g, valido = [problema["base"]], 0, True
        for p in orden:
            if not busqueda.combinan_todas(atuendo, p):
                valido = False
                break
            g += busqueda.costo_prenda(atuendo, p, problema)
            atuendo.append(p)
        if valido and (mejor is None or g < mejor):
            mejor = g
    return mejor


def fuerza_bruta(problema):
    """Costos de todos los atuendos completos posibles, de menor a mayor."""
    faltantes = sorted(problema["necesarias"] - {problema["base"]["categoria"]})
    por_categoria = [[p for p in problema["candidatas"] if p["categoria"] == c] for c in faltantes]
    costos = []
    for conjunto in itertools.product(*por_categoria):
        c = costo_optimo(list(conjunto), problema)
        if c is not None:
            costos.append(c)
    return sorted(costos)


# --- 1. A* da los más baratos, en 300 armarios, climas y ocasiones al azar ---
errores, casos, con_resultado = [], 0, 0
for semilla in range(300):
    armario = armario_al_azar(semilla)
    base = next((p for p in armario if p["categoria"] != "accesorio"), None)
    if not base:
        continue
    hechos = hechos_al_azar(semilla)
    problema = busqueda.preparar_problema(base, armario, hechos)
    esperado = fuerza_bruta(problema)[:3]
    obtenido = [n["g"] for n in busqueda.mejores_atuendos(problema, 3)]
    casos += 1
    con_resultado += bool(esperado)
    if esperado != obtenido:
        errores.append((semilla, esperado, obtenido))
ok(not errores, f"A* = fuerza bruta en {casos} armarios ({con_resultado} con atuendos). Diferencias: {errores[:3]}")

# --- 1b. Los otros algoritmos con los mismos armarios ---
errores = {clave: [] for clave in algoritmos.ALGORITMOS}
for semilla in range(300):
    armario = armario_al_azar(semilla)
    base = next((p for p in armario if p["categoria"] != "accesorio"), None)
    if not base:
        continue
    hechos = hechos_al_azar(semilla)
    problema = busqueda.preparar_problema(base, armario, hechos)
    todos = fuerza_bruta(problema)
    for clave, buscar in algoritmos.ALGORITMOS.items():
        nodos = buscar(problema, 3)
        completos = all(busqueda.faltan(n["atuendo"], problema) == 0 for n in nodos)
        distintos = len({busqueda.estado(n["atuendo"]) for n in nodos}) == len(nodos)
        # Ningún atuendo cuesta menos que el óptimo ni que la estimación de A* (h admisible).
        baratos = not nodos or (min(n["g"] for n in nodos) >= todos[0] >= algoritmos.costo_estimado(problema))
        if not (completos and distintos and baratos) or (clave != "heuristica_simple" and len(nodos) != min(3, len(todos))):
            errores[clave].append(semilla)
        if clave == "ucs" and [n["g"] for n in nodos] != todos[:3]:
            errores[clave].append(semilla)
    if len(algoritmos.heuristica_mejorada(problema)) != len(todos):
        errores["heuristica_mejorada"].append(semilla)
for clave, semillas in errores.items():
    ok(not semillas, f"{clave}: atuendos completos, sin repetir y nunca más baratos que el óptimo {semillas[:5]}")

# Límite de profundidad: con la blusa como base hacen falta 2 prendas (parte inferior y calzado).
armario = [
    {"id": 1, "categoria": "parte_superior", "color_principal": "blanco", "nivel_abrigo": 2, "impermeable": False, "estado": "disponible", "subcategoria": None},
    {"id": 2, "categoria": "parte_inferior", "color_principal": "negro", "nivel_abrigo": 2, "impermeable": False, "estado": "disponible", "subcategoria": None},
    {"id": 3, "categoria": "calzado", "color_principal": "negro", "nivel_abrigo": 2, "impermeable": False, "estado": "disponible", "subcategoria": None},
]
problema = busqueda.preparar_problema(armario[0], armario, set())
ok(algoritmos.heuristica_mejorada(problema, limite=1) == [], "heurística mejorada con límite 1: sin atuendos")
ok(len(algoritmos.heuristica_mejorada(problema, limite=2)) == 1, "heurística mejorada con límite 2: un atuendo")

# --- 2. Orden, accesorio y prendas no disponibles ---
armario = [
    {"id": 1, "categoria": "parte_superior", "color_principal": "blanco", "nivel_abrigo": 2, "impermeable": False, "estado": "disponible", "subcategoria": "Blusa"},
    {"id": 2, "categoria": "parte_inferior", "color_principal": "mezclilla", "nivel_abrigo": 2, "impermeable": False, "estado": "disponible", "subcategoria": None},
    {"id": 3, "categoria": "parte_inferior", "color_principal": "negro", "nivel_abrigo": 3, "impermeable": False, "estado": "disponible", "subcategoria": None},
    {"id": 4, "categoria": "calzado", "color_principal": "negro", "nivel_abrigo": 2, "impermeable": False, "estado": "disponible", "subcategoria": None},
    {"id": 5, "categoria": "calzado", "color_principal": "beige", "nivel_abrigo": 2, "impermeable": False, "estado": "en_lavado", "subcategoria": None},
    {"id": 6, "categoria": "accesorio", "color_principal": "rosa", "nivel_abrigo": 1, "impermeable": False, "estado": "disponible", "subcategoria": "Bolsa"},
]
r = busqueda.recomendar(armario[0], armario, set(), 3)
costos = [s["costo"] for s in r["sugerencias"]]
ok(len(r["sugerencias"]) == 2 and costos == sorted(costos), f"2 atuendos posibles en orden de costo {costos}")
ok(all(s["elementos"][0]["prenda"]["id"] == 1 for s in r["sugerencias"]), "la prenda base va primero")
ok(all(any(e["prenda"]["id"] == 6 for e in s["elementos"]) for s in r["sugerencias"]), "se agrega el accesorio que combina")
ok(all("Se completa con un accesorio" in s["ventajas"] for s in r["sugerencias"]), "ventaja del accesorio")
ok(not any(e["prenda"]["id"] == 5 for s in r["sugerencias"] for e in s["elementos"]), "la prenda en lavado no se usa")
ok(set(r["sugerencias"][0]) == {"elementos", "costo", "puntuacion", "ventajas"}, f"forma de la sugerencia {set(r['sugerencias'][0])}")
r = busqueda.recomendar(armario[0], armario, {"frio", "necesita_abrigo"}, 3)
ok(any("abrigo" in a for a in r["avisos"]), f"aviso de abrigo con frío {r['avisos']}")
r = busqueda.recomendar(armario[0], armario[:2], set(), 3)
ok(r["categorias_faltantes"] == ["calzado"], f"falta calzado {r['categorias_faltantes']}")

# --- 3. API ---
cliente = TestClient(principal.aplicacion)
token = cliente.post("/api/auth/registro", json={"correo": "a@b.com", "contraseña": "12345678"}).json()["token_acceso"]
h = {"Authorization": f"Bearer {token}"}
for p in armario:
    base_datos.ejecutar(
        "INSERT INTO prendas (id, usuario_id, url_imagen, categoria, subcategoria, color_principal, nivel_abrigo, impermeable, estado) "
        "VALUES (?, 1, '/archivos/x.jpg', ?, ?, ?, ?, ?, ?)",
        (p["id"], p["categoria"], p["subcategoria"], p["color_principal"], p["nivel_abrigo"], p["impermeable"], p["estado"]),
    )
principal.obtener_clima = lambda lat, lon: {"temperatura_c": 20, "sensacion_termica_c": 20, "probabilidad_lluvia": 0,
                                            "descripcion": "Despejado", "hechos": [], "deducciones": []}
r = cliente.post("/api/recomendaciones", headers=h, json={"prenda_base_id": 1, "latitud": 19.4, "longitud": -99.1})
ok(r.status_code == 200 and len(r.json()["sugerencias"]) == 2 and "busqueda" not in r.json(), f"/api/recomendaciones ({r.status_code})")
ok(cliente.post("/api/busquedas", headers=h, json={}).status_code == 404, "/api/busquedas ya no existe")
for clave in algoritmos.ALGORITMOS:
    otro = cliente.post("/api/recomendaciones", headers=h,
                        json={"prenda_base_id": 1, "latitud": 19.4, "longitud": -99.1, "algoritmo": clave})
    ok(otro.status_code == 200 and otro.json()["sugerencias"], f"/api/recomendaciones con {clave}")
otro = cliente.post("/api/recomendaciones", headers=h, json={"prenda_base_id": 1, "latitud": 19.4, "longitud": -99.1, "algoritmo": "x"})
ok(otro.status_code == 422, "algoritmo desconocido: 422")

# Guardar con la base al final del orden de ids: debe volver con la base primero.
sug = r.json()["sugerencias"][0]
elementos = [{"prenda_id": e["prenda"]["id"], "rol": e["rol"]} for e in sug["elementos"]]
base_ultima = {"prenda_id": 4, "rol": "calzado"}
orden = [base_ultima] + [e for e in elementos if e["prenda_id"] != 4]
r = cliente.post("/api/atuendos", headers=h, json={"puntuacion": 1, "reporte_clima": {"descripcion": "Despejado"}, "elementos": orden})
ok(r.status_code == 201 and r.json()["elementos"][0]["prenda"]["id"] == 4, "atuendo guardado respeta el orden (base primero)")
lista = cliente.get("/api/atuendos", headers=h).json()
ok(len(lista) == 1 and lista[0]["elementos"][0]["prenda"]["id"] == 4, "listar atuendos")
r = cliente.patch("/api/prendas/2/estado", headers=h, json={"estado": "en_lavado"})
ok(r.status_code == 200 and r.json()["estado"] == "en_lavado", "cambiar estado de prenda")
ok(cliente.delete(f"/api/atuendos/{lista[0]['id']}", headers=h).status_code == 204, "eliminar atuendo")

print("\nFALLAS:", fallas)
