"""Comprueba el modo viaje: lugares, clima de cada día, un look por día, la maleta y que no cuente como voto.
Open-Meteo se simula: las pruebas no salen a internet.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_viaje.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi.testclient import TestClient  # noqa: E402
from pruebas.comun import png_de_color  # noqa: E402
from servidor import base_datos, principal, viaje  # noqa: E402

# Día 1 frío, día 2 calor, día 3 lluvia; los demás templados.
SENSACION = [(8, 2), (34, 28), (22, 16)] + [(22, 16)] * 13
LLUVIA = [0, 0, 80] + [0] * 13
pedidas = []


def open_meteo_falso(url, parametros):
    pedidas.append(url)
    if url == viaje.URL_LUGARES:
        if parametros["name"] == "Nada":
            return {}
        return {"results": [{"name": "Toluca", "admin1": "Estado de México", "country": "México",
                             "latitude": 19.29, "longitude": -99.65}]}
    return {"daily": {
        "time": [f"2026-12-{d:02d}" for d in range(1, 17)],
        "temperature_2m_max": [s[0] + 1 for s in SENSACION], "temperature_2m_min": [s[1] + 1 for s in SENSACION],
        "apparent_temperature_max": [s[0] for s in SENSACION], "apparent_temperature_min": [s[1] for s in SENSACION],
        "precipitation_probability_max": LLUVIA, "weather_code": [61 if p > 50 else 1 for p in LLUVIA],
    }}


viaje.consultar = open_meteo_falso

with TestClient(principal.aplicacion) as cliente:
    r = cliente.post("/api/auth/registro", json={"correo": "viaje@prueba.com", "contraseña": "contraseña-larga"})
    h = {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    def subir(categoria, color, estilo="casual", abrigo="3"):
        datos = {"categoria": categoria, "color_principal": color, "nivel_abrigo": abrigo, "estilo": estilo}
        return cliente.post("/api/prendas", headers=h, data=datos,
                            files={"imagen": ("p.png", png_de_color(120, 120, 120, 8), "image/png")}).json()["id"]

    arribas = [subir("parte_superior", "gris"), subir("parte_superior", "blanco"), subir("parte_superior", "negro", "urbano")]
    abajos = [subir("parte_inferior", "mezclilla"), subir("parte_inferior", "negro")]
    zapatos = subir("calzado", "negro")
    abrigo = subir("abrigo", "beige", "casual", "5")

    # --- Lugares ---
    r = cliente.get("/api/viaje/lugares", headers=h, params={"nombre": "Toluca"})
    ok(r.status_code == 200 and r.json()[0]["nombre"] == "Toluca" and r.json()[0]["latitud"] == 19.29, "busca el destino")
    ok(cliente.get("/api/viaje/lugares", headers=h, params={"nombre": "Nada"}).json() == [], "sin resultados, lista vacía")
    ok(cliente.get("/api/viaje/lugares", headers=h, params={"nombre": "T"}).status_code == 422, "nombre muy corto: 422")
    ok(cliente.get("/api/viaje/lugares", params={"nombre": "Toluca"}).status_code == 401, "buscar pide sesión")

    # --- El plan ---
    pedido = {"latitud": 19.29, "longitud": -99.65, "lugar": "Toluca", "salida": 0, "dias": 3}
    r = cliente.post("/api/viaje", headers=h, json=pedido)
    plan = r.json()
    ok(r.status_code == 200 and len(plan["dias"]) == 3 and plan["lugar"] == "Toluca", "un plan de 3 días")
    ok([d["clima"]["fecha"] for d in plan["dias"]] == ["2026-12-01", "2026-12-02", "2026-12-03"], "las fechas del pronóstico")
    hechos = [set(d["clima"]["hechos"]) for d in plan["dias"]]
    ok("frio" in hechos[0] and "necesita_abrigo" in hechos[0], "día 1: frío y la lógica deduce que necesita abrigo")
    ok("calor" in hechos[1] and "lluvia" in hechos[2], "día 2 calor y día 3 lluvia")
    ok(all(d["sugerencia"] for d in plan["dias"]), "un look por día")
    ids = [[e["prenda"]["id"] for e in d["sugerencia"]["elementos"]] for d in plan["dias"]]
    ok(abrigo in ids[0] and abrigo not in ids[1], "con frío lleva abrigo; con calor no")
    ok(len({i[0] for i in ids}) == 3, f"tres partes de arriba distintas en tres días: {[i[0] for i in ids]}")

    maleta = {m["prenda"]["id"]: m["dias"] for m in plan["maleta"]}
    ok(len(maleta) == len(plan["maleta"]), "la maleta no repite prendas")
    ok(all(numero in maleta[i] for numero, look in enumerate(ids, start=1) for i in look), "cada prenda dice en qué días se usa")
    ok(maleta[zapatos] == [1, 2, 3], "los zapatos se repiten sin problema")
    ok([m["prenda"]["categoria"] for m in plan["maleta"]][0] == "abrigo", "la maleta va en orden del cuerpo")
    ok(base_datos.bd().votos_atuendo.count_documents({}) == 0, "el viaje no cuenta como voto")

    salida = cliente.post("/api/viaje", headers=h, json={**pedido, "salida": 2, "dias": 1}).json()
    ok(salida["dias"][0]["clima"]["fecha"] == "2026-12-03", "salir en 2 días empieza en el día 3 del pronóstico")
    ok(pedidas.count(viaje.URL_LUGARES) == 2 and pedidas.count(viaje.URL_OPEN_METEO) == 1,
       "el pronóstico se reutiliza (caché en climas): una sola consulta")

    # --- Repetir cuesta ---
    armario = principal.prendas_de(base_datos.bd().usuarios.find_one({"correo": "viaje@prueba.com"})["_id"])
    gustos = {"pesos": {}, "votos": {}, "gustados": [], "preferencias": {}, "con_accesorio": True}
    primero, _ = viaje.look_del_dia(armario, set(), {}, gustos)
    usadas = {e["prenda"]["id"]: 5 for e in primero["elementos"]}
    segundo, _ = viaje.look_del_dia(armario, set(), usadas, gustos)
    ok(primero["elementos"][0]["prenda"]["id"] != segundo["elementos"][0]["prenda"]["id"],
       "si ya se usó mucho, cambia de parte de arriba")
    ok(segundo["costo_viaje"] >= segundo["costo_final"], "costo_viaje = costo con gustos + repeticiones")

    # --- Zapatos: repetir no cuesta, empacar otro par sí ---
    otros_zapatos = subir("calzado", "negro")  # idénticos a los primeros: solo los separa la maleta
    armario = principal.prendas_de(base_datos.bd().usuarios.find_one({"correo": "viaje@prueba.com"})["_id"])
    for ya_van in (zapatos, otros_zapatos):
        look, _ = viaje.look_del_dia(armario, set(), {ya_van: 1}, gustos)
        calzado = next(e["prenda"]["id"] for e in look["elementos"] if e["prenda"]["categoria"] == "calzado")
        ok(calzado == ya_van, f"con el par {ya_van} ya en la maleta, vuelve a usarlo en lugar de empacar otro")

    # --- Validación ---
    ok(cliente.post("/api/viaje", headers=h, json={**pedido, "dias": 17}).status_code == 422, "más de 16 días: 422")
    ok(cliente.post("/api/viaje", headers=h, json={**pedido, "salida": 16}).status_code == 422, "salir fuera del pronóstico: 422")
    ok(cliente.post("/api/viaje", headers=h, json={**pedido, "salida": 10, "dias": 7}).status_code == 422,
       "el rango no puede pasar del pronóstico (10 + 7 > 16): 422")
    rango = cliente.post("/api/viaje", headers=h, json={**pedido, "salida": 8, "dias": 8})
    ok(rango.status_code == 200 and len(rango.json()["dias"]) == 8, "un rango de calendario de 8 días (del 9 al 16): 200")
    ok(cliente.post("/api/viaje", headers=h, json={**pedido, "ocasion": "playa"}).status_code == 422, "ocasión desconocida: 422")
    ok(cliente.post("/api/viaje", json=pedido).status_code == 401, "el viaje pide sesión")

    # --- Armario vacío de otra cuenta ---
    r = cliente.post("/api/auth/registro", json={"correo": "vacio@prueba.com", "contraseña": "contraseña-larga"})
    vacio = cliente.post("/api/viaje", headers={"Authorization": f"Bearer {r.json()['token_acceso']}"}, json=pedido).json()
    ok(all(d["sugerencia"] is None and d["avisos"] for d in vacio["dias"]) and vacio["maleta"] == [],
       "sin ropa: cada día avisa qué falta y la maleta va vacía")

terminar()
