"""Comprueba el perceptrón de gustos: la regla de aprendizaje, sus garantías frente a A* y la API de votos.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_aprendizaje.py"""
import json
import os
import struct
import sys
import tempfile
import zlib
from pathlib import Path

os.environ["CLAVE_SECRETA"] = "clave-de-prueba"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
temporal = Path(tempfile.mkdtemp())

from servidor import base_datos  # noqa: E402

base_datos.RUTA_BD = temporal / "prueba.db"
base_datos.CARPETA_ARCHIVOS = temporal / "archivos"

from fastapi.testclient import TestClient  # noqa: E402
from servidor import aprendizaje, busqueda, principal  # noqa: E402
from servidor.aprendizaje import (AJUSTE_MAXIMO, PESOS_DE_RESPUESTA, ajustar, caracteristicas_de, distancia, entrenar,  # noqa: E402
                                  escalar, firma_de, pesos_iniciales, puntuar, reordenar)
from servidor.logica import es_apta, hechos_de_ocasion, razonar_clima  # noqa: E402

fallas = 0


def ok(cond, msg):
    global fallas
    fallas += not cond
    print(("OK   " if cond else "FALLA"), msg)


def prenda(id, categoria, color, estilo="casual", abrigo=2, estampado="liso"):
    return {"id": id, "categoria": categoria, "color_principal": color, "nivel_abrigo": abrigo, "impermeable": False,
            "estado": "disponible", "subcategoria": None, "estampado": estampado, "estilo": estilo}


def ids_de(sugerencia):
    return [e["prenda"]["id"] for e in sugerencia["elementos"]]


# --- 1. Características ---
atuendo = [prenda(1, "parte_superior", "rojo"), prenda(2, "parte_inferior", "negro", "formal", 4),
           prenda(3, "calzado", "verde", "urbano"), prenda(4, "accesorio", "rojo", "formal", 1, "rayas")]
x = caracteristicas_de(atuendo)
ok(all(0 <= v <= 1 for v in x.values()), "las características van de 0 a 1")
ok(len(x) == 13, f"son 13 características ({len(x)})")
ok(x["neutros"] == 0.25 and x["accesorio"] == 1.0 and x["estampado"] == 0.25, "proporciones de neutros, accesorio y estampado")
ok(x["contraste"] == 0.5, "contraste: tonos 3 y 5")
ok(x["complementarios"] == 1.0, "rojo y verde son complementarios")
ok(x["monocromo"] == 1 / 6, "un par de seis es del mismo color")
ok(x["estilo_casual"] == x["estilo_formal"] == x["estilo_urbano"] == 1 / 3 and x["estilo_deportivo"] == 0,
   "el estilo se reparte entre la ropa, sin contar el accesorio")
ok(caracteristicas_de(atuendo) == caracteristicas_de(atuendo[::-1]), "el orden de las prendas no cambia x")
ok(firma_de([28, 3, 16]) == firma_de([3, 16, 28]) == "3-16-28", "la firma no depende del orden")

# --- 2. La regla del perceptrón ---
pesos = {}
ajustar(pesos, {"a": 1, "b": 0.5}, -1)
ok(pesos == {"sesgo": -0.25, "a": -0.25, "b": -0.125}, "regla a mano: w + η·y·x")
copia = dict(pesos)
ajustar(pesos, {"a": 1, "b": 0.5}, -1)
ok(pesos == copia, "si acierta (y·s > 0), los pesos no cambian")
ajustar(pesos, {"a": 1, "b": 0.5}, 1)
ok(pesos != copia, "si se equivoca, corrige")
ok(puntuar({}, {"a": 1}) == 0, "sin pesos el puntaje es 0")

votos = [{"caracteristicas": {"urbano": 1.0, "formal": 0.0}, "me_gusta": 1},
         {"caracteristicas": {"urbano": 0.0, "formal": 1.0}, "me_gusta": -1},
         {"caracteristicas": {"urbano": 0.5, "formal": 0.0}, "me_gusta": 1},
         {"caracteristicas": {"urbano": 0.0, "formal": 0.5}, "me_gusta": -1}]
aprendidos = entrenar(votos)
ok(all(v["me_gusta"] * puntuar(aprendidos, v["caracteristicas"]) > 0 for v in votos), "datos separables: clasifica todos los votos")
ok(entrenar([]) == {}, "sin votos no hay pesos")

# --- 2b. Arranque en frío ---
ok(pesos_iniciales({}) == {}, "sin cuestionario, pesos en cero")
ok(pesos_iniciales({"paleta": "sin_preferencia", "ropa": "sin_preferencia", "estampados": "uno", "accesorios": "a_veces"}) == {},
   "omitir el cuestionario deja los pesos en cero")
