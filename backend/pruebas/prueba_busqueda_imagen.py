"""Comprueba la búsqueda por imagen (busqueda_imagen.py): la prenda exacta en tiendas y las parecidas.
Google Cloud Vision y la IA local se simulan: las pruebas no salen a internet ni necesitan clave.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_busqueda_imagen.py"""
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()
os.environ.pop("GOOGLE_VISION_CLAVE", None)

from fastapi.testclient import TestClient  # noqa: E402
from pruebas.comun import png_de_color  # noqa: E402
from servidor import base_datos, busqueda_imagen as bi, principal  # noqa: E402

RESPUESTA = {"responses": [{"webDetection": {
    "bestGuessLabels": [{"label": "tom and jerry sweatshirt", "languageCode": "en"}],
    "pagesWithMatchingImages": [
        {"url": "https://www.pinterest.com/pin/123", "pageTitle": "Pin", "fullMatchingImages": [{"url": "https://i.pinimg.com/a.jpg"}]},
        {"url": "https://blog.ejemplo.com/moda", "pageTitle": "Mi blog", "partialMatchingImages": [{"url": "https://blog.ejemplo.com/b.jpg"}]},
        {"url": "https://www.amazon.com/dp/X1", "pageTitle": "<b>Tom and Jerry</b> Sweatshirt",
         "partialMatchingImages": [{"url": "https://m.media-amazon.com/x.jpg"}]},
        {"url": "https://articulo.mercadolibre.com.mx/MLM-1", "pageTitle": "Sudadera <b>Tom Y Jerry</b> &amp; Amigos",
         "fullMatchingImages": [{"url": "https://http2.mlstatic.com/D_1.jpg"}]},
        {"url": "javascript:alert(1)", "pageTitle": "malo"},
        {"url": "https://articulo.mercadolibre.com.mx/MLM-1", "pageTitle": "repetida"},
    ],
    "visuallySimilarImages": [
        {"url": "https://http2.mlstatic.com/D_2.jpg"}, {"url": "https://i.pinimg.com/c.jpg"},
        {"url": "https://tienda.ejemplo.mx/d.png"}, {"url": "ftp://raro/e.jpg"},
    ],
}}]}
pedidas = []


def vision_falsa(cuerpo, clave):
    pedidas.append((cuerpo, clave))
    return RESPUESTA


bi.consultar_vision = vision_falsa

# --- 1. Lo que se arma con la respuesta de Google ---
ok(bi.buscar_por_imagen(b"foto") is None and not bi.activa() and pedidas == [], "sin clave no se manda nada a Google")
os.environ["GOOGLE_VISION_CLAVE"] = "clave-de-prueba"
r = bi.buscar_por_imagen(b"foto")
cuerpo, clave = pedidas[-1]
ok(bi.activa() and clave == "clave-de-prueba" and cuerpo["requests"][0]["features"][0]["type"] == "WEB_DETECTION",
   "con clave pide la detección web")
ok(cuerpo["requests"][0]["image"]["content"] == "Zm90bw==", "manda la foto en base64")
exactas = r["exactas"]
ok([e["tienda"] for e in exactas] == ["Mercado Libre", "Amazon", "blog.ejemplo.com"],
   f"tiendas primero (las de México antes), luego otras páginas: {[e['tienda'] for e in exactas]}")
ok(exactas[0]["titulo"] == "Sudadera Tom Y Jerry & Amigos" and exactas[0]["misma_foto"] and exactas[0]["es_tienda"],
   "título sin etiquetas ni entidades HTML; marca si la foto coincide completa")
ok(exactas[0]["imagen"] == "https://http2.mlstatic.com/D_1.jpg" and exactas[1]["imagen"] == "https://m.media-amazon.com/x.jpg",
   "cada resultado trae su imagen para la vista previa")
ok(not any("pinterest" in e["url"] for e in exactas), "sin redes sociales: ahí no se compra")
ok(len({e["url"] for e in exactas}) == len(exactas) and all(e["url"].startswith("https://") for e in exactas),
   "sin repetidas ni links raros (javascript:)")
parecidas = r["parecidas"]
ok([p["imagen"] for p in parecidas] == ["https://http2.mlstatic.com/D_2.jpg", "https://tienda.ejemplo.mx/d.png"],
   "parecidas sin redes sociales ni links raros")
