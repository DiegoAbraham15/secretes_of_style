"""Colorimetría personal: la estación de color de la persona (Primavera, Verano, Otoño o Invierno) y su paleta.

Tres medidas deciden la estación, como en el análisis de color clásico:
  calidez      subtono de la piel: cálido (dorado), frío (rosado) o neutro.
  profundidad  qué tan clara o profunda es la persona (piel y cabello).
  contraste    diferencia entre el cabello/ojos y la piel.
Reglas:
  cálido + claro → Primavera · cálido + profundo/medio → Otoño
  frío + contraste alto o profundo → Invierno · frío + suave → Verano
  neutro: el contraste alto lleva a Invierno, lo profundo a Otoño, lo claro y suave a Verano; si no, Primavera.

Dos caminos que se combinan:
  1. Cuestionario de 5 preguntas visuales (venas, sol, metales, cabello y contraste): cada respuesta suma puntos.
  2. Selfie: el motor (SegFormer) marca rostro y cabello y mide su color en L*a*b*. El subtono sale del ángulo de
     tono de la piel (h = atan2(b*, a*)), la profundidad de su luz (L*) y el contraste de la diferencia de luz con
     el cabello. La foto no se guarda. La selfie pesa el doble que el cuestionario en la calidez.

Integración: ajustar() marca cada look según las prendas que van cerca del rostro (arriba, abrigo y accesorio):
"favorece" si están en la paleta, "evitar" si están en los colores a evitar. Con priorizar, también los reordena.
"""

import math

from servidor.aprendizaje import AJUSTE_MAXIMO

# Pregunta → opción → (calidez, profundidad, contraste). Las opciones llevan un color de muestra para la app.
PREGUNTAS = [
    {"clave": "venas", "pregunta": "¿De qué color se ven las venas de tu muñeca con luz natural?", "opciones": [
        {"valor": "azul", "etiqueta": "Azules o moradas", "hex": "#5B6FB5", "puntos": (-2, 0, 0)},
        {"valor": "verde", "etiqueta": "Verdes", "hex": "#5E8C61", "puntos": (2, 0, 0)},
        {"valor": "ambas", "etiqueta": "No sé / ambas", "hex": "#7A8C8C", "puntos": (0, 0, 0)}]},
    {"clave": "sol", "pregunta": "¿Qué te pasa con el sol?", "opciones": [
        {"valor": "se_quema", "etiqueta": "Me quemo y casi no me bronceo", "hex": "#F2B8A0", "puntos": (-1, -1, 0)},
        {"valor": "ambas", "etiqueta": "Me quemo y luego me bronceo", "hex": "#D99C73", "puntos": (0, 0, 0)},
        {"valor": "se_broncea", "etiqueta": "Me bronceo fácil", "hex": "#A86B42", "puntos": (1, 1, 0)}]},
    {"clave": "metales", "pregunta": "¿Qué joyería te ilumina más la cara?", "opciones": [
        {"valor": "plata", "etiqueta": "Plata", "hex": "#C0C0C8", "puntos": (-2, 0, 0)},
        {"valor": "oro", "etiqueta": "Oro", "hex": "#D4AF37", "puntos": (2, 0, 0)},
        {"valor": "ambos", "etiqueta": "Las dos", "hex": "#CBB580", "puntos": (0, 0, 0)}]},
    {"clave": "cabello", "pregunta": "¿Cuál es tu color de cabello natural?", "opciones": [
        {"valor": "claro", "etiqueta": "Rubio o castaño claro", "hex": "#D9B77A", "puntos": (0, -2, 0)},
        {"valor": "castano", "etiqueta": "Castaño", "hex": "#7A5230", "puntos": (0, 0, 0)},
        {"valor": "oscuro", "etiqueta": "Castaño oscuro o negro", "hex": "#2A1E1A", "puntos": (0, 2, 0)},
        {"valor": "pelirrojo", "etiqueta": "Pelirrojo o cobrizo", "hex": "#A5432A", "puntos": (2, 0, 0)}]},
    {"clave": "contraste", "pregunta": "¿Qué tanto contrastan tu cabello y tus ojos con tu piel?", "opciones": [
        {"valor": "alto", "etiqueta": "Mucho", "hex": "#1A1A1A", "puntos": (0, 0, 2)},
        {"valor": "medio", "etiqueta": "Algo", "hex": "#8A7060", "puntos": (0, 0, 0)},
        {"valor": "bajo", "etiqueta": "Poco", "hex": "#D8C4B0", "puntos": (0, 0, -2)}]},
]
OPCIONES = {p["clave"]: {o["valor"]: o["puntos"] for o in p["opciones"]} for p in PREGUNTAS}