ok(pesos_iniciales({"paleta": "oscuros", "ropa": "urbano", "estampados": "liso"}) ==
   {"tono": 1.0, "estilo_urbano": 1.0, "estilo_formal": -0.5, "estampado": -1.0}, "las respuestas suman sus pesos")
nombres = set(caracteristicas_de(atuendo))
ok(all(set(pesos) <= nombres for pregunta in PESOS_DE_RESPUESTA.values() for pesos in pregunta.values()),
   "cada peso del cuestionario es una característica real")
iniciales = {"a": 1.0}
ok(entrenar([], iniciales) == {"a": 1.0} and iniciales == {"a": 1.0}, "sin votos quedan los pesos del cuestionario, sin modificarlos")
ok(puntuar(entrenar([{"caracteristicas": {"a": 1.0}, "me_gusta": 1}], iniciales), {"a": 1.0}) > 0, "un voto de acuerdo no borra el cuestionario")
ok(puntuar(entrenar([{"caracteristicas": {"a": 1.0}, "me_gusta": -1}], iniciales), {"a": 1.0}) < 0, "los votos pueden corregir el cuestionario")


# --- 3. Reordenar lo que propone A* ---
def sugerencia(costo, *prendas):
    return {"costo": costo, "elementos": [{"prenda": p} for p in prendas]}


urbano = sugerencia(5, prenda(1, "parte_superior", "negro", "urbano"), prenda(2, "calzado", "negro", "urbano"))
casual = sugerencia(5, prenda(3, "parte_superior", "negro"), prenda(4, "calzado", "negro"))
ok([ids_de(s) for s in reordenar([casual, urbano], {}, {})] == [[3, 4], [1, 2]], "sin pesos se respeta el orden de A*")
ok([ids_de(s) for s in reordenar([casual, urbano], {"estilo_urbano": 1.0}, {})] == [[1, 2], [3, 4]], "el gusto desempata")
ordenadas = reordenar([casual, urbano], {"estilo_urbano": 99.0, "estilo_casual": -99.0}, {"1-2": 1})
ok(ordenadas[0]["costo_final"] == 5 - AJUSTE_MAXIMO and ordenadas[1]["costo_final"] == 5 + AJUSTE_MAXIMO, "el ajuste tiene tope")
ok(ordenadas[0]["voto"] == 1 and ordenadas[1]["voto"] is None, "cada sugerencia trae su voto")
ok(ordenadas[0]["costo"] == 5, "se conserva el costo de A*")
ok(escalar([1.0, 2.0, 3.0]) == [-1.0, 0.0, 1.0] and escalar([2.0, 2.0]) == [0.0, 0.0] and escalar([]) == [], "escalar va de -1 a +1")
ok(distancia({"a": 1.0, "b": 0.5}, {"a": 0.5, "b": 1.0}) == 1.0, "distancia manhattan")
gustado = caracteristicas_de([e["prenda"] for e in urbano["elementos"]])
ok([ids_de(s) for s in reordenar([casual, urbano], {}, {}, [gustado])] == [[1, 2], [3, 4]], "el corazón sube lo parecido, sin pesos")
ok(5 - AJUSTE_MAXIMO <= reordenar([urbano, casual], {}, {}, [gustado])[0]["costo_final"] < 5, "el parecido respeta el tope")
ordenadas = reordenar([urbano, casual], {"estilo_urbano": 99.0, "estilo_casual": -99.0}, {"3-4": 1, "1-2": -1})
ok([ids_de(s) for s in ordenadas] == [[3, 4], [1, 2]], "lo votado no se adivina: el corazón manda sobre los pesos")
ok(ordenadas[0]["costo_final"] == 5 - AJUSTE_MAXIMO and ordenadas[1]["costo_final"] == 5 + AJUSTE_MAXIMO, "lo votado sigue acotado")
ok(AJUSTE_MAXIMO * 2 < busqueda.PENALIZACION_NO_APTA < busqueda.PENALIZACION_OCASION, "el ajuste no alcanza a ninguna penalización")

armario = [prenda(1, "parte_superior", "blanco", "formal"), prenda(2, "parte_inferior", "negro", "formal"),
           prenda(3, "parte_inferior", "mezclilla", "casual"), prenda(4, "parte_inferior", "mezclilla", "urbano"),
           prenda(5, "calzado", "negro", "formal"), prenda(6, "calzado", "blanco", "casual"),
           prenda(7, "calzado", "gris", "urbano"), prenda(8, "accesorio", "negro", "semiformal", 1),
           prenda(9, "accesorio", "negro", "casual", 1)]
