"""Comprueba la digitalización sin fricción (digitalizar.py): borradores con IA y sin fondo, color dominante,
temporada, duplicados, importar desde un link (con protección SSRF) y la edición completa de una prenda.
La IA, el motor y la red se simulan. Ejecutar desde backend: .venv\\Scripts\\python pruebas\\prueba_digitalizar.py"""
import io
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from pruebas.comun import png_de_color  # noqa: E402
from servidor import base_datos, digitalizar as dg, principal  # noqa: E402
from servidor.archivos import ruta_de  # noqa: E402


def foto(fondo=(240, 240, 240), prenda=(200, 30, 30), lado=120, transparente=False) -> bytes:
    """Una "prenda" (cuadro de color) en el centro, sobre fondo liso o transparente."""
    imagen = Image.new("RGBA", (lado, lado), (*fondo, 0 if transparente else 255))
    for x in range(lado // 4, 3 * lado // 4):
        for y in range(lado // 4, 3 * lado // 4):
            imagen.putpixel((x, y), (*prenda, 255))
    salida = io.BytesIO()
    imagen.save(salida, "PNG")
    return salida.getvalue()


# --- 1. Medir la foto ---
ok([dg.temporada_de(n) for n in (1, 2, 3, 4, 5, None)] ==
   ["primavera_verano", "primavera_verano", "todo_el_ano", "otono_invierno", "otono_invierno", None],
   "la temporada sale del nivel de abrigo")
ok(dg.color_mas_cercano((26, 26, 26)) == "negro" and dg.color_mas_cercano((250, 250, 250)) == "blanco"
   and dg.color_mas_cercano((30, 40, 90)) == "azul_marino", "el color medido se traduce al catálogo (en Lab)")
ok(dg.color_mas_cercano((216, 103, 96)) == "rojo" and dg.color_mas_cercano((240, 170, 190)) == "rosa"
   and dg.color_mas_cercano((95, 110, 50)) == "verde", "CIE94: un rojo claro, un rosa pálido y un verde olivo")
ruta = temporal / "transparente.png"
ruta.write_bytes(foto(transparente=True))
hex_, nombre = dg.color_dominante(ruta)
ok(nombre == "rojo" and hex_ == "#C81E1E", f"sin fondo, solo cuenta la prenda: {hex_} {nombre}")
ruta.write_bytes(foto(fondo=(255, 255, 255), prenda=(37, 99, 235)))
ok(dg.color_dominante(ruta)[1] == "azul", "con fondo, cuenta el centro de la foto")
ok(dg.color_dominante(temporal / "no-existe.png") is None, "sin foto no se mide nada")

# --- 2. Leer la página de una tienda ---
pagina = dg.leer_pagina("""<html><head><title>Tienda</title>
<meta property="og:image" content="/img/chamarra.jpg"><meta property="og:title" content="Chamarra  de mezclilla">
<meta property="product:price:amount" content="1,299.00"></head></html>""", "https://tienda.mx/p/1")
ok(pagina == {"imagen": "https://tienda.mx/img/chamarra.jpg", "titulo": "Chamarra de mezclilla", "precio": 1299.0},
   f"og:image (relativa), título y precio: {pagina}")
pagina = dg.leer_pagina("""<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
{"@type":"WebPage"},{"@type":"Product","name":"Tenis blancos","image":["https://cdn.mx/t.webp"],
"offers":[{"@type":"Offer","price":"899"}]}]}</script>""", "https://tienda.mx/t")
ok(pagina == {"imagen": "https://cdn.mx/t.webp", "titulo": "Tenis blancos", "precio": 899.0},
   "sin og:image usa el JSON-LD Product (imagen, nombre y precio)")
ok(dg.leer_pagina("<p>nada</p>", "https://x.mx")["imagen"] is None, "una página sin foto")

# --- 3. SSRF: solo direcciones de internet ---
for malo in ("ftp://tienda.mx/x", "http://127.0.0.1:8000/api", "http://10.0.0.5/x", "http://192.168.1.10/",
             "http://localhost:8000/", "http://169.254.169.254/latest", "http://[::1]/"):
    try:
        dg.revisar_destino(malo)
        ok(False, f"bloquea {malo}")
    except HTTPException as error:
        ok(error.status_code == 422, f"bloquea {malo}")
try:
    dg.RedireccionRevisada().redirect_request(None, None, 302, "", {}, "http://127.0.0.1/admin")
    ok(False, "una redirección a la red interna también se bloquea")
except HTTPException:
    ok(True, "una redirección a la red interna también se bloquea")

# --- 4. La API ---
dg.encolar = lambda funcion, *argumentos: funcion(*argumentos)  # el trabajo de fondo corre al instante
vio = {"categoria": "abrigo", "subcategoria": "Chamarra", "color_principal": "mezclilla", "estampado": "liso",
       "estilo": "casual", "nivel_abrigo": 4, "impermeable": False}
dg.detectar_prenda = lambda contenido: dict(vio)
pedidas = []


def motor_falso(ruta, datos=None, espera=0):
    pedidas.append((ruta, datos))
    Image.open(datos["entrada"]).convert("RGBA").save(datos["salida"])
    return {"segundos": 0.1}


def motor_apagado(ruta, datos=None, espera=0):
    raise HTTPException(503, "El probador está apagado")


dg.gpu.pedir_al_motor = motor_falso

with TestClient(principal.aplicacion) as cliente:
    def cuenta(correo):
        r = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "contraseña-larga"})
        return {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    h, otra = cuenta("digital@prueba.com"), cuenta("otra-digital@prueba.com")
    subir = lambda contenido, enc=h: cliente.post("/api/prendas/borradores", headers=enc,  # noqa: E731
                                                  files={"imagen": ("f.png", contenido, "image/png")})

    r = subir(foto())
    b = r.json()
    ok(r.status_code == 201 and b["estado"] == "lista" and b["sin_fondo"], f"la foto queda lista y sin fondo ({b['estado']})")
    ok(pedidas[-1][0] == "/quitar-fondo" and b["url_imagen"].endswith(".png") and b["url_imagen"] != b["url_original"],
       "el motor deja un PNG aparte; el original se conserva")
    ok(b["propuesta"]["categoria"] == "abrigo" and b["propuesta"]["color_principal"] == "mezclilla",
       "la IA propone los datos (y su color manda sobre el medido)")
    ok(b["propuesta"]["color_hex"].startswith("#") and b["propuesta"]["temporada"] == "otono_invierno",
       "también el color medido (HEX) y la temporada")
    ok(b["duplicada_de"] is None and "huella" not in b, "no es duplicada y la huella no sale en la respuesta")
    ok(cliente.get(f"/api/prendas/borradores/{b['id']}", headers=otra).status_code == 404, "cada quien ve sus borradores")
    ok([x["id"] for x in cliente.get("/api/prendas/borradores", headers=h).json()] == [b["id"]], "la lista por confirmar")

    r = cliente.post(f"/api/prendas/borradores/{b['id']}/confirmar", headers=h, json={
        **{k: vio[k] for k in ("categoria", "color_principal", "nivel_abrigo", "estampado", "estilo")},
        "subcategoria": "  Chamarra de mezclilla ", "precio_compra": 899.5, "fecha_adquisicion": "2026-10-01"})
    prenda = r.json()
    ok(r.status_code == 201 and prenda["subcategoria"] == "Chamarra de mezclilla" and prenda["sin_fondo"]
       and prenda["url_imagen"] == b["url_imagen"] and prenda["url_original"] == b["url_original"],
       "confirmar crea la prenda con la foto sin fondo y guarda la original")
    ok(prenda["precio_compra"] == 899.5 and prenda["fecha_adquisicion"] == "2026-10-01"
       and prenda["temporada"] == "otono_invierno" and prenda["color_hex"] == b["propuesta"]["color_hex"],
       "con precio, fecha de compra, temporada y color medido")
    ok(cliente.get("/api/prendas/borradores", headers=h).json() == [] and ruta_de(prenda["url_imagen"]).is_file(),
       "el borrador desaparece pero sus fotos quedan con la prenda")

    r = subir(foto())
    ok(r.json()["duplicada_de"] == prenda["id"], "la misma foto otra vez avisa que ya es una prenda")
    sin_datos = cliente.post(f"/api/prendas/borradores/{r.json()['id']}/confirmar", headers=h, json={"categoria": "abrigo"})
    ok(sin_datos.status_code == 422, "confirmar sin color ni abrigo: 422")
    ok(cliente.post(f"/api/prendas/borradores/{r.json()['id']}/confirmar", headers=h,
                    json={"categoria": "abrigo", "color_principal": "rojo", "nivel_abrigo": 3, "precio_compra": -5})
       .status_code == 422, "un precio negativo: 422")
    descartado = r.json()
    ok(cliente.delete(f"/api/prendas/borradores/{descartado['id']}", headers=h).status_code == 204
       and not ruta_de(descartado["url_original"]).exists() and not ruta_de(descartado["url_imagen"]).exists(),
       "descartar borra el borrador y sus dos fotos")

    dg.gpu.pedir_al_motor = motor_apagado
    dg.detectar_prenda = lambda contenido: (_ for _ in ()).throw(HTTPException(503, "Ollama apagado"))
    b = subir(foto(prenda=(22, 163, 74))).json()
    ok(b["estado"] == "lista" and not b["sin_fondo"] and b["url_imagen"] == b["url_original"] and len(b["avisos"]) == 2,
       "sin motor ni IA igual queda lista, con la foto original y dos avisos")
    ok(b["propuesta"].get("color_principal") == "verde" and b["propuesta"].get("temporada") is None,
       "sin IA, el color sale de lo medido")

    base_datos.bd().borradores.update_one({"_id": b["id"]}, {"$set": {"estado": "error"}})
    dg.gpu.pedir_al_motor = motor_falso
    dg.detectar_prenda = lambda contenido: dict(vio)
    r = cliente.post(f"/api/prendas/borradores/{b['id']}/reintentar", headers=h)
    ok(r.json()["estado"] == "lista" and r.json()["sin_fondo"], "reintentar vuelve a procesarla")

    base_datos.bd().borradores.update_one({"_id": b["id"]}, {"$set": {
        "estado": "analizando", "fecha_creacion": base_datos.ahora() - timedelta(minutes=10)}})
    ok(cliente.get("/api/prendas/borradores", headers=h).json()[0]["estado"] == "error",
       "uno que se quedó a medias (servidor reiniciado) pasa a error para reintentar")
    base_datos.bd().borradores.update_one({"_id": b["id"]}, {"$set": {"fecha_creacion": base_datos.ahora() - timedelta(days=8)}})
    ok(cliente.get("/api/prendas/borradores", headers=h).json() == [] and not ruta_de(b["url_original"]).exists(),
       "los de más de 7 días se borran solos con sus fotos")

    # --- Importar desde un link ---
    respuestas = {
        "https://tienda.mx/p/1": (b'<meta property="og:image" content="https://cdn.tienda.mx/c.png">'
                                  b'<meta property="og:title" content="Chamarra"><meta property="product:price:amount" '
                                  b'content="1299">', "text/html; charset=utf-8", "https://tienda.mx/p/1"),
        "https://cdn.tienda.mx/c.png": (foto(prenda=(30, 40, 90)), "image/png", "https://cdn.tienda.mx/c.png"),
        "https://tienda.mx/sin-foto": (b"<p>hola</p>", "text/html", "https://tienda.mx/sin-foto"),
        "https://tienda.mx/raro.gif": (b"GIF89a....", "image/gif", "https://tienda.mx/raro.gif"),
    }
    descargar_real = dg.descargar
    dg.descargar = lambda url, limite: respuestas[url]
    r = cliente.post("/api/prendas/borradores/url", headers=h, json={"url": "https://tienda.mx/p/1"})
    b = r.json()
    ok(r.status_code == 201 and b["origen"] == {"tipo": "url", "url_tienda": "https://tienda.mx/p/1", "titulo": "Chamarra"},
       "importar guarda de dónde viene y el nombre")
    ok(b["propuesta"]["precio_compra"] == 1299 and b["propuesta"]["categoria"] == "abrigo" and b["sin_fondo"],
       "y prellena el precio; la foto pasa por la IA y el fondo como las demás")
    r = cliente.post("/api/prendas/borradores/url", headers=h, json={"url": "https://cdn.tienda.mx/c.png"})
    ok(r.status_code == 201 and r.json()["origen"]["titulo"] is None, "también un link directo a una imagen")
    ok(cliente.post("/api/prendas/borradores/url", headers=h, json={"url": "https://tienda.mx/sin-foto"}).status_code == 422,
       "una página sin foto de producto: 422 con qué hacer")
    ok(cliente.post("/api/prendas/borradores/url", headers=h, json={"url": "https://tienda.mx/raro.gif"}).status_code == 422,
       "una imagen en formato que no usamos: 422")
    dg.descargar = descargar_real
    ok(cliente.post("/api/prendas/borradores/url", headers=h, json={"url": "http://127.0.0.1:8000/api/salud"})
       .status_code == 422, "la ruta real rechaza un link a la propia computadora (SSRF)")

    # --- Editar una prenda completa y quitar el fondo a las de antes ---
    vieja = cliente.post("/api/prendas", headers=h, data={"categoria": "parte_superior", "color_principal": "gris",
                                                          "nivel_abrigo": "2"},
                         files={"imagen": ("v.png", foto(prenda=(150, 150, 150)), "image/png")}).json()
    r = cliente.patch(f"/api/prendas/{vieja['id']}", headers=h, json={
        "color_principal": "negro", "subcategoria": "Playera", "precio_compra": 250, "fecha_adquisicion": "2025-12-24",
        "temporada": "todo_el_ano"})
    ok(r.status_code == 200 and r.json()["color_principal"] == "negro" and r.json()["subcategoria"] == "Playera"
       and r.json()["precio_compra"] == 250 and r.json()["categoria"] == "parte_superior",
       "editar cambia lo que viene y deja lo demás")
    for malo, motivo in (({"temporada": "invierno"}, "temporada desconocida"), ({"nivel_abrigo": 9}, "abrigo fuera de rango"),
                         ({"categoria": None}, "dejar la categoría vacía"), ({"fecha_adquisicion": "2099-01-01"}, "fecha futura")):
        ok(cliente.patch(f"/api/prendas/{vieja['id']}", headers=h, json=malo).status_code == 422, f"{motivo}: 422")
    ok(cliente.patch(f"/api/prendas/{vieja['id']}", headers=otra, json={"color_principal": "rojo"}).status_code == 404,
       "no se edita lo ajeno")

    dg.gpu.pedir_al_motor = motor_apagado
    ok(cliente.post(f"/api/prendas/{vieja['id']}/quitar-fondo", headers=h).status_code == 503, "sin motor: 503 con aviso")
    dg.gpu.pedir_al_motor = motor_falso
    r = cliente.post(f"/api/prendas/{vieja['id']}/quitar-fondo", headers=h)
    nueva = r.json()
    ok(r.status_code == 200 and nueva["sin_fondo"] and nueva["url_original"] == vieja["url_imagen"]
       and nueva["url_imagen"].endswith(".png"), "a una prenda de antes se le quita el fondo y se guarda la original")
    antes = len(pedidas)
    ok(cliente.post(f"/api/prendas/{vieja['id']}/quitar-fondo", headers=h).json()["url_imagen"] == nueva["url_imagen"]
       and len(pedidas) == antes, "si ya no tiene fondo, no se vuelve a procesar")
    cliente.delete(f"/api/prendas/{vieja['id']}", headers=h)
    ok(not ruta_de(nueva["url_imagen"]).exists() and not ruta_de(nueva["url_original"]).exists(),
       "borrar la prenda borra sus dos fotos")
    ok(cliente.post("/api/prendas/borradores", files={"imagen": ("f.png", foto(), "image/png")}).status_code == 401,
       "pide sesión")

terminar()
