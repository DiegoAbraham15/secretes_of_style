"""Comprueba "¿Vale la pena comprarla?" (compra.py): cuántos looks arma una prenda de la tienda con tu ropa.
La IA de visión se simula: las pruebas no necesitan Ollama.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_compra.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi.testclient import TestClient  # noqa: E402
from pruebas.comun import png_de_color  # noqa: E402
from servidor import base_datos, compra, principal  # noqa: E402

# --- 1. La prenda de la foto ---
deseo = {"url_imagen": "/archivos/deseos/x.png", "detectado": {
    "categoria": "abrigo", "subcategoria": "Chamarra", "color_principal": "cafe", "estampado": "liso", "estilo": "casual"}}
prenda = compra.prenda_del_deseo(deseo)
ok(prenda["id"] == 0 and prenda["estado"] == "disponible" and prenda["url_imagen"] == deseo["url_imagen"],
   "la foto se vuelve una prenda virtual disponible, con id 0 y la foto de la tienda")
ok(prenda["nivel_abrigo"] == compra.ABRIGO_TIPICO["abrigo"] and prenda["impermeable"] is False,
   "si la IA no dijo el abrigo (deseos anteriores), usa el típico de la categoría")
deseo["detectado"]["nivel_abrigo"] = 5
ok(compra.prenda_del_deseo(deseo)["nivel_abrigo"] == 5, "si lo dijo, usa el de la IA")
ok(compra.prenda_del_deseo({"url_imagen": "x", "detectado": None}) is None, "sin lo que vio la IA no se puede calcular")
ok(compra.prenda_del_deseo({"url_imagen": "x", "detectado": {"categoria": "sombrero", "color_principal": "rojo"}}) is None,
   "una categoría fuera del catálogo tampoco")

# --- 2. El veredicto ---
ok(compra.veredicto(0, 4, 0, "calzado", ["calzado"])[0] == "no_combina", "ningún look: no combina")
ok("No tienes una parte de abajo ni un par de zapatos" in compra.veredicto(0, None, 0, "abrigo", ["parte_inferior", "calzado"])[1], "y dice qué falta")
tipo, frase = compra.veredicto(6, 6, 2, "parte_superior", [])
ok(tipo == "piensalo" and "2 partes de arriba parecidas" in frase, f"con parecidas, piénsalo: {frase}")
ok("1 par de zapatos parecido" in compra.veredicto(3, 2, 1, "calzado", [])[1], "concuerda en singular y masculino")
ok(compra.veredicto(8, 5.5, 0, "parte_inferior", [])[0] == "vale_la_pena", "más looks que el promedio: vale la pena")
ok(compra.veredicto(2, 5.5, 0, "parte_inferior", [])[0] == "piensalo", "menos looks que el promedio: piénsalo")
ok(compra.veredicto(4, None, 0, "abrigo", [])[0] == "vale_la_pena", "una categoría que no tienes: llena un hueco")
ok(f"{compra.LOOKS_MAXIMOS} o más" in compra.veredicto(compra.LOOKS_MAXIMOS, 10, 0, "abrigo", [])[1], "con el tope dice «500 o más»")

# --- 3. La API ---
visto = {}
principal.detectar_para_tienda = lambda contenido: visto

with TestClient(principal.aplicacion) as cliente:
    def cuenta(correo):
        r = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "contraseña-larga"})
        return {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    h, otra = cuenta("compra@prueba.com"), cuenta("otra-compra@prueba.com")

    def subir(categoria, color, encabezados=h):
        datos = {"categoria": categoria, "color_principal": color, "nivel_abrigo": "2"}
        return cliente.post("/api/prendas", headers=encabezados, data=datos,
                            files={"imagen": ("p.png", png_de_color(120, 120, 120, 8), "image/png")}).json()["id"]

    def desear(categoria, color, encabezados=h):
        visto.clear()
        visto.update({"categoria": categoria, "subcategoria": None, "color_principal": color, "estampado": "liso",
                      "estilo": "casual", "nivel_abrigo": 2, "impermeable": False})
        return cliente.post("/api/deseos", headers=encabezados,
                            files={"imagen": ("t.png", png_de_color(10, 10, 200, 8), "image/png")}).json()

    gris, blanca = subir("parte_superior", "gris"), subir("parte_superior", "blanco")
    subir("parte_inferior", "mezclilla"), subir("parte_inferior", "negro"), subir("parte_inferior", "rojo")
    subir("calzado", "negro"), subir("calzado", "blanco")
    subir("parte_superior", "verde", encabezados=otra)

    nueva = desear("parte_superior", "azul_marino")
    ok(nueva["detectado"]["nivel_abrigo"] == 2, "el deseo ahora guarda también el abrigo que vio la IA")
    votos_antes = base_datos.bd().votos_atuendo.count_documents({})
    prendas_antes = base_datos.bd().prendas.count_documents({})
    r = cliente.get(f"/api/deseos/{nueva['id']}/vale-la-pena", headers=h)
    a = r.json()
    ok(r.status_code == 200 and a["looks"] == 6 and not a["looks_tope"], f"una parte de arriba neutra: 3 de abajo × 2 zapatos = {a.get('looks')}")
    ok(a["comparadas"] == 2 and a["promedio_categoria"] is not None, f"se compara con tus 2 partes de arriba (promedio {a['promedio_categoria']})")
    ok(a["parecidas"] == [] and a["veredicto"] == "vale_la_pena", f"sin parecidas y arriba del promedio: {a['mensaje']}")
    ok(a["combina_con"] == 5 and a["otras_prendas"] == 5, "combina con las 5 prendas de otras categorías")
    ok(len(a["ejemplos"]) == compra.EJEMPLOS and all(s["elementos"][0]["prenda"]["id"] == 0 for s in a["ejemplos"]),
       "dos ejemplos, con la prenda de la tienda como base")
    ok(a["ejemplos"][0]["elementos"][0]["prenda"]["url_imagen"] == nueva["url_imagen"], "el ejemplo muestra la foto de la tienda")
    ok(base_datos.bd().votos_atuendo.count_documents({}) == votos_antes, "no cuenta como voto")
    ok(base_datos.bd().prendas.count_documents({}) == prendas_antes, "no agrega nada al armario")

    igual = desear("parte_superior", "gris")
    a = cliente.get(f"/api/deseos/{igual['id']}/vale-la-pena", headers=h).json()
    ok(a["veredicto"] == "piensalo" and [p["id"] for p in a["parecidas"]] == [gris], f"ya tienes una gris: {a['mensaje']}")

    azul = desear("parte_superior", "azul")
    a = cliente.get(f"/api/deseos/{azul['id']}/vale-la-pena", headers=h).json()
    ok(a["looks"] < a["promedio_categoria"] and a["veredicto"] == "piensalo",
       f"azul: no va con el pantalón rojo, arma menos que el promedio ({a['looks']} vs {a['promedio_categoria']})")

    a = cliente.get(f"/api/deseos/{desear('abrigo', 'beige')['id']}/vale-la-pena", headers=h).json()
    ok(a["veredicto"] == "vale_la_pena" and a["promedio_categoria"] is None and a["looks"] > 0,
       f"un abrigo, que no tienes: llena un hueco ({a['looks']} looks)")

    sola = desear("parte_superior", "negro", encabezados=otra)
    a = cliente.get(f"/api/deseos/{sola['id']}/vale-la-pena", headers=otra).json()
    ok(a["veredicto"] == "no_combina" and set(a["faltantes"]) == {"parte_inferior", "calzado"} and a["ejemplos"] == [],
       "sin pantalones ni zapatos no arma nada y dice qué falta")

    principal.detectar_para_tienda = lambda contenido: (_ for _ in ()).throw(principal.HTTPException(503, "Ollama apagado"))
    sin_ia = cliente.post("/api/deseos", headers=h, files={"imagen": ("t.png", png_de_color(), "image/png")}).json()
    ok(cliente.get(f"/api/deseos/{sin_ia['id']}/vale-la-pena", headers=h).status_code == 422, "si la IA no vio la prenda: 422")
    ok(cliente.get(f"/api/deseos/{nueva['id']}/vale-la-pena", headers=otra).status_code == 404, "no se calcula lo ajeno")
    ok(cliente.get(f"/api/deseos/{nueva['id']}/vale-la-pena").status_code == 401, "pide sesión")

terminar()