hechos = hechos_de_ocasion("formal")
deducidos = razonar_clima(hechos)[0]
candidatas = busqueda.recomendar(armario[0], armario, hechos, 12)["sugerencias"]
gusto_contrario = {"estilo_casual": 99.0, "estilo_urbano": 99.0, "estilo_formal": -99.0, "sesgo": 99.0}
primera = reordenar(candidatas, gusto_contrario, {})[0]
ok(all(es_apta(e["prenda"], deducidos) for e in primera["elementos"]), "ocasión formal: los gustos no cuelan una prenda fuera de ocasión")

ligera = prenda(2, "parte_inferior", "negro", abrigo=1)
abrigada = prenda(3, "parte_inferior", "negro", abrigo=4)
frio = [prenda(1, "parte_superior", "negro", abrigo=4), ligera, abrigada, prenda(4, "calzado", "negro", abrigo=4),
        prenda(5, "abrigo", "negro", abrigo=4)]
candidatas = busqueda.recomendar(frio[0], frio, {"frio"}, 12)["sugerencias"]
primera = reordenar(candidatas, {"abrigo": -99.0, "sesgo": -99.0}, {})[0]
ok(3 in ids_de(primera), "con frío: el gusto por lo ligero no pasa sobre la regla del clima")

# El look con corazón se queda en pantalla, aunque otro con las mismas características no tenga.
parecidos = [prenda(1, "parte_superior", "gris"), prenda(2, "parte_inferior", "negro"), prenda(3, "calzado", "cafe", abrigo=3),
             prenda(4, "calzado", "cafe", abrigo=3), prenda(5, "calzado", "blanco", abrigo=3), prenda(6, "calzado", "negro", abrigo=3),
             prenda(7, "calzado", "gris", abrigo=3)]


def mostrar(votos):
    pesos = entrenar(list(votos.values()))
    firmas = {firma_de(ids_de(s)): s for s in busqueda.recomendar(parecidos[0], parecidos, set(), 12)["sugerencias"]}
    resultado = reordenar(list(firmas.values()), pesos, {f: v["me_gusta"] for f, v in votos.items()})[:3]
    for s in resultado:
        votos.setdefault(firma_de(ids_de(s)), {"caracteristicas": caracteristicas_de([e["prenda"] for e in s["elementos"]]), "me_gusta": -1})
    return [firma_de(ids_de(s)) for s in resultado]


votos = {}
primeras = mostrar(votos)
votos[primeras[1]]["me_gusta"] = 1
ok(all(mostrar(votos)[0] == primeras[1] for _ in range(4)), "el look con corazón se queda en primer lugar")

# Con costos parejos, lo que ya se vio sin corazón deja lugar a lo que falta por ver.
parecidos = [prenda(1, "parte_superior", "gris"), prenda(2, "parte_inferior", "negro"),
             *[prenda(3 + i, "calzado", color, abrigo=3) for i, color in enumerate(["rojo", "verde", "azul", "mezclilla", "rojo"])]]
votos = {}
vistos = set()
for _ in range(3):
    vistos |= set(mostrar(votos))
ok(len(vistos) == 5, f"sin corazones aparecen opciones nuevas ({len(vistos)} de 5)")

# Un gusto simulado sobre un armario fijo: mejora con los votos y los looks que gustan suben.
surtido = [prenda(1, "parte_superior", "gris"), prenda(2, "parte_superior", "blanco"), prenda(3, "parte_superior", "negro"),
           *[prenda(10 + i, "parte_inferior", color, estilo, 3) for i, (color, estilo) in enumerate(
               [("mezclilla", "casual"), ("mezclilla", "urbano"), ("negro", "casual"), ("negro", "urbano"), ("gris", "urbano")])],
           *[prenda(20 + i, "calzado", color, estilo, 3) for i, (color, estilo) in enumerate(
               [("blanco", "casual"), ("gris", "urbano"), ("negro", "casual"), ("negro", "urbano"), ("cafe", "casual")])]]


def le_gusta(s):
    return caracteristicas_de([e["prenda"] for e in s["elementos"]])["estilo_urbano"] >= 0.5


def tasa(pesos, base):
    mostradas = reordenar(busqueda.recomendar(base, surtido, set(), 12)["sugerencias"], pesos, {})[:3]
    return sum(le_gusta(s) for s in mostradas) / 3


