"""Digitalización sin fricción: de una foto (o del link de una tienda) a una prenda lista para confirmar.

Cada foto se vuelve un BORRADOR (colección borradores) que se procesa en segundo plano, de dos en dos:
  1. La IA local (vision.detectar_prenda, Ollama) propone categoría, tipo, color, estampado, estilo y abrigo.
  2. Al mismo tiempo, el motor del probador le quita el fondo (U2-Net, o SegFormer si la trae puesta una persona) y
     deja un PNG transparente recortado a la prenda. Si el motor está apagado, se queda la foto original.
  3. Del PNG se mide el color dominante (k-means con numpy sobre lo que no es fondo) → HEX y el color del catálogo
     más cercano en el espacio L*a*b*. Se usa si la IA no dijo el color.
  4. La temporada sale del nivel de abrigo, y la huella (md5) avisa si esa misma foto ya es una prenda.
La app consulta el borrador mientras se procesa (etapa: en_fila → analizando → lista) y la persona confirma con un
toque. Nada se agrega al armario hasta confirmar.

importar_url: el link de una tienda → la foto (og:image, twitter:image o JSON-LD Product), el nombre y el precio.
Como el servidor descarga lo que le pasan, se protege contra SSRF: solo http(s) y nunca direcciones privadas, ni
siquiera después de una redirección.
"""

import hashlib
import ipaddress
import json
import socket
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import numpy as np
from fastapi import HTTPException
from PIL import Image, ImageOps

from servidor import gpu
from servidor.archivos import borrar_imagen, guardar_imagen, revisar_imagen, ruta_de
from servidor.base_datos import ahora, bd, siguiente_id
from servidor.esquemas import TEMPORADAS
from servidor.logica import HEX_COLOR
from servidor.vision import detectar_prenda

DIAS_DE_BORRADOR = 7  # los borradores sin confirmar se borran solos
MINUTOS_SIN_TERMINAR = 5  # un borrador "en proceso" más viejo que esto se interrumpió (p. ej. se reinició el servidor)
MAXIMO_HTML = 3 * 1024 * 1024
MAXIMO_FOTO = 8 * 1024 * 1024
AGENTE = "Mozilla/5.0 (compatible; SecretsOfStyle/1.0)"  # genérico: no lleva datos de la persona

ejecutor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="borradores")


def encolar(funcion, *argumentos):
    """Manda el trabajo a la fila de fondo. Las pruebas lo cambian para que corra al instante."""
    ejecutor.submit(funcion, *argumentos)


# ------------------------------------------------
# 1. MEDIR LA FOTO
# ------------------------------------------------

def temporada_de(nivel_abrigo: int | None) -> str | None:
    """1–2 primavera/verano, 3 todo el año, 4–5 otoño/invierno."""
    if not nivel_abrigo:
        return None
    return TEMPORADAS[0] if nivel_abrigo <= 2 else TEMPORADAS[1] if nivel_abrigo == 3 else TEMPORADAS[2]


