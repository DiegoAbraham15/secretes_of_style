"""Buscador en tiendas: viste una prenda en una tienda y no la compraste; le tomas foto y te llevamos a buscarla.

La foto NO sale de la computadora: la IA de visión local (Ollama, la misma de "Nueva prenda") dice qué prenda
es, de qué color, con qué estampado y, si se ven, la marca y lo que la distingue (vision.detectar_para_tienda).
Con eso se arman dos búsquedas, en este orden:
  1. La misma prenda: marca + tipo + lo que la distingue + color ("Sudadera Tom y Jerry azul marino"). La persona
     puede corregir este texto si la IA se equivocó.
  2. Parecidas, por si no la encuentras: solo tipo, color y estampado ("Sudadera azul marino").
Cada búsqueda da un link por tienda que abre su buscador con ese texto.

Los links no se guardan: se arman cada vez con el texto, así una tienda que cambie su dirección se arregla aquí.
"""

from urllib.parse import quote, quote_plus

PARA = {"mujer": "mujer", "hombre": "hombre", "sin_especificar": ""}  # para quién es la prenda (va en la búsqueda)

# Cómo se dice cada valor del catálogo en una búsqueda de tienda.
COLOR = {"azul_marino": "azul marino", "cafe": "café", "mezclilla": "mezclilla"}
ESTAMPADO = {"rayas": "a rayas", "cuadros": "a cuadros", "floral": "floral", "animal": "animal print"}
ESTILO = {"formal": "formal", "deportivo": "deportiva"}  # casual, urbano y semiformal no ayudan a buscar
# Palabras que la IA agrega a los detalles pero no ayudan a buscar ("Tom y Jerry estampado" → "Tom y Jerry").
RELLENO = {"estampado", "estampada", "estampados", "diseño", "dibujo", "gráfico", "grafico", "imagen", "con"}
CATEGORIA = {"parte_superior": "Blusa", "parte_inferior": "Pantalón", "calzado": "Zapatos", "abrigo": "Chamarra",
             "accesorio": "Accesorio"}

# (tienda, cómo arma su link con el texto de búsqueda)
TIENDAS = [
    ("Mercado Libre", lambda q: f"https://listado.mercadolibre.com.mx/{quote(q.replace(' ', '-'))}"),
    ("Amazon México", lambda q: f"https://www.amazon.com.mx/s?k={quote_plus(q)}"),
    ("Shein", lambda q: f"https://www.shein.com.mx/pdsearch/{quote(q)}/"),
    ("Liverpool", lambda q: f"https://www.liverpool.com.mx/tienda?s={quote_plus(q)}"),
    ("Google Shopping", lambda q: f"https://www.google.com/search?udm=28&q={quote_plus(q)}"),  # udm=28: Shopping
]


def texto_de_busqueda(detectado: dict | None, exacta: bool = False) -> str:
    """"Chamarra mezclilla a rayas": tipo de prenda, color, estampado y, si ayuda, el estilo.

    exacta: además la marca (al principio) y lo que distingue a la prenda (después del tipo), si la IA los vio:
    "Nike Tenis Air Force 1 blanco".
    """
    if not detectado:
        return ""
    tipo = detectado.get("subcategoria") or CATEGORIA.get(detectado.get("categoria"), "")
    partes = [tipo]
    if exacta:
        marca, detalles = detectado.get("marca"), detectado.get("detalles")
        if marca and marca.lower() not in tipo.lower():
            partes.insert(0, marca)
        detalles = " ".join(p for p in (detalles or "").split() if p.lower() not in RELLENO)
        if detalles and detalles.lower() not in tipo.lower():
            partes.append(detalles)
    color = detectado.get("color_principal")
    if color:
        partes.append(COLOR.get(color, color))
    partes.append(ESTAMPADO.get(detectado.get("estampado"), ""))
    partes.append(ESTILO.get(detectado.get("estilo"), ""))
    # Sin palabras repetidas ("Playera logo blanco blanco"); las cortas ("y", "de") sí se pueden repetir.
    palabras, vistas = [], set()
    for palabra in " ".join(p for p in partes if p).split():
        if len(palabra) <= 2 or palabra.lower() not in vistas:
            palabras.append(palabra)
            vistas.add(palabra.lower())
    return " ".join(palabras)


def links(busqueda: str, para: str) -> list[dict]:
    """Un link por tienda con el texto de búsqueda (y "mujer" u "hombre" si se eligió)."""
    texto = f"{busqueda} {PARA[para]}".strip()
    return [{"tienda": tienda, "url": armar(texto)} for tienda, armar in TIENDAS]
