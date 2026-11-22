"""Comprueba el rescate de prendas olvidadas (rescate.py): qué cuenta como olvidada, el reto de la semana con 3
propuestas distintas, favoritas, cumplido con "Me lo puse hoy", cambiar, omitir y una semana por usuario.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_rescate.py"""
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi.testclient import TestClient  # noqa: E402
from pruebas.comun import png_de_color  # noqa: E402
from servidor import base_datos, principal, rescate  # noqa: E402

HOY = datetime.now(timezone.utc).date()
dia = lambda atras: (HOY - timedelta(days=atras)).isoformat()  # noqa: E731

# --- 1. Reglas ---
ok(rescate.semana_de(date(2026, 11, 20)) == "2026-W47" and rescate.dias_de_la_semana("2026-W47")[0] == "2026-11-16"
   and len(rescate.dias_de_la_semana("2026-W47")) == 7, "la semana ISO y sus 7 días (de lunes a domingo)")
prenda = lambda i, alta, estado="disponible": {"id": i, "estado": estado, "fecha_creacion": f"{dia(alta)} 10:00:00"}  # noqa: E731
armario = [prenda(1, 300), prenda(2, 300), prenda(3, 5), prenda(4, 300, "en_lavado"), prenda(5, 100)]
usos = {1: {"veces": 3, "ultimo": dia(90)}, 2: {"veces": 9, "ultimo": dia(3)}}
lista = rescate.olvidadas(armario, usos, HOY)
ok([(p["id"], dias, nunca) for p, dias, nunca in lista] == [(5, 100, True), (1, 90, False)],
   "olvidadas: sin uso hace ≥ 60 días o nunca usadas con ≥ 14 días de alta; ni recientes, ni nuevas, ni en lavado")

# --- 2. La API ---
with TestClient(principal.aplicacion) as cliente:
    def cuenta(correo):
        r = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "contraseña-larga"})
        return {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    h, otra = cuenta("rescate@prueba.com"), cuenta("otra-rescate@prueba.com")

    def subir(categoria, color, alta_hace=200, estampado="liso"):
        p = cliente.post("/api/prendas", headers=h, data={"categoria": categoria, "color_principal": color, "nivel_abrigo": "2",
                                                          "estampado": estampado},
                         files={"imagen": ("p.png", png_de_color(), "image/png")}).json()
        base_datos.bd().prendas.update_one({"_id": p["id"]}, {"$set": {"fecha_creacion": datetime.now(timezone.utc) - timedelta(days=alta_hace)}})
        return p["id"]

    olvidada = subir("parte_superior", "rojo")  # nunca usada en 200 días: la más olvidada
    otra_olvidada = subir("parte_superior", "verde", alta_hace=150)
    diaria = subir("parte_superior", "blanco")
    abajos = [subir("parte_inferior", c) for c in ("negro", "mezclilla", "beige", "gris")]
    zapatos = [subir("calzado", c) for c in ("negro", "blanco", "cafe")]
    for atras in range(1, 8):  # las favoritas: lo que se usa a diario
        cliente.post("/api/usos", headers=h, json={"prenda_ids": [diaria, abajos[0], zapatos[0]], "fecha": dia(atras)})
    for prenda_id in abajos[1:] + zapatos[1:]:
        cliente.post("/api/usos", headers=h, json={"prenda_ids": [prenda_id], "fecha": dia(20 + prenda_id % 10)})

    ok(cliente.get("/api/reto", headers=otra).json() is None, "sin prendas olvidadas no hay reto")
    r = cliente.get("/api/reto", headers=h, params={"fecha": HOY.isoformat()})
    reto = r.json()
    ok(r.status_code == 200 and reto["prenda"]["id"] == olvidada and reto["nunca_usada"] and reto["dias_sin_usar"] == 200,
       f"el reto es la más olvidada ({reto['prenda']['color_principal']}, {reto['dias_sin_usar']} días)")
    ok(len(reto["propuestas"]) == 3 and all(p["elementos"][0]["prenda"]["id"] == olvidada for p in reto["propuestas"]),
       "3 propuestas, todas con la olvidada")
    claves = [frozenset(e["prenda"]["id"] for e in p["elementos"] if e["rol"] in ("parte_inferior", "calzado")) for p in reto["propuestas"]]
    ok(len(set(claves)) == 3, "las 3 cambian la parte de abajo o el calzado")
    ids_primera = {e["prenda"]["id"] for e in reto["propuestas"][0]["elementos"]}
    ok(abajos[0] in ids_primera or zapatos[0] in ids_primera, "la primera propuesta usa tus favoritas (lo que más te pones)")
    ok(not reto["cumplido"] and reto["estado"] == "activo" and reto["cambios_restantes"] == 2, "recién creado: activo y sin cumplir")
    ok(cliente.get("/api/reto", headers=h, params={"fecha": HOY.isoformat()}).json()["prenda"]["id"] == olvidada
       and base_datos.bd().retos.count_documents({}) == 1, "un solo reto por semana: pedirlo otra vez da el mismo")

    look = [e["prenda"]["id"] for e in reto["propuestas"][1]["elementos"]]
    cliente.post("/api/usos", headers=h, json={"prenda_ids": look, "fecha": HOY.isoformat()})
    ok(cliente.get("/api/reto", headers=h, params={"fecha": HOY.isoformat()}).json()["cumplido"],
       "ponerte una propuesta («Me lo puse hoy») cumple el reto")
    cliente.delete(f"/api/usos/{HOY.isoformat()}", headers=h)

    r = cliente.post("/api/reto/cambiar", headers=h, params={"fecha": HOY.isoformat()})
    ok(r.status_code == 200 and r.json()["prenda"]["id"] == otra_olvidada and r.json()["cambios_restantes"] == 1,
       "cambiar da la siguiente olvidada")
    ok(cliente.post("/api/reto/cambiar", headers=h, params={"fecha": HOY.isoformat()}).status_code == 404,
       "si ya no hay otra olvidada, 404 (la que se cambió no vuelve)")
    r = cliente.post("/api/reto/omitir", headers=h, params={"fecha": HOY.isoformat()})
    ok(r.json()["estado"] == "omitido", "«Ahora no» deja el reto omitido esta semana")

    proxima = (HOY + timedelta(days=7)).isoformat()
    r = cliente.get("/api/reto", headers=h, params={"fecha": proxima}).json()
    ok(r is not None and r["semana"] != reto["semana"] and r["prenda"]["id"] not in (olvidada, otra_olvidada)
       or r is None, "la semana siguiente no repite las prendas de las últimas semanas")

    cliente.patch(f"/api/prendas/{otra_olvidada}/estado", headers=h, json={"estado": "archivada"})
    base_datos.bd().retos.delete_many({})
    r = cliente.get("/api/reto", headers=h, params={"fecha": HOY.isoformat()}).json()
    ok(r["prenda"]["id"] == olvidada, "una prenda archivada no se rescata")
    cliente.delete(f"/api/prendas/{olvidada}", headers=h)
    r = cliente.get("/api/reto", headers=h, params={"fecha": HOY.isoformat()})
    ok(r.status_code == 200 and (r.json() is None or r.json()["prenda"]["id"] != olvidada),
       "si borras la prenda del reto, se cambia sola (o no hay reto)")
    ok(cliente.post("/api/reto/omitir", headers=otra).status_code == 404, "omitir sin reto: 404")
    ok(cliente.get("/api/reto").status_code == 401, "pide sesión")

terminar()