def a_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB (0–255) → CIE L*a*b* (D65). Distancias en Lab se parecen a las que ve el ojo."""
    c = rgb.astype(float) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]])
    xyz /= np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


LAB_CATALOGO = {nombre: a_lab(np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)])) for nombre, h in HEX_COLOR.items()}


NEUTROS_PUROS = {"negro", "blanco", "gris"}


def diferencia_cie94(lab1, lab2) -> float:
    """ΔE CIE94 con los pesos para textiles (kL = 2): la luz pesa menos que el tono, como al ver tela."""
    croma1, croma2 = np.hypot(lab1[1], lab1[2]), np.hypot(lab2[1], lab2[2])
    delta_l, delta_c = lab1[0] - lab2[0], croma1 - croma2
    delta_h2 = max(float(((lab1[1:] - lab2[1:]) ** 2).sum() - delta_c ** 2), 0.0)
    return float(np.sqrt((delta_l / 2) ** 2 + (delta_c / (1 + 0.048 * croma1)) ** 2
                         + delta_h2 / (1 + 0.014 * croma1) ** 2))


def color_mas_cercano(rgb) -> str:
    """El color del catálogo más parecido. Un color vivo (croma ≥ 15) nunca se llama negro, blanco o gris: un rosa
    claro se parecería más al blanco por la luz, pero se ve rosa."""
    lab = a_lab(np.asarray(rgb))
    vivo = np.hypot(lab[1], lab[2]) >= 15
    candidatos = [n for n in LAB_CATALOGO if not (vivo and n in NEUTROS_PUROS)]
    return min(candidatos, key=lambda nombre: diferencia_cie94(lab, LAB_CATALOGO[nombre]))


def color_dominante(ruta) -> tuple[str, str] | None:
    """(HEX, color del catálogo) del grupo de píxeles más grande. Sin fondo, solo cuenta la prenda (alfa > 128);
    con fondo, el centro de la foto. k-means (k = 3) hecho a mano, con un inicio fijo para que sea repetible."""
    try:
        imagen = ImageOps.exif_transpose(Image.open(ruta))
        imagen.thumbnail((160, 160))
        rgba = np.asarray(imagen.convert("RGBA"))
    except OSError:
        return None
    if (rgba[..., 3] < 128).mean() > 0.05:  # tiene transparencia: el PNG sin fondo
        pixeles = rgba[rgba[..., 3] > 128][:, :3]
    else:
        alto, ancho = rgba.shape[:2]
        pixeles = rgba[alto // 4: 3 * alto // 4, ancho // 4: 3 * ancho // 4, :3].reshape(-1, 3)
    if len(pixeles) < 20:
        return None
    pixeles = pixeles.astype(float)
    brillo = pixeles.mean(axis=1)
    centros = np.array([pixeles[np.argsort(brillo)[int(q * (len(brillo) - 1))]] for q in (0.2, 0.5, 0.8)])
    for _ in range(10):
        grupo = np.argmin(((pixeles[:, None, :] - centros[None]) ** 2).sum(-1), axis=1)
        centros = np.array([pixeles[grupo == k].mean(0) if (grupo == k).any() else centros[k] for k in range(3)])
    mayor = np.bincount(grupo, minlength=3).argmax()
    rgb = np.clip(np.round(centros[mayor]), 0, 255).astype(int)
    return "#{:02X}{:02X}{:02X}".format(*rgb), color_mas_cercano(rgb)


def huella(contenido: bytes) -> str:
    return hashlib.md5(contenido).hexdigest()


def huella_de_prenda(prenda: dict) -> str | None:
    """La guardada o, para las prendas de antes, la de su foto original."""
    if prenda.get("huella"):
        return prenda["huella"]
    ruta = ruta_de(prenda.get("url_original") or prenda["url_imagen"])
    return huella(ruta.read_bytes()) if ruta.is_file() else None


def duplicada_de(usuario_id: int, marca: str) -> int | None:
    """El id de la prenda que tiene exactamente la misma foto, si hay."""
    for prenda in bd().prendas.find({"usuario_id": usuario_id}, {"huella": 1, "url_imagen": 1, "url_original": 1}):
        if huella_de_prenda(prenda) == marca:
            return prenda["_id"]
    return None


# ------------------------------------------------
# 2. QUITAR EL FONDO (el motor del probador)
# ------------------------------------------------

def quitar_fondo(ruta_publica: str) -> str | None:
    """Pide al motor el PNG sin fondo de la foto. Devuelve su ruta pública, o None si el motor no respondió."""
    salida = guardar_imagen(b"", ".png", "prendas")  # reserva el nombre; el motor escribe encima
    try:
        gpu.pedir_al_motor("/quitar-fondo", {"entrada": str(ruta_de(ruta_publica)), "salida": str(ruta_de(salida))},
                           espera=180)
    except HTTPException:
        borrar_imagen(salida)
        return None
    if not ruta_de(salida).is_file() or ruta_de(salida).stat().st_size == 0:
        borrar_imagen(salida)
        return None
    return salida


# ------------------------------------------------
# 3. LOS BORRADORES
# ------------------------------------------------

def crear_borrador(usuario_id: int, contenido: bytes, extension: str, origen: dict | None,
                   propuesta: dict | None = None) -> dict:
    """Guarda la foto original y deja el borrador en la fila. Responde de inmediato."""
    marca = huella(contenido)
    documento = {
        "_id": siguiente_id("borradores"),
        "usuario_id": usuario_id,
        "url_original": guardar_imagen(contenido, extension, "prendas"),
        "url_imagen": None,
        "sin_fondo": False,
        "huella": marca,
        "estado": "en_fila",
        "propuesta": propuesta or {},
        "avisos": [],
        "duplicada_de": duplicada_de(usuario_id, marca),
        "origen": origen,
        "fecha_creacion": ahora(),
    }
    documento["url_imagen"] = documento["url_original"]
    bd().borradores.insert_one(documento)
    encolar(procesar_borrador, documento["_id"])
    return bd().borradores.find_one({"_id": documento["_id"]})  # ya procesado si la fila fue muy rápida


def procesar_borrador(borrador_id: int):
    """El trabajo de fondo: IA y quitar fondo a la vez, luego color y temporada."""
    borrador = bd().borradores.find_one({"_id": borrador_id})
    if borrador is None:
        return
    original = ruta_de(borrador["url_original"])
    if not original.is_file():
        return
    bd().borradores.update_one({"_id": borrador_id}, {"$set": {"estado": "analizando"}})
    contenido = original.read_bytes()
    avisos = []

    def ver():
        try:
            return detectar_prenda(contenido)
        except HTTPException:
            avisos.append("La IA no estaba disponible: revisa los datos a mano.")
            return {}

    try:
        with ThreadPoolExecutor(max_workers=2) as hilos:
            vista, sin_fondo = hilos.submit(ver), hilos.submit(quitar_fondo, borrador["url_original"])
            visto, url_sin_fondo = vista.result(), sin_fondo.result()
    except Exception:  # nunca dejar el borrador colgado
        bd().borradores.update_one({"_id": borrador_id}, {"$set": {"estado": "error", "avisos": [
            "No se pudo analizar la foto; intenta de nuevo."]}})
        return
    if url_sin_fondo is None:
        avisos.append("El fondo no se quitó (el motor está apagado): se usa la foto como está.")
    url_imagen = url_sin_fondo or borrador["url_original"]
    medido = color_dominante(ruta_de(url_imagen))
    propuesta = {**{k: v for k, v in visto.items() if v is not None}, **borrador.get("propuesta", {})}
    if medido:
        propuesta["color_hex"] = medido[0]
        propuesta.setdefault("color_principal", medido[1])  # la IA manda; lo medido solo si ella no dijo
    propuesta["temporada"] = propuesta.get("temporada") or temporada_de(propuesta.get("nivel_abrigo"))
    hecho = bd().borradores.update_one({"_id": borrador_id}, {"$set": {
        "estado": "lista", "url_imagen": url_imagen, "sin_fondo": url_sin_fondo is not None,
        "propuesta": propuesta, "avisos": avisos}})
    if hecho.matched_count == 0:  # lo descartaron mientras se procesaba
        borrar_imagen(url_sin_fondo)


def limpiar_borradores(usuario_id: int):
    """Borra los de más de 7 días (y sus fotos) y marca como error los que se quedaron a medias."""
    viejos = list(bd().borradores.find({"usuario_id": usuario_id,
                                        "fecha_creacion": {"$lt": ahora() - timedelta(days=DIAS_DE_BORRADOR)}}))
    for borrador in viejos:
        descartar(borrador)
    bd().borradores.update_many(
        {"usuario_id": usuario_id, "estado": {"$in": ["en_fila", "analizando"]},
         "fecha_creacion": {"$lt": ahora() - timedelta(minutes=MINUTOS_SIN_TERMINAR)}},
        {"$set": {"estado": "error", "avisos": ["El análisis se interrumpió; toca reintentar."]}})


def descartar(borrador: dict):
    """Borra el borrador y sus fotos (las de una prenda confirmada ya no son del borrador)."""
    bd().borradores.delete_one({"_id": borrador["_id"]})
    borrar_imagen(borrador["url_original"])
    if borrador.get("url_imagen") != borrador["url_original"]:
        borrar_imagen(borrador.get("url_imagen"))


# ------------------------------------------------
# 4. IMPORTAR DESDE EL LINK DE UNA TIENDA
# ------------------------------------------------

def revisar_destino(url: str):
    """Solo http(s) hacia internet: rechaza localhost, la red de la casa y demás direcciones internas (SSRF)."""
    partes = urlparse(url)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise HTTPException(422, "Pega un link que empiece con http:// o https://")
    try:
        direcciones = {info[4][0] for info in socket.getaddrinfo(partes.hostname, partes.port or 443)}
    except (socket.gaierror, UnicodeError):
        raise HTTPException(422, "No encontramos esa página; revisa el link")
    for direccion in direcciones:
        ip = ipaddress.ip_address(direccion.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise HTTPException(422, "Ese link no es de una tienda en internet")


class RedireccionRevisada(urllib.request.HTTPRedirectHandler):
    """Cada redirección se revisa igual que el link original."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        revisar_destino(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def descargar(url: str, limite: int) -> tuple[bytes, str, str]:
    """(contenido, tipo, url final). Aparte para que las pruebas la simulen."""
    revisar_destino(url)
    abridor = urllib.request.build_opener(RedireccionRevisada)
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept-Language": "es-MX,es;q=0.9"})
    try:
        with abridor.open(peticion, timeout=10) as respuesta:
            contenido = respuesta.read(limite + 1)
            tipo = respuesta.headers.get("Content-Type", "")
            final = respuesta.geturl()
    except urllib.error.HTTPError as error:
        raise HTTPException(422, f"La tienda no dejó leer la página ({error.code}); guarda la foto y súbela desde la galería")
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        raise HTTPException(422, "No se pudo abrir el link; revisa tu conexión o el link")
    if len(contenido) > limite:
        raise HTTPException(413, "La página o la imagen es demasiado grande")
    return contenido, tipo, final


