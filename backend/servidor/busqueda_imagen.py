"""Búsqueda por imagen: dónde está en internet la prenda exacta de tu foto (Google Cloud Vision, detección web).

La IA local sabe QUÉ es la prenda, pero no conoce los catálogos de las tiendas. Para encontrar ESA misma prenda, el
servidor manda la foto a Google Cloud Vision (función WEB_DETECTION), que la compara con las imágenes de internet y
contesta:
  - pagesWithMatchingImages  páginas donde aparece la misma foto o la misma prenda → "La misma prenda"
  - visuallySimilarImages    imágenes que se le parecen                            → "Parecidas"
  - bestGuessLabels          cómo la llamaría Google ("tom and jerry sweatshirt")
Las páginas de tiendas van primero (las de México antes); las redes sociales se quitan porque ahí no se compra.

Se activa con la variable GOOGLE_VISION_CLAVE en backend/.env (una clave de API de Google Cloud con la Cloud Vision
API habilitada). Sin ella, activa() es False y la app sigue con la búsqueda por texto.
"""

import base64
import html
import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

from servidor.base_datos import ahora

URL_VISION = "https://vision.googleapis.com/v1/images:annotate"
MAXIMO_RESULTADOS = 30  # los que se piden a Google; se muestran hasta MAXIMO_EXACTAS y MAXIMO_PARECIDAS
MAXIMO_EXACTAS = 12
MAXIMO_PARECIDAS = 12
ESPERA_SEGUNDOS = 20

# Parte del dominio → nombre de la tienda. También los servidores de imágenes de algunas (mlstatic es Mercado Libre).
TIENDAS = {
    "mercadolibre": "Mercado Libre", "mlstatic": "Mercado Libre", "amazon": "Amazon", "media-amazon": "Amazon",
    "shein": "Shein", "ltwebstatic": "Shein", "liverpool": "Liverpool", "elpalaciodehierro": "El Palacio de Hierro",
    "zara": "Zara", "hm": "H&M", "nike": "Nike", "adidas": "Adidas", "puma": "Puma", "underarmour": "Under Armour",
    "levi": "Levi's", "gap": "Gap", "walmart": "Walmart", "coppel": "Coppel", "suburbia": "Suburbia", "sears": "Sears",
    "cyamoda": "C&A", "pullandbear": "Pull&Bear", "bershka": "Bershka", "stradivarius": "Stradivarius",
    "mango": "Mango", "uniqlo": "Uniqlo", "innovasport": "Innovasport", "marti": "Martí", "privalia": "Privalia",
    "aliexpress": "AliExpress", "alicdn": "AliExpress", "temu": "Temu", "kwcdn": "Temu", "ebay": "eBay",
    "ebayimg": "eBay", "etsy": "Etsy", "etsystatic": "Etsy", "asos": "ASOS", "zalando": "Zalando",
    "farfetch": "Farfetch", "gotrendier": "GoTrendier", "vinted": "Vinted", "depop": "Depop", "poshmark": "Poshmark",
    "hottopic": "Hot Topic", "boxlunch": "BoxLunch", "redbubble": "Redbubble", "teepublic": "TeePublic",
    "shopee": "Shopee", "dafiti": "Dafiti", "falabella": "Falabella", "target": "Target", "kohls": "Kohl's",
    "macys": "Macy's", "nordstrom": "Nordstrom", "footlocker": "Foot Locker", "converse": "Converse", "vans": "Vans",
}
# Donde no se compra: no sirven para la vista previa.
SIN_COMPRA = {"pinterest", "instagram", "facebook", "tiktok", "twitter", "x", "reddit", "youtube", "tumblr", "fbsbx",
              "pinimg", "cdninstagram", "wikipedia", "wikimedia"}


def activa() -> bool:
    """¿Hay clave de Google Cloud Vision? Se lee cada vez: basta con agregarla al .env y reiniciar."""
    return bool(os.getenv("GOOGLE_VISION_CLAVE"))


def segura(url) -> bool:
    """Solo links http(s): la app los abre tal cual."""
    return isinstance(url, str) and urlparse(url).scheme in ("http", "https") and bool(urlparse(url).hostname)


def partes_del_dominio(url: str) -> list[str]:
    return (urlparse(url).hostname or "").lower().removeprefix("www.").split(".")


def tienda_de(url: str) -> str | None:
    """El nombre de la tienda si el dominio es de una conocida ("listado.mercadolibre.com.mx" → "Mercado Libre")."""
    return next((TIENDAS[parte] for parte in partes_del_dominio(url) if parte in TIENDAS), None)


