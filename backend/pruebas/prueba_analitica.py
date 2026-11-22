"""Comprueba la analítica real de uso: veces usada y última vez por prenda, costo por puesta, aprovechamiento a 30 y
90 días y el semáforo de rotación. Las fechas se controlan escribiendo directo en la base.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_analitica.py"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi.testclient import TestClient  # noqa: E402
from pruebas.comun import png_de_color  # noqa: E402
from servidor import base_datos, principal  # noqa: E402

HOY = datetime.now(timezone.utc).date()
dia = lambda atras: (HOY - timedelta(days=atras)).isoformat()  # noqa: E731

with TestClient(principal.aplicacion) as cliente:
    def cuenta(correo):
        r = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "contraseña-larga"})
        return {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    h, otra = cuenta("analitica@prueba.com"), cuenta("otra-analitica@prueba.com")

    def subir(categoria, color, alta_hace=120, precio=None):
        prenda = cliente.post("/api/prendas", headers=h, data={"categoria": categoria, "color_principal": color, "nivel_abrigo": "2"},
                              files={"imagen": ("p.png", png_de_color(), "image/png")}).json()
        base_datos.bd().prendas.update_one({"_id": prenda["id"]}, {"$set": {
            "fecha_creacion": datetime.now(timezone.utc) - timedelta(days=alta_hace)}})
        if precio is not None:
            cliente.patch(f"/api/prendas/{prenda['id']}", headers=h, json={"precio_compra": precio})
        return prenda["id"]

    diaria = subir("parte_superior", "negro", precio=200)  # se usa mucho: la más rentable
    jeans = subir("parte_inferior", "mezclilla", precio=900)
    poco = subir("parte_superior", "blanco", precio=600)  # usada hace 45 días
    olvidada = subir("calzado", "negro", precio=1500)  # usada hace 120 días: candidata
    nueva = subir("abrigo", "beige", alta_hace=10)  # sin uso pero recién dada de alta
    vieja_sin_uso = subir("accesorio", "cafe", alta_hace=200)  # nunca usada en 200 días: candidata
    archivada = subir("parte_inferior", "negro", precio=300)
    cliente.patch(f"/api/prendas/{archivada}/estado", headers=h, json={"estado": "archivada"})

    for atras in range(0, 10):
        cliente.post("/api/usos", headers=h, json={"prenda_ids": [diaria, jeans] if atras % 2 else [diaria], "fecha": dia(atras)})
    cliente.post("/api/usos", headers=h, json={"prenda_ids": [poco, jeans], "fecha": dia(45)})
    cliente.post("/api/usos", headers=h, json={"prenda_ids": [olvidada], "fecha": dia(120)})

    # --- Por prenda ---
    r = cliente.get(f"/api/prendas/{diaria}", headers=h).json()
    ok(r["uso"] == {"veces": 10, "ultimo": dia(0), "dias_sin_usar": 0} and r["costo_por_uso"] == 20.0, f"veces, última vez y $ por puesta: {r['uso']}, {r['costo_por_uso']}")
    r = cliente.get(f"/api/prendas/{nueva}", headers=h).json()
    ok(r["uso"] == {"veces": 0, "ultimo": None, "dias_sin_usar": None} and r["costo_por_uso"] is None, "sin uso ni precio")
    lista = {p["id"]: p for p in cliente.get("/api/prendas", headers=h).json()}
    ok(lista[jeans]["uso"]["veces"] == 6 and lista[olvidada]["uso"]["ultimo"] == dia(120), "la lista también trae el uso")
    cliente.delete(f"/api/usos/{dia(0)}", headers=h)
    ok(cliente.get(f"/api/prendas/{diaria}", headers=h).json()["uso"]["veces"] == 9, "deshacer un día se nota al instante")

    # --- Estadísticas ---
    a = cliente.get("/api/estadisticas", headers=h, params={"fecha": HOY.isoformat()}).json()["analitica"]
    ok(a["aprovechamiento"] == {"30": round(100 * 2 / 6), "90": round(100 * 3 / 6)},
       f"aprovechamiento a 30 y 90 días (6 activas, sin la archivada): {a['aprovechamiento']}")
    ids = lambda grupo: {f["prenda"]["id"] for f in a["rotacion"][grupo]}  # noqa: E731
    ok(ids("activas") == {diaria, jeans} and ids("poco_usadas") == {poco}, "activas (≤ 30 días) y poco usadas (≤ 90)")
    ok(ids("nuevas") == {nueva} and ids("candidatas") == {olvidada, vieja_sin_uso}, "nuevas sin uso y candidatas a donar o vender")
    ok([f["prenda"]["id"] for f in a["rotacion"]["candidatas"]] == [vieja_sin_uso, olvidada]
       and a["rotacion"]["candidatas"][1]["dias_sin_usar"] == 120,
       "candidatas de la más olvidada a la menos (nunca usada en 200 días antes que usada hace 120)")
    cpu = a["costo_por_uso"]
    ok(cpu["prendas_con_precio"] == 4 and cpu["invertido"] == 3200, f"invertido en las prendas con precio: {cpu['invertido']}")
    ok([f["prenda"]["id"] for f in cpu["mas_rentables"]] == [diaria, jeans, poco, olvidada]
       and cpu["mas_rentables"][0]["costo_por_uso"] == round(200 / 9, 2), "las más rentables: menos $ por puesta")
    ok(cpu["menos_amortizadas"][0]["prenda"]["id"] == olvidada and cpu["menos_amortizadas"][0]["costo_por_uso"] == 1500,
       "la menos amortizada: cara y casi sin usar")
    vacia = cliente.get("/api/estadisticas", headers=otra).json()["analitica"]
    ok(vacia["aprovechamiento"] == {"30": 0, "90": 0} and vacia["costo_por_uso"]["prendas_con_precio"] == 0
       and all(v == [] for v in vacia["rotacion"].values()), "un armario vacío no rompe nada")

terminar()