class LectorDePagina(HTMLParser):
    """Junta las etiquetas <meta>, el <title> y los bloques JSON-LD de una página."""

    def __init__(self):
        super().__init__()
        self.meta, self.json_ld, self.titulo = {}, [], ""
        self._en_json = self._en_titulo = False

    def handle_starttag(self, etiqueta, atributos):
        atributos = dict(atributos)
        if etiqueta == "meta":
            clave = (atributos.get("property") or atributos.get("name") or "").lower()
            if clave and atributos.get("content") and clave not in self.meta:
                self.meta[clave] = atributos["content"].strip()
        elif etiqueta == "script" and (atributos.get("type") or "").lower() == "application/ld+json":
            self._en_json = True
            self.json_ld.append("")
        elif etiqueta == "title":
            self._en_titulo = True

    def handle_endtag(self, etiqueta):
        self._en_json = self._en_json and etiqueta != "script"
        self._en_titulo = self._en_titulo and etiqueta != "title"

    def handle_data(self, datos):
        if self._en_json:
            self.json_ld[-1] += datos
        elif self._en_titulo:
            self.titulo += datos


def productos_en(nodo):
    """Recorre el JSON-LD y devuelve los objetos de tipo Product."""
    if isinstance(nodo, list):
        for parte in nodo:
            yield from productos_en(parte)
    elif isinstance(nodo, dict):
        tipo = nodo.get("@type")
        if tipo == "Product" or (isinstance(tipo, list) and "Product" in tipo):
            yield nodo
        for valor in nodo.values():
            if isinstance(valor, (dict, list)):
                yield from productos_en(valor)