def sitio_de(url: str) -> str:
    """Para las páginas que no son tiendas conocidas: el dominio sin www ("tiendadeplayeras.mx")."""
    return ".".join(partes_del_dominio(url))


def limpiar_titulo(titulo) -> str:
    """Google marca en negritas lo que coincide ("<b>Sudadera</b> Tom y Jerry"): se quitan etiquetas y entidades."""
    texto = html.unescape(re.sub(r"<[^>]+>", "", str(titulo or "")))
    return " ".join(texto.split())[:120]


def consultar_vision(cuerpo: dict, clave: str) -> dict:
    """La llamada a la API (aparte para que las pruebas la simulen)."""
    peticion = urllib.request.Request(f"{URL_VISION}?key={clave}", data=json.dumps(cuerpo).encode(),
                                      headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=ESPERA_SEGUNDOS) as respuesta:
        return json.load(respuesta)


class ErrorDeBusqueda(Exception):
    """Google no contestó o contestó con un error (clave inválida, API sin habilitar, sin red...)."""


def exactas_de(paginas: list[dict]) -> list[dict]:
    """Las páginas donde aparece la prenda, como vistas previas: tiendas primero (.mx antes) y sin redes sociales."""
    resultados, vistas = [], set()
    for pagina in paginas:
        url = pagina.get("url")
        if not segura(url) or url in vistas or set(partes_del_dominio(url)) & SIN_COMPRA:
            continue
        completas = [i["url"] for i in pagina.get("fullMatchingImages", []) if segura(i.get("url"))]
        parciales = [i["url"] for i in pagina.get("partialMatchingImages", []) if segura(i.get("url"))]
        tienda = tienda_de(url)
        vistas.add(url)
        resultados.append({
            "titulo": limpiar_titulo(pagina.get("pageTitle")) or tienda or sitio_de(url),
            "url": url,
            "tienda": tienda or sitio_de(url),
            "es_tienda": tienda is not None,
            "imagen": (completas or parciales or [None])[0],
            "misma_foto": bool(completas),  # la foto coincide completa, no solo una parte
        })
    resultados.sort(key=lambda r: (not r["es_tienda"], not partes_del_dominio(r["url"])[-1] == "mx", not r["misma_foto"],
                                   r["imagen"] is None))
    return resultados[:MAXIMO_EXACTAS]


def parecidas_de(imagenes: list[dict]) -> list[dict]:
    """Las imágenes parecidas: Google no dice de qué página son, así que van sin link (solo la vista previa)."""
    resultados = []
    for imagen in imagenes:
        url = imagen.get("url")
        if not segura(url) or set(partes_del_dominio(url)) & SIN_COMPRA:
            continue
        resultados.append({"imagen": url, "tienda": tienda_de(url), "url": None})
    return resultados[:MAXIMO_PARECIDAS]


def buscar_por_imagen(contenido: bytes) -> dict | None:
    """Lo que encontró Google con la foto. None si no hay clave; ErrorDeBusqueda si Google no contestó bien."""
    clave = os.getenv("GOOGLE_VISION_CLAVE")
    if not clave:
        return None
    cuerpo = {"requests": [{
        "image": {"content": base64.b64encode(contenido).decode()},
        "features": [{"type": "WEB_DETECTION", "maxResults": MAXIMO_RESULTADOS}],
        "imageContext": {"webDetectionParams": {"includeGeoResults": True}},
    }]}
    try:
        respuesta = consultar_vision(cuerpo, clave)["responses"][0]
    except urllib.error.HTTPError as error:  # 400 clave inválida, 403 API sin habilitar o sin facturación
        raise ErrorDeBusqueda(f"Google Cloud Vision respondió {error.code}: revisa la clave y que la API esté habilitada")
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError):
        raise ErrorDeBusqueda("No se pudo consultar Google Cloud Vision (¿hay internet?)")
    if "error" in respuesta:
        raise ErrorDeBusqueda(f"Google Cloud Vision: {respuesta['error'].get('message', 'error')}")
    web = respuesta.get("webDetection", {})
    etiquetas = [e.get("label") for e in web.get("bestGuessLabels", []) if e.get("label")]
    return {
        "exactas": exactas_de(web.get("pagesWithMatchingImages", [])),
        "parecidas": parecidas_de(web.get("visuallySimilarImages", [])),
        "etiqueta": etiquetas[0] if etiquetas else None,
        "fecha": ahora(),
    }