antes = tasa({}, surtido[2])
votos = []
for s in reordenar(busqueda.recomendar(surtido[0], surtido, set(), 12)["sugerencias"], {}, {}):
    votos.append({"caracteristicas": caracteristicas_de([e["prenda"] for e in s["elementos"]]), "me_gusta": 1 if le_gusta(s) else -1})
pesos = entrenar(votos)
despues = tasa(pesos, surtido[2])
ok(despues > antes and despues == 1.0, f"aprende el gusto urbano en otra prenda base ({antes:.2f} -> {despues:.2f})")
ok(pesos["estilo_urbano"] > 0 > pesos["estilo_casual"], "los pesos muestran lo aprendido")


# --- 4. API ---
def png(lado=8):
    def bloque(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))
    fila = b"\x00" + bytes([120, 120, 120]) * lado
    return (b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", lado, lado, 8, 2, 0, 0, 0))
            + bloque(b"IDAT", zlib.compress(fila * lado)) + bloque(b"IEND", b""))


principal.obtener_clima = lambda lat, lon: {"hechos": [], "descripcion": "Despejado", "temperatura_c": 20,
                                            "sensacion_termica_c": 20, "probabilidad_lluvia": 0, "deducciones": []}
with TestClient(principal.aplicacion) as cliente:
    def cuenta(correo):
        r = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "contraseña-larga"})
        return {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    h, otra = cuenta("gustos@prueba.com"), cuenta("otra@prueba.com")

    def subir(cabeceras, categoria, color, estilo):
        datos = {"categoria": categoria, "color_principal": color, "nivel_abrigo": "3", "estilo": estilo}
        return cliente.post("/api/prendas", headers=cabeceras, data=datos, files={"imagen": ("p.png", png(), "image/png")}).json()["id"]

    playera = subir(h, "parte_superior", "gris", "casual")
    jeans = subir(h, "parte_inferior", "mezclilla", "casual")
    cargo = subir(h, "parte_inferior", "mezclilla", "urbano")
    tenis = subir(h, "calzado", "negro", "urbano")
    ajena = subir(otra, "calzado", "negro", "casual")
    pedido = {"prenda_base_id": playera, "latitud": 19.4, "longitud": -99.1}

    r = cliente.post("/api/recomendaciones", headers=h, json=pedido)
    primera = r.json()["sugerencias"][0]
    ok(r.status_code == 200 and primera["voto"] is None and "costo_final" in primera, "recomendaciones sin votos")
    ok(len(r.json()["sugerencias"]) <= 3, "se muestran 3 aunque A* proponga más")
    mostrados = len(r.json()["sugerencias"])

    ok(cliente.get("/api/auth/yo", headers=h).json()["cuestionario_listo"] is False, "cuenta nueva: falta el cuestionario")
    cuestionario = lambda datos, cabeceras=h: cliente.put("/api/preferencias", headers=cabeceras, json=datos)
    ok(cliente.put("/api/preferencias", json={}).status_code == 401, "cuestionario sin sesión: 401")
    ok(cuestionario({"ropa": "x"}).status_code == 422, "respuesta desconocida: 422")
    ok(cliente.get("/api/auth/yo", headers=h).json()["cuestionario_listo"] is False, "una respuesta inválida no lo completa")

    def votar(ids, me_gusta, cabeceras=h):
        return cliente.post("/api/atuendos/voto", headers=cabeceras, json={"prenda_ids": ids, "me_gusta": me_gusta})

    cuantos = lambda tabla: base_datos.consultar(f"SELECT count(*) AS n FROM {tabla}")[0]["n"]

    ok(mostrados == 2 and cuantos("votos_atuendo") == 2, "lo que se muestra queda registrado")
    voto_de = lambda ids: base_datos.consultar_uno("SELECT * FROM votos_atuendo WHERE firma = ?", (firma_de(ids),))
    ok(voto_de([playera, cargo, tenis])["me_gusta"] == -1, "sin corazón cuenta como no me gusta")
    ok(cuantos("pesos_usuario") == 1, "se guardan los pesos")

    cliente.post("/api/recomendaciones", headers=h, json=pedido)
    ok(cuantos("votos_atuendo") == 2, "volver a mostrarlo no duplica el voto")

    r = votar([playera, cargo, tenis], True)
    ok(r.status_code == 200 and r.json() == {"voto": 1, "votos": 2}, f"el corazón cambia el voto ({r.status_code})")
    guardado = voto_de([playera, cargo, tenis])
    ok(guardado["me_gusta"] == 1, "con corazón cuenta como me gusta")
    ok(json.loads(guardado["caracteristicas"])["estilo_urbano"] == 2 / 3, "las características las calcula el servidor")

    r = votar([tenis, cargo, playera], False)
    ok(r.json() == {"voto": -1, "votos": 2} and cuantos("votos_atuendo") == 2, "quitar el corazón reemplaza el voto")
    pesos = json.loads(base_datos.consultar_uno("SELECT pesos FROM pesos_usuario")["pesos"])
    ok(pesos["estilo_urbano"] < 0, "los pesos siguen al voto nuevo, sin rastro del anterior")

    votar([playera, cargo, tenis], True)
    r = cliente.post("/api/recomendaciones", headers=h, json=pedido).json()["sugerencias"]
    ok(ids_de(r[0]) == [playera, cargo, tenis] or set(ids_de(r[0])) == {playera, cargo, tenis}, "lo que gustó sube al primer lugar")
    ok(r[0]["voto"] == 1, "la sugerencia trae su voto para pintar el botón")
    ok(cliente.post("/api/recomendaciones", headers=otra, json={**pedido, "prenda_base_id": ajena}).json()["sugerencias"] == [],
       "los gustos no se mezclan con otra cuenta")
    ok(cuantos("pesos_usuario") == 1, "la otra cuenta sigue sin pesos")

    ok(voto_de([playera, jeans, tenis])["me_gusta"] == -1, "un look mostrado sigue sin corazón")
    elementos = [{"prenda_id": i, "rol": "parte"} for i in (playera, jeans, tenis)]
    r = cliente.post("/api/atuendos", headers=h, json={"puntuacion": 0, "reporte_clima": None, "elementos": elementos})
    ok(r.status_code == 201 and voto_de([playera, jeans, tenis])["me_gusta"] == 1, "guardar un atuendo cuenta como corazón")
    ok(cuantos("votos_atuendo") == 2, "guardar no duplica el voto")

    ok(votar([playera, ajena], True).status_code == 404, "prenda ajena: 404")
    ok(votar([playera, playera], True).status_code == 422, "prendas repetidas: 422")
    ok(votar([playera], True).status_code == 422, "una sola prenda: 422")
    ok(cliente.post("/api/atuendos/voto", json={"prenda_ids": [playera, jeans], "me_gusta": True}).status_code == 401, "sin sesión: 401")

    r = cliente.post("/api/recomendaciones", headers=h, json={**pedido, "algoritmo": "dfs"})
    ok(r.status_code == 200 and all("costo_final" not in s for s in r.json()["sugerencias"]), "los otros algoritmos no pasan por el perceptrón")
    ok(cuantos("votos_atuendo") == 2, "los otros algoritmos no registran votos")

    ok(cuestionario({"ropa": "urbano"}).status_code == 200, "guardar el cuestionario")
    ok(cliente.get("/api/auth/yo", headers=h).json()["cuestionario_listo"] is True, "cuestionario contestado")
    ok(cuantos("votos_atuendo") == 2, "contestar el cuestionario no borra los votos")
    gorra = subir(h, "accesorio", "negro", "casual")
    tiene_accesorio = lambda: any(e["prenda"]["id"] == gorra for s in cliente.post("/api/recomendaciones", headers=h, json=pedido).json()["sugerencias"]
                                  for e in s["elementos"])
    ok(tiene_accesorio(), "con accesorios a veces, el atuendo lleva accesorio")
    cuestionario({"ropa": "urbano", "accesorios": "casi_nunca"})
    ok(not tiene_accesorio(), "con accesorios casi nunca, el atuendo va sin accesorio")

    nueva = cuenta("arranque@prueba.com")
    base_nueva = subir(nueva, "parte_superior", "gris", "casual")
    subir(nueva, "parte_inferior", "mezclilla", "casual")
    urbana = subir(nueva, "parte_inferior", "mezclilla", "urbano")
    subir(nueva, "calzado", "negro", "casual")
    tenis_urbano = subir(nueva, "calzado", "negro", "urbano")
    cuestionario({"ropa": "urbano"}, nueva)
    r = cliente.post("/api/recomendaciones", headers=nueva, json={**pedido, "prenda_base_id": base_nueva}).json()["sugerencias"]
    ok({urbana, tenis_urbano} <= set(ids_de(r[0])), "primera generación, sin votos: el cuestionario ya cambia el resultado")

    cliente.delete(f"/api/prendas/{tenis}", headers=h)
    ok(base_datos.consultar_uno("SELECT count(*) AS n FROM votos_atuendo WHERE firma LIKE ?", (f"%{playera}%",))["n"] >= 2,
       "borrar una prenda conserva lo aprendido")

print("\nFALLAS:", fallas)
sys.exit(1 if fallas else 0)