# Cada estación: los colores del catálogo que le favorecen, los que conviene evitar y muestras de referencia.
ESTACIONES = {
    "primavera": {
        "nombre": "Primavera", "descripcion": "Colores cálidos, claros y luminosos.",
        "paleta": ["amarillo", "naranja", "verde", "azul", "beige", "rosa"], "evitar": ["negro", "gris", "morado"],
        "paleta_hex": ["#FFD966", "#FFA07A", "#FF7F50", "#F4C430", "#98D982", "#40E0D0", "#6CB4EE", "#F5DEB3",
                       "#E8B98A", "#FFB6C1", "#C9A66B", "#FFF1D6"]},
    "verano": {
        "nombre": "Verano", "descripcion": "Colores fríos, suaves y empolvados.",
        "paleta": ["rosa", "azul", "gris", "azul_marino", "morado", "blanco"], "evitar": ["naranja", "amarillo", "negro", "cafe"],
        "paleta_hex": ["#E8B4C8", "#C9A0DC", "#B0C4DE", "#7BA7CC", "#9AB0C4", "#A3A9C8", "#D8BFD8", "#9FB8AD",
                       "#C0C0C8", "#4F6D8F", "#F2F2F5", "#B784A7"]},
    "otono": {
        "nombre": "Otoño", "descripcion": "Colores cálidos, profundos y terrosos.",
        "paleta": ["cafe", "verde", "naranja", "beige", "amarillo", "rojo"], "evitar": ["negro", "blanco", "rosa", "gris", "morado"],
        "paleta_hex": ["#8B4513", "#A0522D", "#CC7722", "#DAA520", "#6B8E23", "#556B2F", "#B7410E", "#C19A6B",
                       "#E2C290", "#800020", "#2E5E4E", "#D2691E"]},
    "invierno": {
        "nombre": "Invierno", "descripcion": "Colores fríos, intensos y de alto contraste.",
        "paleta": ["negro", "blanco", "rojo", "azul_marino", "azul", "morado", "rosa", "gris"],
        "evitar": ["beige", "naranja", "cafe", "amarillo"],
        "paleta_hex": ["#000000", "#FFFFFF", "#DC143C", "#1E2A55", "#0047AB", "#7C3AED", "#FF1493", "#36454F",
                       "#008080", "#C0C0C8", "#800080", "#E0115F"]},
}

CERCA_DEL_ROSTRO = {"parte_superior", "abrigo", "accesorio"}
AJUSTE = AJUSTE_MAXIMO / 2  # con priorizar: lo que suma o resta cada prenda cerca del rostro


# ------------------------------------------------
# 1. LAS MEDIDAS
# ------------------------------------------------

def puntos_del_cuestionario(respuestas: dict) -> tuple[int, int, int]:
    """(calidez, profundidad, contraste) sumando las 5 respuestas. KeyError si falta alguna o no existe."""
    totales = [0, 0, 0]
    for pregunta in OPCIONES:
        for i, valor in enumerate(OPCIONES[pregunta][respuestas[pregunta]]):
            totales[i] += valor
    return tuple(totales)


def medidas_de_selfie(medidas: dict) -> dict:
    """Del color de la piel y el cabello (L*a*b*) al subtono, la profundidad y el contraste."""
    luz, a, b = medidas["piel"]["lab"]
    tono = math.degrees(math.atan2(b, a))  # la piel va de ~40° (rosada) a ~70° (dorada)
    subtono = "calido" if tono >= 60 else "frio" if tono <= 50 else "neutro"
    profundidad = "profundo" if luz < 55 else "claro" if luz > 70 else "medio"
    contraste = "medio"
    if medidas.get("cabello"):
        diferencia = abs(medidas["cabello"]["lab"][0] - luz)
        contraste = "alto" if diferencia >= 45 else "bajo" if diferencia <= 25 else "medio"
    return {"subtono": subtono, "profundidad": profundidad, "contraste": contraste, "tono_piel": round(tono, 1)}