ok(parecidas[0]["tienda"] == "Mercado Libre" and parecidas[1]["tienda"] is None, "la tienda de la imagen, si se sabe")
ok(all(p["url"] is None for p in parecidas), "las parecidas no traen página: solo su vista previa, sin Google Lens")
ok(r["etiqueta"] == "tom and jerry sweatshirt" and r["fecha"] is not None, "cómo la llama Google y cuándo se buscó")

bi.consultar_vision = lambda c, k: {"responses": [{"error": {"code": 7, "message": "API sin habilitar"}}]}
try:
    bi.buscar_por_imagen(b"foto")
    ok(False, "un error de Google avisa")
except bi.ErrorDeBusqueda as e:
    ok("API sin habilitar" in str(e), "un error de Google avisa con su mensaje")


def sin_red(c, k):
    raise urllib.error.URLError("sin red")


bi.consultar_vision = sin_red
try:
    bi.buscar_por_imagen(b"foto")
    ok(False, "sin internet avisa")
except bi.ErrorDeBusqueda as e:
    ok("internet" in str(e), "sin internet avisa")

# --- 2. La API ---
principal.detectar_para_tienda = lambda contenido: {
    "categoria": "parte_superior", "subcategoria": "Sudadera", "color_principal": "azul_marino", "estampado": "otro",
    "estilo": "urbano", "nivel_abrigo": 4, "impermeable": False, "marca": None, "detalles": "Tom y Jerry"}
foto = {"imagen": ("t.png", png_de_color(20, 20, 90, 16), "image/png")}

with TestClient(principal.aplicacion) as cliente:
    def cuenta(correo):
        r = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "contraseña-larga"})
        return {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    h, otra = cuenta("imagen@prueba.com"), cuenta("otra-imagen@prueba.com")

    bi.consultar_vision = vision_falsa
    r = cliente.post("/api/deseos", headers=h, files=foto)
    deseo = r.json()
    ok(r.status_code == 201 and deseo["por_imagen"] and deseo["aviso_imagen"] is None, "al tomar la foto también busca en internet")
    ok(len(deseo["imagen_web"]["exactas"]) == 3 and deseo["imagen_web"]["exactas"][0]["tienda"] == "Mercado Libre",
       "la respuesta trae las vistas previas de la misma prenda")
    ok(isinstance(deseo["imagen_web"]["fecha"], str) and len(deseo["imagen_web"]["fecha"]) == 19, "la fecha va como texto")
    ok(deseo["busqueda"] == "Sudadera Tom y Jerry azul marino", "y la IA local sigue armando la búsqueda por texto")
    guardado = base_datos.bd().deseos.find_one({"_id": deseo["id"]})
    ok(len(guardado["imagen_web"]["parecidas"]) == 2, "se guarda: ver la lista no gasta búsquedas de Google")
    ok(cliente.get("/api/deseos", headers=h).json()[0]["imagen_web"]["exactas"][1]["tienda"] == "Amazon", "la lista las trae")

    bi.consultar_vision = sin_red
    r = cliente.post("/api/deseos", headers=h, files=foto)
    ok(r.status_code == 201 and r.json()["imagen_web"] is None and "internet" in r.json()["aviso_imagen"],
       "si Google falla, la prenda igual se guarda y avisa")
    fallida = r.json()
    ok(cliente.post(f"/api/deseos/{fallida['id']}/buscar-por-imagen", headers=h).status_code == 502, "reintentar sin red: 502")
    bi.consultar_vision = vision_falsa
    r = cliente.post(f"/api/deseos/{fallida['id']}/buscar-por-imagen", headers=h)
    ok(r.status_code == 200 and len(r.json()["imagen_web"]["exactas"]) == 3, "reintentar con red la encuentra y la guarda")
    ok(cliente.post(f"/api/deseos/{fallida['id']}/buscar-por-imagen", headers=otra).status_code == 404, "no se busca lo ajeno")
    ok(cliente.post(f"/api/deseos/{fallida['id']}/buscar-por-imagen").status_code == 401, "pide sesión")

    os.environ.pop("GOOGLE_VISION_CLAVE")
    antes = len(pedidas)
    r = cliente.post("/api/deseos", headers=h, files=foto)
    ok(r.status_code == 201 and r.json()["imagen_web"] is None and r.json()["aviso_imagen"] is None
       and not r.json()["por_imagen"] and len(pedidas) == antes, "sin clave todo sigue como antes y no se manda la foto")
    ok(cliente.post(f"/api/deseos/{r.json()['id']}/buscar-por-imagen", headers=h).status_code == 503,
       "buscar por imagen sin clave: 503 con el aviso de qué falta")

terminar()
