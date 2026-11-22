"""Comprueba el buscador en tiendas: la IA propone qué buscar, los links de cada tienda y la lista de deseos.
La IA se simula: las pruebas no necesitan Ollama.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_tiendas.py"""
import os
import sys
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pruebas.comun import png_de_color  # noqa: E402
from servidor import base_datos, principal, tiendas  # noqa: E402

# --- 1. El texto de búsqueda y los links ---
ok(tiendas.texto_de_busqueda({"categoria": "abrigo", "subcategoria": "Chamarra", "color_principal": "mezclilla",
                              "estampado": "liso", "estilo": "casual"}) == "Chamarra mezclilla",
   "tipo y color; liso y casual no se agregan porque no ayudan a buscar")
ok(tiendas.texto_de_busqueda({"categoria": "parte_superior", "subcategoria": None, "color_principal": "azul_marino",
                              "estampado": "rayas", "estilo": "formal"}) == "Blusa azul marino a rayas formal",
   "sin subcategoría usa la categoría; colores y estampados como se dicen en una tienda")
ok(tiendas.texto_de_busqueda(None) == "", "sin lo que vio la IA, el texto queda vacío")
sudadera = {"categoria": "parte_superior", "subcategoria": "Sudadera", "color_principal": "azul_marino", "estampado": "otro",
            "estilo": "urbano", "marca": None, "detalles": "Tom y Jerry estampado"}
ok(tiendas.texto_de_busqueda(sudadera, exacta=True) == "Sudadera Tom y Jerry azul marino",
   "la exacta lleva lo que distingue a la prenda, sin palabras de relleno como «estampado»")
ok(tiendas.texto_de_busqueda(sudadera) == "Sudadera azul marino", "la de parecidas, solo tipo y color")
tenis = {"categoria": "calzado", "subcategoria": "Tenis", "color_principal": "blanco", "estampado": "liso",
         "estilo": "casual", "marca": "Nike", "detalles": "Air Force 1 blanco"}
ok(tiendas.texto_de_busqueda(tenis, exacta=True) == "Nike Tenis Air Force 1 blanco", "la marca va primero y sin repetir palabras")
ok(tiendas.texto_de_busqueda({**tenis, "marca": None, "detalles": None}, exacta=True) == "Tenis blanco",
   "sin marca ni detalles, la exacta es igual a la de parecidas")
from servidor import vision  # noqa: E402
ok(vision.texto_corto("  No visible ", 40) is None and vision.texto_corto("ninguna", 40) is None, "«no visible» o «ninguna» no cuentan como marca")
ok(vision.texto_corto("\"Levi's\"", 40) == "Levi's" and len(vision.texto_corto("x" * 90, 60)) == 60, "se limpia y se recorta")
enlaces = tiendas.links("Chamarra café", "hombre")
ok([l["tienda"] for l in enlaces] == ["Mercado Libre", "Amazon México", "Shein", "Liverpool", "Google Shopping"], "un link por tienda")
ok(all("Chamarra café hombre" in unquote(l["url"]).replace("+", " ").replace("-", " ") for l in enlaces),
   "cada link lleva la búsqueda y para quién es")
ok(all(l["url"].startswith("https://") and " " not in l["url"] for l in enlaces), "links seguros y sin espacios")
ok("hombre" not in tiendas.links("Chamarra", "sin_especificar")[1]["url"], "sin especificar no agrega nada")

# --- 2. La API ---
vio = {"categoria": "calzado", "subcategoria": "Tenis", "color_principal": "blanco", "estampado": "liso",
       "estilo": "deportivo", "nivel_abrigo": 2, "impermeable": False, "marca": "Adidas", "detalles": "Samba"}
principal.detectar_para_tienda = lambda contenido: vio

