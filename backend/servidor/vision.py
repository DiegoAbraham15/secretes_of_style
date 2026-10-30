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

from servidor.logica import COLORES_NEUTROS, COLORES_VIVOS, ESTAMPADOS, ESTILOS
from servidor.ollama import preguntar

# ------------------------------------------------
# 1. LO QUE EL MODELO PUEDE CONTESTAR
# ------------------------------------------------

# Mismas categorías que principal.CATEGORIAS, con ejemplos para el prompt.
EJEMPLOS_CATEGORIA = {
    "parte_superior": "blusa, playera, camisa, top, suéter, sudadera",
    "parte_inferior": "pantalón, jeans, falda, short",
    "calzado": "tenis, zapatos, botas, botines, sandalias",
    "abrigo": "chamarra, abrigo, gabardina, chaleco, impermeable",
    "accesorio": "bolsa, gorra, sombrero, bufanda, cinturón, lentes, reloj",
}
COLORES = sorted(COLORES_NEUTROS | COLORES_VIVOS)

ESQUEMA = {
    "type": "object",
    "properties": {
        "categoria": {"type": "string", "enum": list(EJEMPLOS_CATEGORIA)},
        "subcategoria": {"type": "string"},
        "color_principal": {"type": "string", "enum": COLORES},
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
subcategoria: el tipo de prenda en español, en una o dos palabras (por ejemplo "Blusa", "Jeans", "Botines").
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

def limpiar_respuesta(datos: dict) -> dict:
    """Deja solo valores válidos para el formulario; lo que no sirva queda en None."""
    def del_catalogo(campo, catalogo):
        return datos.get(campo) if datos.get(campo) in catalogo else None

    subcategoria = str(datos.get("subcategoria") or "").strip()[:60]
    abrigo = datos.get("nivel_abrigo")
    return {
        "categoria": del_catalogo("categoria", EJEMPLOS_CATEGORIA),
        "subcategoria": subcategoria[:1].upper() + subcategoria[1:] or None,
        "color_principal": del_catalogo("color_principal", COLORES),
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
