"""Comprueba las cápsulas de guardarropa (capsulas.py): cuotas, looks válidos, greedy + búsqueda local, acentos,
clima del viaje y las rutas con la checklist. Open-Meteo se simula.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_capsulas.py"""
import os
import sys
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi.testclient import TestClient  # noqa: E402
from pruebas.comun import png_de_color  # noqa: E402
from servidor import capsulas as ca, principal, viaje  # noqa: E402
from servidor.logica import COLORES_NEUTROS, por_que_combinan, se_recargan  # noqa: E402

siguiente = iter(range(1, 1000))


def prenda(categoria, color, abrigo=2, estampado="liso", estilo="casual", estado="disponible"):
    return {"id": next(siguiente), "categoria": categoria, "color_principal": color, "nivel_abrigo": abrigo,
            "impermeable": False, "estampado": estampado, "estilo": estilo, "estado": estado, "subcategoria": None}


armario = [
    prenda("parte_superior", "gris"), prenda("parte_superior", "blanco"), prenda("parte_superior", "negro"),
    prenda("parte_superior", "rojo"), prenda("parte_superior", "verde", estampado="floral"),
    prenda("parte_superior", "amarillo"), prenda("parte_superior", "azul", estado="en_lavado"),
    prenda("parte_inferior", "mezclilla"), prenda("parte_inferior", "negro"), prenda("parte_inferior", "beige"),
    prenda("parte_inferior", "rojo"), prenda("parte_inferior", "verde", estampado="cuadros"),
    prenda("calzado", "negro", 3), prenda("calzado", "blanco", 3), prenda("calzado", "cafe", 3), prenda("calzado", "rosa", 3),
    prenda("abrigo", "beige", 5), prenda("abrigo", "negro", 4), prenda("abrigo", "naranja", 4),
    prenda("accesorio", "negro", 1), prenda("accesorio", "cafe", 1),
]


def valido(look):
    return all(por_que_combinan(a["color_principal"], b["color_principal"]) and not se_recargan(a, b)
               for a, b in combinations(look, 2))


r = ca.armar(armario, "mensual", [set()])
por_id = {p["id"]: p for p in armario}
cuenta = {c: sum(p["categoria"] == c for p in r["prendas"]) for c in ca.ESCENARIOS["mensual"]["cuotas"]}
ok(all(cuenta[c] <= n for c, n in ca.ESCENARIOS["mensual"]["cuotas"].items()) and len(r["prendas"]) == 15,
   f"la cápsula del mes respeta las cuotas (15 prendas): {cuenta}")
ok(all(p["estado"] == "disponible" for p in r["prendas"]), "solo prendas disponibles (la de lavado no entra)")
looks = [[por_id[i] for i in look] for look in r["combinaciones"]]
ok(r["looks"] == len(looks) and all(valido(look) and len(look) == 3 for look in looks),
   f"todos los looks son válidos: colores que combinan y sin dos estampados ({r['looks']} looks)")
ok(r["looks"] >= r["looks_greedy"] * (1 - ca.PERDIDA_ACEPTABLE), "la búsqueda local no empeora al greedy (salvo el margen por acentos)")
ok(r["acentos"] >= 2 and r["neutros"] + r["acentos"] == 15, f"equilibra neutros y acentos: {r['neutros']} y {r['acentos']}")
ok(ca.armar(armario, "mensual", [set()])["combinaciones"] == r["combinaciones"], "es determinista: mismo armario, misma cápsula")

frio = ca.armar(armario, "viaje", [{"frio"}, {"frio"}])
ok(frio["con_abrigo"] and all(len(look) == 4 for look in frio["combinaciones"]) and len(frio["prendas"]) <= 10,
   "con frío cada look lleva abrigo y la maleta tiene hasta 10 prendas")
calor = ca.armar(armario, "viaje", [{"calor"}])
ok(not calor["con_abrigo"] and all(por_id[i]["nivel_abrigo"] < 4 for i in {i for look in calor["combinaciones"] for i in look}),
   "con calor no entra ropa abrigada en los looks")
mixto = ca.armar(armario, "viaje", [{"frio"}, {"calor"}])
ok(mixto["con_abrigo"] and any(p["categoria"] == "abrigo" for p in mixto["prendas"]), "un viaje con un día frío lleva abrigo")
poca = ca.armar(armario[:2] + armario[7:9] + armario[12:13], "mensual", [set()])
ok(poca["looks"] < ca.META_LOOKS and poca["sugerencia"], f"sin llegar a la meta dice qué falta: {poca['sugerencia']}")
ok(ca.armar([], "mensual", [set()])["looks"] == 0, "un armario vacío no rompe nada")