def estacion_de(subtono: str, profundidad: str, contraste: str) -> str:
    if subtono == "calido":
        return "primavera" if profundidad == "claro" else "otono"
    if subtono == "frio":
        return "invierno" if contraste == "alto" or profundidad == "profundo" else "verano"
    if contraste == "alto":
        return "invierno"
    if profundidad == "profundo":
        return "otono"
    if profundidad == "claro" and contraste == "bajo":
        return "verano"
    return "primavera"


def diagnosticar(respuestas: dict | None, selfie: dict | None) -> dict:
    """Junta el cuestionario y la selfie (la selfie pesa el doble en la calidez y manda en luz y contraste)."""
    calidez, profundidad_q, contraste_q = puntos_del_cuestionario(respuestas) if respuestas else (0, 0, 0)
    medidas = medidas_de_selfie(selfie) if selfie else None
    if medidas:
        calidez += {"calido": 4, "frio": -4, "neutro": 0}[medidas["subtono"]]
    subtono = "calido" if calidez > 1 else "frio" if calidez < -1 else "neutro"
    profundidad = medidas["profundidad"] if medidas else "profundo" if profundidad_q >= 1 else "claro" if profundidad_q <= -1 else "medio"
    contraste = medidas["contraste"] if medidas else "alto" if contraste_q >= 2 else "bajo" if contraste_q <= -2 else "medio"
    clave = estacion_de(subtono, profundidad, contraste)
    estacion = ESTACIONES[clave]
    return {
        "estacion": clave, "nombre": estacion["nombre"], "descripcion": estacion["descripcion"],
        "subtono": subtono, "profundidad": profundidad, "contraste": contraste,
        "metodo": "ambos" if respuestas and selfie else "selfie" if selfie else "cuestionario",
        "paleta": estacion["paleta"], "evitar": estacion["evitar"], "paleta_hex": estacion["paleta_hex"],
        "medidas": medidas,
    }


# ------------------------------------------------
# 2. EN LOS LOOKS
# ------------------------------------------------

def nivel_de_color(color: str, perfil: dict | None) -> str:
    if not perfil:
        return "neutral"
    return "favorece" if color in perfil["paleta"] else "evitar" if color in perfil["evitar"] else "neutral"


def marca_de(prendas: list[dict], perfil: dict) -> tuple[dict, int]:
    """La insignia de un look y su balance (+ por cada prenda cerca del rostro en la paleta, − en evitar)."""
    cerca = [p for p in prendas if p["categoria"] in CERCA_DEL_ROSTRO]
    favorecen = [p for p in cerca if p["color_principal"] in perfil["paleta"]]
    evitan = [p for p in cerca if p["color_principal"] in perfil["evitar"]]
    if evitan and len(evitan) >= len(favorecen):
        nivel, detalle = "evitar", "Lleva cerca del rostro colores fuera de tu paleta"
    elif favorecen:
        nivel, detalle = "favorece", f"Va con tu paleta de {ESTACIONES[perfil['estacion']]['nombre']}"
    else:
        nivel, detalle = "neutral", None
    return {"nivel": nivel, "detalle": detalle}, len(favorecen) - len(evitan)


def ajustar(sugerencias: list[dict], perfil: dict | None) -> list[dict]:
    """Marca cada look y, si la persona lo pidió (priorizar), reordena por costo_final con el balance de color."""
    if not perfil:
        return sugerencias
    for sugerencia in sugerencias:
        marca, balance = marca_de([e["prenda"] for e in sugerencia["elementos"]], perfil)
        sugerencia["colorimetria"] = marca
        if perfil.get("priorizar") and "costo_final" in sugerencia:
            sugerencia["costo_final"] -= AJUSTE * balance
    if perfil.get("priorizar"):
        sugerencias = sorted(sugerencias, key=lambda s: (s.get("costo_final", s["costo"]), s["costo"]))
    return sugerencias