def a_numero(valor) -> float | None:
    try:
        numero = float(str(valor).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return None
    return numero if 0 < numero < 1_000_000 else None


def leer_pagina(html_texto: str, base: str) -> dict:
    """{imagen, titulo, precio} de la página de un producto."""
    lector = LectorDePagina()
    lector.feed(html_texto)
    meta = lector.meta
    producto = {}
    for bloque in lector.json_ld:
        try:
            producto = next(productos_en(json.loads(bloque)), {}) or producto
        except ValueError:
            continue
        if producto:
            break
    imagen = meta.get("og:image:secure_url") or meta.get("og:image") or meta.get("twitter:image")
    if not imagen and producto.get("image"):
        imagen = producto["image"]
        imagen = imagen[0] if isinstance(imagen, list) else imagen
        imagen = imagen.get("url") if isinstance(imagen, dict) else imagen
    ofertas = producto.get("offers") or {}
    ofertas = ofertas[0] if isinstance(ofertas, list) and ofertas else ofertas
    precio = a_numero(meta.get("product:price:amount") or meta.get("og:price:amount")
                      or (ofertas.get("price") if isinstance(ofertas, dict) else None))
    titulo = meta.get("og:title") or meta.get("twitter:title") or producto.get("name") or lector.titulo
    return {"imagen": urljoin(base, imagen) if isinstance(imagen, str) else None,
            "titulo": " ".join(str(titulo or "").split())[:120] or None, "precio": precio}


def importar_url(url: str) -> tuple[bytes, str, dict]:
    """(foto, extensión, {titulo, precio, url_tienda}) desde el link de un producto o de una imagen."""
    url = url.strip()
    contenido, tipo, final = descargar(url, MAXIMO_HTML)
    datos = {"titulo": None, "precio": None, "url_tienda": url}
    if not tipo.startswith("image/"):
        pagina = leer_pagina(contenido.decode("utf-8", errors="ignore"), final)
        if not pagina["imagen"]:
            raise HTTPException(422, "No encontramos la foto de la prenda en esa página; guárdala y súbela desde la galería")
        datos.update(titulo=pagina["titulo"], precio=pagina["precio"])
        contenido, tipo, _ = descargar(pagina["imagen"], MAXIMO_FOTO)
    try:
        extension = revisar_imagen(contenido)
    except HTTPException:
        raise HTTPException(422, "La foto de esa tienda está en un formato que no podemos usar; guárdala y súbela")
    return contenido, extension, datos