# --- La API ---
SENSACION = [(8, 2)] * 16
viaje.consultar = lambda url, parametros: {"daily": {
    "time": [f"2026-12-{d:02d}" for d in range(1, 17)], "temperature_2m_max": [9] * 16, "temperature_2m_min": [3] * 16,
    "apparent_temperature_max": [8] * 16, "apparent_temperature_min": [2] * 16,
    "precipitation_probability_max": [0] * 16, "weather_code": [1] * 16}}

with TestClient(principal.aplicacion) as cliente:
    def cuenta_nueva(correo):
        r = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "contraseña-larga"})
        return {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    h, otra = cuenta_nueva("capsula@prueba.com"), cuenta_nueva("otra-capsula@prueba.com")
    ids = []
    for p in armario[:6] + armario[7:10] + armario[12:15] + armario[16:18]:
        ids.append(cliente.post("/api/prendas", headers=h, data={"categoria": p["categoria"], "color_principal": p["color_principal"],
                                                                 "nivel_abrigo": str(p["nivel_abrigo"]), "estampado": p["estampado"]},
                                files={"imagen": ("p.png", png_de_color(), "image/png")}).json()["id"])

    r = cliente.post("/api/capsulas/generar", headers=h, json={"escenario": "mensual"})
    mes = r.json()
    ok(r.status_code == 200 and mes["looks"] > 0 and mes["detalles"]["ocasion"] == "diario", f"generar la del mes ({mes['looks']} looks)")
    r = cliente.post("/api/capsulas/generar", headers=h, json={"escenario": "viaje", "latitud": 19.29, "longitud": -99.65,
                                                               "lugar": "Toluca", "dias": 3})
    maleta = r.json()
    ok(r.status_code == 200 and maleta["con_abrigo"] and maleta["detalles"]["lugar"] == "Toluca",
       "la maleta usa el pronóstico del destino (frío: con abrigo)")
    ok([d["fecha"] for d in maleta["pronostico"]] == ["2026-12-01", "2026-12-02", "2026-12-03"]
       and all({"maxima_c", "minima_c", "probabilidad_lluvia", "descripcion"} <= d.keys() for d in maleta["pronostico"]),
       "la maleta devuelve el pronóstico de cada día del destino")
    ok(mes["pronostico"] == [], "la cápsula del mes no trae pronóstico por día")
    ok(cliente.post("/api/capsulas/generar", headers=h, json={"escenario": "viaje"}).status_code == 422, "viaje sin destino: 422")
    ok(cliente.post("/api/capsulas/generar", headers=h, json={"escenario": "anual"}).status_code == 422, "escenario desconocido: 422")

    r = cliente.post("/api/capsulas", headers=h, json={"nombre": "Toluca diciembre", "escenario": "viaje",
                                                       "prenda_ids": [p["id"] for p in maleta["prendas"]], "detalles": maleta["detalles"]})
    guardada = r.json()
    ok(r.status_code == 201 and guardada["looks"] == maleta["looks"] and guardada["empacadas"] == [], "guardar la cápsula")
    ok([c["id"] for c in cliente.get("/api/capsulas", headers=h).json()] == [guardada["id"]], "la lista de cápsulas")
    ok(cliente.get(f"/api/capsulas/{guardada['id']}", headers=otra).status_code == 404, "cada quien ve las suyas")
    dos = [p["id"] for p in guardada["prendas"][:2]]
    r = cliente.patch(f"/api/capsulas/{guardada['id']}", headers=h, json={"empacadas": dos + dos})
    ok(r.json()["empacadas"] == sorted(dos), "la checklist marca lo que ya va en la maleta (sin repetir)")
    ok(cliente.patch(f"/api/capsulas/{guardada['id']}", headers=h, json={"empacadas": [9999]}).status_code == 422,
       "solo se marcan prendas de la cápsula")
    ok(cliente.post("/api/capsulas", headers=h, json={"nombre": "x", "escenario": "mensual", "prenda_ids": [ids[0], ids[0]]})
       .status_code == 422, "una cápsula sin prendas repetidas")
    cliente.delete(f"/api/prendas/{dos[0]}", headers=h)
    r = cliente.get(f"/api/capsulas/{guardada['id']}", headers=h).json()
    ok(dos[0] not in r["prenda_ids"] and dos[0] not in r["empacadas"] and len(r["prendas"]) == len(guardada["prendas"]) - 1,
       "borrar una prenda la quita de la cápsula y de la checklist")
    ok(cliente.delete(f"/api/capsulas/{guardada['id']}", headers=h).status_code == 204
       and cliente.get("/api/capsulas", headers=h).json() == [], "borrar la cápsula")
    ok(cliente.post("/api/capsulas/generar", json={"escenario": "mensual"}).status_code == 401, "pide sesión")

terminar()