with TestClient(principal.aplicacion) as cliente:
    def cuenta(correo):
        r = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "contraseña-larga"})
        return {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    h, otra = cuenta("tiendas@prueba.com"), cuenta("otra@prueba.com")
    foto = {"imagen": ("tienda.png", png_de_color(250, 250, 250, 16), "image/png")}

    r = cliente.post("/api/deseos", headers=h, files=foto, data={"para": "mujer"})
    deseo = r.json()
    ok(r.status_code == 201 and deseo["busqueda"] == "Adidas Tenis Samba blanco deportiva",
       f"primero la misma prenda: marca, modelo y color ({deseo.get('busqueda')})")
    ok(deseo["parecida"] == "Tenis blanco deportiva" and len(deseo["links_parecidas"]) == 5
       and "Samba" not in deseo["links_parecidas"][0]["url"], "después, parecidas: sin marca ni modelo")
    ok(deseo["para"] == "mujer" and deseo["aviso"] is None and len(deseo["links"]) == 5, "se guarda con sus 5 links")
    ok("mujer" in deseo["links"][1]["url"], "los links llevan para quién es")
    ok(set(deseo["detectado"]) == {"categoria", "subcategoria", "color_principal", "estampado", "estilo", "nivel_abrigo",
                                   "impermeable", "marca", "detalles"}, "guarda lo que vio la IA, con marca y detalles")
    archivo = base_datos.CARPETA_ARCHIVOS / deseo["url_imagen"].removeprefix("/archivos/")
    ok(archivo.exists() and cliente.get(deseo["url_imagen"]).status_code == 200, "la foto se guarda y se puede ver")

    principal.detectar_para_tienda = lambda contenido: (_ for _ in ()).throw(HTTPException(503, "Ollama apagado"))
    r = cliente.post("/api/deseos", headers=h, files=foto)
    sin_ia = r.json()
    ok(r.status_code == 201 and sin_ia["aviso"] == principal.AVISO_SIN_IA and sin_ia["busqueda"] == "Ropa"
       and sin_ia["detectado"] is None, "sin IA igual se guarda y avisa que escribas qué buscar")
    ok(sin_ia["parecida"] is None and sin_ia["links_parecidas"] == [], "sin lo que vio la IA no hay búsqueda de parecidas")
    ok(cliente.post(f"/api/deseos/{sin_ia['id']}/analizar", headers=h).status_code == 503, "volver a analizar con la IA apagada: 503")
    ok(sin_ia["para"] == "sin_especificar", "si no se dice para quién, queda sin especificar")

    principal.detectar_para_tienda = lambda contenido: {**vio, "categoria": "parte_superior", "subcategoria": "Sudadera",
                                                        "color_principal": "azul_marino", "marca": None,
                                                        "detalles": "Tom y Jerry", "estilo": "urbano", "estampado": "otro"}
    r = cliente.post(f"/api/deseos/{sin_ia['id']}/analizar", headers=h)
    ok(r.status_code == 200 and r.json()["busqueda"] == "Sudadera Tom y Jerry azul marino"
       and r.json()["parecida"] == "Sudadera azul marino", "volver a analizar rehace la búsqueda exacta y la de parecidas")
    ok(cliente.post(f"/api/deseos/{sin_ia['id']}/analizar", headers=otra).status_code == 404, "no se analiza lo ajeno")
    ok(cliente.post(f"/api/deseos/{sin_ia['id']}/analizar").status_code == 401, "analizar pide sesión")
    principal.detectar_para_tienda = lambda contenido: (_ for _ in ()).throw(HTTPException(503, "Ollama apagado"))

    lista = cliente.get("/api/deseos", headers=h).json()
    ok([d["id"] for d in lista] == [sin_ia["id"], deseo["id"]] and all(len(d["links"]) == 5 for d in lista),
       "la lista va de la más nueva a la más vieja, con sus links")
    ok(cliente.get("/api/deseos", headers=otra).json() == [], "cada quien ve solo su lista")

    r = cliente.patch(f"/api/deseos/{sin_ia['id']}", headers=h, json={"busqueda": "  Bolsa de piel café  ", "para": "mujer"})
    ok(r.status_code == 200 and r.json()["busqueda"] == "Bolsa de piel café" and "Bolsa+de+piel" in r.json()["links"][1]["url"],
       "corregir el texto cambia los links")
    ok(cliente.patch(f"/api/deseos/{sin_ia['id']}", headers=h, json={"busqueda": "   "}).status_code == 422, "texto vacío: 422")
    ok(cliente.patch(f"/api/deseos/{sin_ia['id']}", headers=h, json={"busqueda": "x" * 121}).status_code == 422, "texto muy largo: 422")
    ok(cliente.patch(f"/api/deseos/{sin_ia['id']}", headers=h, json={"para": "niños"}).status_code == 422, "para quién desconocido: 422")
    ok(cliente.patch(f"/api/deseos/{deseo['id']}", headers=otra, json={"busqueda": "Otra"}).status_code == 404, "no se edita lo ajeno")
    ok(cliente.post("/api/deseos", headers=h, files=foto, data={"para": "niños"}).status_code == 422, "al buscar, para quién desconocido: 422")
    no_imagen = {"imagen": ("x.png", b"esto no es una imagen", "image/png")}
    ok(cliente.post("/api/deseos", headers=h, files=no_imagen).status_code == 415, "un archivo que no es imagen: 415")
    ok(cliente.post("/api/deseos", files=foto).status_code == 401, "buscar pide sesión")
    ok(cliente.get("/api/deseos").status_code == 401, "la lista pide sesión")

    ok(cliente.delete(f"/api/deseos/{deseo['id']}", headers=otra).status_code == 404, "no se borra lo ajeno")
    ok(cliente.delete(f"/api/deseos/{deseo['id']}", headers=h).status_code == 204, "quitar de la lista")
    ok(not archivo.exists(), "al quitarla también se borra su foto")
    ok([d["id"] for d in cliente.get("/api/deseos", headers=h).json()] == [sin_ia["id"]], "ya no aparece en la lista")
    ok(cliente.delete(f"/api/deseos/{deseo['id']}", headers=h).status_code == 404, "borrarla otra vez: 404")

terminar()
