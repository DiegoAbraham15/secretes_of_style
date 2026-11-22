"""Comprueba "Me lo puse hoy" (colección usos), el look del día y lo que se usa en las estadísticas.
El clima se simula: las pruebas no salen a internet.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_uso.py"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi.testclient import TestClient  # noqa: E402
from pruebas.comun import png_de_color  # noqa: E402
from servidor import base_datos, principal  # noqa: E402
from servidor.aprendizaje import firma_de  # noqa: E402

principal.obtener_clima = lambda lat, lon: {"temperatura_c": 20, "sensacion_termica_c": 20, "probabilidad_lluvia": 0,
                                            "descripcion": "Despejado", "hechos": [], "deducciones": []}
HOY = datetime.now(timezone.utc).date()


def dia(atras: int) -> str:
    return (HOY - timedelta(days=atras)).isoformat()


with TestClient(principal.aplicacion) as cliente:
    def cuenta(correo):
        r = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "contraseña-larga"})
        return {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    h, otra = cuenta("uso@prueba.com"), cuenta("otra-uso@prueba.com")

    def subir(categoria, color, abrigo="2", encabezados=h):
        datos = {"categoria": categoria, "color_principal": color, "nivel_abrigo": abrigo}
        return cliente.post("/api/prendas", headers=encabezados, data=datos,
                            files={"imagen": ("p.png", png_de_color(120, 120, 120, 8), "image/png")}).json()["id"]

    arribas = [subir("parte_superior", "gris"), subir("parte_superior", "blanco"), subir("parte_superior", "negro")]
    abajos = [subir("parte_inferior", "mezclilla"), subir("parte_inferior", "negro")]
    zapatos = subir("calzado", "negro")
    ajena = subir("parte_superior", "gris", encabezados=otra)
    lugar = {"latitud": 19.4, "longitud": -99.1}

    # --- 1. Look del día ---
    r = cliente.post("/api/recomendaciones/dia", headers=h, json={**lugar, "fecha": HOY.isoformat()})
    hoy = r.json()
    ok(r.status_code == 200 and hoy["del_dia"] and hoy["prenda_base"] is None and len(hoy["sugerencias"]) == 1,
       "el look del día responde como las recomendaciones, con una sola sugerencia")
    look = hoy["sugerencias"][0]
    ids = [e["prenda"]["id"] for e in look["elementos"]]
    ok({e["prenda"]["categoria"] for e in look["elementos"]} >= {"parte_superior", "parte_inferior", "calzado"},
       "es un look completo sin elegir prenda base")
    ok(look["elementos"][0]["prenda"]["categoria"] == "parte_superior", "la base es una parte de arriba")
    voto = base_datos.bd().votos_atuendo.find_one({"firma": firma_de(ids)})
    ok(voto and voto["me_gusta"] == -1, "como los demás looks, sin corazón cuenta como que no gustó")
    ok(cliente.post("/api/recomendaciones/dia", json=lugar).status_code == 401, "pide sesión")
    ok(cliente.post("/api/recomendaciones/dia", headers=h, json={**lugar, "ocasion": "fiesta"}).status_code == 422, "ocasión desconocida: 422")
    ok(cliente.post("/api/recomendaciones/dia", headers=h, json={**lugar, "fecha": "20-11-2026"}).status_code == 422, "fecha mal escrita: 422")
    vacia = cliente.post("/api/recomendaciones/dia", headers=otra, json=lugar).json()
    ok(vacia["sugerencias"] == [] and vacia["avisos"], "sin un look completo, ninguna sugerencia y un aviso")

    # --- 2. Me lo puse ---
    r = cliente.post("/api/usos", headers=h, json={"prenda_ids": ids, "fecha": dia(1)})
    uso = r.json()
    ok(r.status_code == 201 and uso["fecha"] == dia(1) and sorted(e["prenda"]["id"] for e in uso["elementos"]) == sorted(ids),
       "registra lo que se puso ayer")
    ok([e["rol"] for e in uso["elementos"]][:3] == ["parte_superior", "parte_inferior", "calzado"], "las prendas van en orden del cuerpo")
    ok(base_datos.bd().votos_atuendo.find_one({"firma": firma_de(ids)})["me_gusta"] == 1, "ponérselo cuenta como corazón")

    otro = cliente.post("/api/recomendaciones/dia", headers=h, json={**lugar, "fecha": HOY.isoformat()}).json()["sugerencias"][0]
    ok(otro["elementos"][0]["prenda"]["id"] != ids[0], "hoy no propone la misma parte de arriba que ayer")

    cliente.post("/api/usos", headers=h, json={"prenda_ids": [arribas[1], abajos[1], zapatos], "fecha": dia(1)})
    ok(base_datos.bd().usos.count_documents({"fecha": dia(1)}) == 1, "volver a registrar el mismo día lo reemplaza")
    ok(cliente.post("/api/usos", headers=h, json={"prenda_ids": [arribas[0]], "fecha": dia(-5)}).status_code == 422,
       "un día que no ha llegado: 422")
    ok(cliente.post("/api/usos", headers=h, json={"prenda_ids": [ajena]}).status_code == 404, "no se registra ropa ajena")
    ok(cliente.post("/api/usos", headers=h, json={"prenda_ids": [zapatos, zapatos]}).status_code == 422, "prendas repetidas: 422")
    ok(cliente.post("/api/usos", headers=h, json={"prenda_ids": []}).status_code == 422, "sin prendas: 422")
    ok(cliente.post("/api/usos", json={"prenda_ids": [zapatos]}).status_code == 401, "pide sesión")
    r = cliente.post("/api/usos", headers=h, json={"prenda_ids": [arribas[2]]})
    ok(r.status_code == 201 and r.json()["fecha"] == HOY.isoformat(), "sin fecha registra hoy (y una sola prenda también vale)")

    # --- 3. La lista ---
    for atras in (10, 20, 40):
        cliente.post("/api/usos", headers=h, json={"prenda_ids": [arribas[2], abajos[1]], "fecha": dia(atras)})
    lista = cliente.get("/api/usos", headers=h).json()
    ok([u["fecha"] for u in lista] == [dia(0), dia(1), dia(10), dia(20), dia(40)], "del día más reciente al más viejo")
    ok([u["fecha"] for u in cliente.get("/api/usos", headers=h, params={"desde": dia(1)}).json()] == [dia(0), dia(1)],
       "con desde, solo de ese día en adelante")
    ok(cliente.get("/api/usos", headers=otra).json() == [], "cada quien ve solo lo suyo")
    ok(cliente.delete(f"/api/usos/{dia(40)}", headers=otra).status_code == 404, "no se borra lo ajeno")
    ok(cliente.delete(f"/api/usos/{dia(40)}", headers=h).status_code == 204, "deshacer un día")
    ok(cliente.delete(f"/api/usos/{dia(40)}", headers=h).status_code == 404, "deshacerlo otra vez: 404")

    # --- 4. Estadísticas ---
    uso = cliente.get("/api/estadisticas", headers=h, params={"fecha": HOY.isoformat()}).json()["uso"]
    ok(uso["dias_registrados"] == 4 and not uso["listo"], f"4 días en los últimos 30 (el de hace 40 no cuenta): {uso['dias_registrados']}")
    ok(uso["mas_usadas"][0] == {"prenda": uso["mas_usadas"][0]["prenda"], "veces": 3}
       and uso["mas_usadas"][0]["prenda"]["id"] == arribas[2], "la más usada va primero, con sus veces")
    ok({p["id"] for p in uso["sin_usar"]} == {arribas[0], abajos[0]}, "las que no te pusiste")
    ok(uso["porcentaje_usado"] == round(100 * 4 / 6), f"porcentaje del armario usado: {uso['porcentaje_usado']}")
    cliente.patch(f"/api/prendas/{arribas[0]}/estado", headers=h, json={"estado": "archivada"})
    uso = cliente.get("/api/estadisticas", headers=h, params={"fecha": HOY.isoformat()}).json()["uso"]
    ok({p["id"] for p in uso["sin_usar"]} == {abajos[0]} and uso["porcentaje_usado"] == 80, "las archivadas no cuentan")
    cliente.post("/api/usos", headers=h, json={"prenda_ids": [zapatos], "fecha": dia(2)})
    ok(cliente.get("/api/estadisticas", headers=h).json()["uso"]["listo"], "con 5 días ya se muestra lo que no usas")
    ok(cliente.get("/api/estadisticas", headers=otra).json()["uso"]["dias_registrados"] == 0, "otra cuenta empieza en cero")

    # --- 5. Borrar una prenda ---
    cliente.delete(f"/api/prendas/{zapatos}", headers=h)
    ok(base_datos.bd().usos.count_documents({"prenda_ids": zapatos}) == 0, "borrar una prenda la quita de los días en que se usó")
    ok(base_datos.bd().usos.count_documents({"fecha": dia(2)}) == 0, "un día que se quedó sin prendas se borra")
    ok(base_datos.bd().usos.count_documents({"fecha": dia(1)}) == 1, "los demás días se quedan")

terminar()
