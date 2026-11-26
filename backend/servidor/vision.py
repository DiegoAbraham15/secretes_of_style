"""Detección de prendas en una foto con un modelo de visión local (Ollama).

Al agregar una prenda, la app manda la foto y el modelo propone sus datos para llenar el
formulario; la persona los revisa antes de guardar. Nada sale de la computadora: Ollama corre
en el mismo equipo que el servidor (ver ollama.py).

  Modelo         gemma3:4b, un modelo de visión y lenguaje que entiende imágenes y texto.
  Instrucciones  el prompt explica las categorías, los colores, el estampado, el estilo y el abrigo.
  Esquema        salida estructurada: Ollama obliga al modelo a contestar un JSON que solo usa
                 los valores de los catálogos (categoría, color, estampado, estilo, abrigo de 1 a 5...).
  Limpieza       se revisa la respuesta otra vez: lo que no esté en los catálogos queda en None.

Requisitos: Ollama abierto y el modelo descargado (ollama pull gemma3:4b).
"""

import json
import unicodedata

from servidor.esquemas import TIPOS_POR_CATEGORIA
from servidor.logica import COLORES, ESTAMPADOS, ESTILOS
from servidor.ollama import preguntar

# ------------------------------------------------
# 1. LO QUE EL MODELO PUEDE CONTESTAR
# ------------------------------------------------

# Mismas categorías que esquemas.CATEGORIAS, con ejemplos para el prompt.
# Los ejemplos son los tipos del catálogo (esquemas.TIPOS_POR_CATEGORIA): así la IA y el formulario hablan igual.
EJEMPLOS_CATEGORIA = {categoria: ", ".join(t.lower() for t in tipos) for categoria, tipos in TIPOS_POR_CATEGORIA.items()}
COLORES_ORDENADOS = sorted(COLORES)

ESQUEMA = {
    "type": "object",
    "properties": {
        "categoria": {"type": "string", "enum": list(EJEMPLOS_CATEGORIA)},
        "subcategoria": {"type": "string"},
        "color_principal": {"type": "string", "enum": COLORES_ORDENADOS},
        "estampado": {"type": "string", "enum": ESTAMPADOS},
        "estilo": {"type": "string", "enum": ESTILOS},
        "nivel_abrigo": {"type": "integer", "minimum": 1, "maximum": 5},
        "impermeable": {"type": "boolean"},
    },
    "required": ["categoria", "subcategoria", "color_principal", "estampado", "estilo", "nivel_abrigo", "impermeable"],
}

INSTRUCCIONES = f"""Eres el asistente de un armario digital. Mira la prenda de la foto y contesta en JSON.

categoria: una de estas (con ejemplos):
{chr(10).join(f"- {c}: {e}" for c, e in EJEMPLOS_CATEGORIA.items())}
subcategoria: el tipo de prenda en español. Usa exactamente uno de los de la categoría si la prenda encaja (los
de arriba); si no, escribe el tipo en una o dos palabras (por ejemplo "Vestido", "Mochila").
color_principal: el color que cubre más área de la prenda, no del fondo. Usa "mezclilla" para el azul
de los jeans, "azul_marino" para el azul muy oscuro y "cafe" para el café o marrón.
estampado: "liso" si es de un solo color (aunque tenga costuras o botones); si no, "rayas", "cuadros",
"floral", "animal" (leopardo, cebra) u "otro" (letras, dibujos, lunares).
estilo: "formal" (traje, saco, corbata, vestido de noche, zapatos de vestir), "semiformal" (camisa con
cuello, pantalón de vestir, blazer, blusa arreglada, mocasines), "deportivo" (ropa para hacer ejercicio,
tenis para correr, pants), "urbano" (sudadera holgada, playera con estampado grande, pantalón cargo,
gorra, tenis de moda) o "casual" (todo lo demás, como jeans y playeras lisas).
nivel_abrigo: 1 muy fresca (tirantes, short, sandalias), 2 ligera (playera, blusa), 3 media (camisa de
manga larga, jeans, tenis), 4 abrigada (suéter, sudadera, botas), 5 muy abrigada (abrigo grueso, chamarra de invierno).
impermeable: true solo si la prenda resiste la lluvia (impermeable, botas de lluvia, chamarra de nylon)."""


# ------------------------------------------------
# 2. CONSULTA AL MODELO
# ------------------------------------------------

def sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def normalizar_tipo(texto: str, categoria: str | None) -> str:
    """Si el tipo es uno del catálogo de la categoría (sin importar mayúsculas, acentos ni plural), da su nombre exacto.

    "short" y "shorts", "pantalon" y "Pantalón" o "sueter" y "Suéter" quedan igual que en la app; lo demás se respeta.
    """
    buscado = sin_acentos(texto.strip())
    for tipo in TIPOS_POR_CATEGORIA.get(categoria, []):
        base = sin_acentos(tipo)
        if buscado in (base, base + "s", base + "es", base.rstrip("s"), base.rstrip("s") + "s"):
            return tipo
    return texto


def limpiar_respuesta(datos: dict) -> dict:
    """Deja solo valores válidos para el formulario; lo que no sirva queda en None."""
    def del_catalogo(campo, catalogo):
        return datos.get(campo) if datos.get(campo) in catalogo else None

    categoria = del_catalogo("categoria", EJEMPLOS_CATEGORIA)
    subcategoria = normalizar_tipo(str(datos.get("subcategoria") or "").strip()[:60], categoria)
    abrigo = datos.get("nivel_abrigo")
    return {
        "categoria": categoria,
        "subcategoria": subcategoria[:1].upper() + subcategoria[1:] or None,
        "color_principal": del_catalogo("color_principal", COLORES_ORDENADOS),
        "estampado": del_catalogo("estampado", ESTAMPADOS),
        "estilo": del_catalogo("estilo", ESTILOS),
        "nivel_abrigo": min(max(abrigo, 1), 5) if isinstance(abrigo, int) and not isinstance(abrigo, bool) else None,
        "impermeable": datos.get("impermeable") is True,
    }


def detectar_prenda(contenido: bytes) -> dict:
    """Manda la foto al modelo y devuelve los datos de la prenda que propone."""
    aviso = "La detección automática no está disponible; llena los datos a mano"
    respuesta = preguntar(INSTRUCCIONES, aviso, imagen=contenido, formato=ESQUEMA)
    try:
        return limpiar_respuesta(json.loads(respuesta))
    except ValueError:
        return limpiar_respuesta({})


# ------------------------------------------------
# 3. PARA BUSCARLA EN TIENDAS: lo que hace única a la prenda
# ------------------------------------------------

# En el buscador de tiendas no basta con "Sudadera azul marino": para encontrar ESA prenda hace falta la marca y
# lo que la distingue ("Tom y Jerry", "Air Force 1"). El modelo los lee de la foto; si no se ven, quedan vacíos.
ESQUEMA_TIENDA = {
    "type": "object",
    "properties": {**ESQUEMA["properties"], "marca": {"type": "string"}, "detalles": {"type": "string"}},
    "required": ESQUEMA["required"] + ["marca", "detalles"],
}

INSTRUCCIONES_TIENDA = INSTRUCCIONES + """

La foto se tomó en una tienda para encontrar ESA MISMA prenda en internet. Fíjate en lo que la distingue:
marca: solo si se lee en la prenda o su logo es inconfundible (Nike, Adidas, Zara, Levi's, Puma...). Si no se ve,
deja "". No la adivines.
detalles: de 2 a 6 palabras con lo que hace única a esta prenda y sirve para buscarla: el personaje, el texto o el
logo del estampado (copia el texto tal como se lee), el modelo (por ejemplo "Air Force 1" o "501") o un detalle que
se vea (capucha, cierre, bordado, cuello alto). Si es una prenda básica sin nada especial, deja ""."""

SIN_DATO = {"", "ninguna", "ninguno", "no visible", "no se ve", "desconocida", "desconocido", "n/a", "na", "none", "sin marca"}


def texto_corto(valor, largo: int) -> str | None:
    """El texto limpio y recortado; None si el modelo contestó vacío o algo como "no visible"."""
    texto = " ".join(str(valor or "").split()).strip(" .\"'")[:largo]
    return None if texto.lower() in SIN_DATO else texto


def detectar_para_tienda(contenido: bytes) -> dict:
    """Como detectar_prenda, más la marca y los detalles que distinguen a la prenda (para la búsqueda exacta)."""
    respuesta = preguntar(INSTRUCCIONES_TIENDA, "La IA no está disponible ahora", imagen=contenido, formato=ESQUEMA_TIENDA)
    try:
        datos = json.loads(respuesta)
    except ValueError:
        datos = {}
    return {**limpiar_respuesta(datos), "marca": texto_corto(datos.get("marca"), 40),
            "detalles": texto_corto(datos.get("detalles"), 60)}
