"""Lógica proposicional de Secrets of Style: reglas, motor de inferencia y hechos.

Proposiciones (19):
  Clima:      frio, calor, lluvia
  Ocasión:    ocasion_formal, ocasion_deporte (la ocasión "diario" no agrega hechos)
  Prenda:     ligera (abrigo 1-2), abrigada (abrigo 3-5), impermeable, formal, deportiva, urbana, casual
  Colores:    neutro, mismo_color, complementarios
  Estampados: dos_estampados (las dos prendas del par tienen estampado)
  Atuendo:    accesorio, un_estampado, todo_formal, todo_deportivo
"""

from dataclasses import dataclass
from itertools import combinations

# ---------- Umbrales para convertir mediciones en proposiciones ----------

UMBRAL_FRIO_C = 12  # sensación térmica menor → "frio"
UMBRAL_CALOR_C = 27  # sensación térmica mayor → "calor"
UMBRAL_LLUVIA = 40  # probabilidad de lluvia mayor (%) → "lluvia"

# ---------- Hechos fijos sobre colores ----------

COLORES_NEUTROS = {"negro", "blanco", "gris", "beige", "cafe", "azul_marino", "mezclilla"}
COLORES_VIVOS = {"rojo", "naranja", "amarillo", "verde", "azul", "morado", "rosa"}

# Estampado y estilo de cada prenda; los detecta la IA en la foto (vision.py) y la persona los corrige.
ESTAMPADOS = ["liso", "rayas", "cuadros", "floral", "animal", "otro"]
ESTILOS = ["casual", "semiformal", "formal", "deportivo", "urbano"]
ESTILOS_ARREGLADOS = {"formal", "semiformal"}  # cuentan como "formal" para las reglas de ocasión
OCASIONES = ["diario", "formal", "deporte"]

# Pares opuestos en la rueda cromática que se usa en moda.
COMPLEMENTARIOS = {
    frozenset({"rojo", "verde"}),
    frozenset({"azul", "naranja"}),
    frozenset({"amarillo", "morado"}),
    frozenset({"rosa", "verde"}),
}


# ---------- Reglas: cláusulas de Horn  p1 ∧ p2 ∧ ... ∧ pn → q ----------

@dataclass(frozen=True)
class Regla:
    nombre: str  # explicación en lenguaje natural, se muestra al usuario
    si: tuple[str, ...]  # premisas (conjunción)
    entonces: str  # conclusión


REGLAS_CLIMA = [
    Regla("Hace frío: agrega una capa de abrigo", ("frio",), "necesita_abrigo"),
    Regla("Va a llover: agrega una capa exterior", ("lluvia",), "necesita_abrigo"),
]

# Una prenda es apta si NO se deduce "no_apta" (clima) ni "fuera_de_ocasion". Son conclusiones aparte porque
# la búsqueda las paga distinto: una prenda puede fallar por las dos razones y la ocasión pesa más.
REGLAS_PRENDA = [
    Regla("Una prenda ligera no sirve con frío", ("frio", "ligera"), "no_apta"),
    Regla("Una prenda abrigada no sirve con calor", ("calor", "abrigada"), "no_apta"),
    Regla("Una prenda deportiva no va en una ocasión formal", ("ocasion_formal", "deportiva"), "fuera_de_ocasion"),
    Regla("Una prenda urbana no va en una ocasión formal", ("ocasion_formal", "urbana"), "fuera_de_ocasion"),
    Regla("Una prenda casual no va en una ocasión formal", ("ocasion_formal", "casual"), "fuera_de_ocasion"),
    Regla("Una prenda formal no va para hacer deporte", ("ocasion_deporte", "formal"), "fuera_de_ocasion"),
]

# Se evalúa para cada par de prendas.
REGLAS_COLOR = [
    Regla("combina porque es un color neutro", ("neutro",), "combinan"),
    Regla("mismo color, look monocromático", ("mismo_color",), "combinan"),
    Regla("colores complementarios", ("complementarios",), "combinan"),
]

# También por par: dos estampados juntos no se descartan, pero la búsqueda los paga más caros.
REGLAS_ESTAMPADO = [
    Regla("Dos estampados juntos recargan el atuendo", ("dos_estampados",), "recargado"),
]

# Se evalúa para el atuendo completo; cada ventaja suma una estrella.
REGLAS_ATUENDO = [
    Regla("Incluye una prenda impermeable para la lluvia", ("lluvia", "impermeable"), "ventaja_lluvia"),
    Regla("Tiene un contraste de colores complementarios", ("complementarios",), "ventaja_contraste"),
    Regla("Se completa con un accesorio", ("accesorio",), "ventaja_accesorio"),
    Regla("Un solo estampado y lo demás liso: atuendo equilibrado", ("un_estampado",), "ventaja_estampado"),
    Regla("Todo el atuendo es formal, como pide la ocasión", ("ocasion_formal", "todo_formal"), "ventaja_ocasion"),
    Regla("Todo el atuendo es deportivo, listo para moverte", ("ocasion_deporte", "todo_deportivo"), "ventaja_ocasion"),
]


# ---------- Motor de inferencia: encadenamiento hacia adelante ----------

def inferir(hechos: set[str], reglas: list[Regla]) -> tuple[set[str], list[Regla]]:
    """Aplica las reglas hasta que no se pueda deducir nada nuevo.

    Devuelve todos los hechos (iniciales + deducidos) y las reglas que se dispararon,
    en orden, para poder explicar el razonamiento.
    """
    conocidos = set(hechos)
    disparadas: list[Regla] = []

    hubo_cambios = True
    while hubo_cambios:
        hubo_cambios = False
        for regla in reglas:
            premisas_ciertas = all(premisa in conocidos for premisa in regla.si)
            if premisas_ciertas and regla.entonces not in conocidos:
                conocidos.add(regla.entonces)
                disparadas.append(regla)
                hubo_cambios = True

    return conocidos, disparadas


# ---------- De mediciones a hechos ----------

def hechos_del_clima(sensacion_c: float, probabilidad_lluvia: int, codigo_clima: int) -> set[str]:
    hechos = set()
    if sensacion_c < UMBRAL_FRIO_C:
        hechos.add("frio")
    if sensacion_c > UMBRAL_CALOR_C:
        hechos.add("calor")
    # Códigos WMO 51-67 y 80-99 son llovizna, lluvia, chubascos o tormenta.
    if probabilidad_lluvia > UMBRAL_LLUVIA or 51 <= codigo_clima <= 67 or 80 <= codigo_clima <= 99:
        hechos.add("lluvia")
    return hechos


def hechos_de_ocasion(ocasion: str) -> set[str]:
    return {f"ocasion_{ocasion}"} if ocasion in ("formal", "deporte") else set()


def hechos_de_prenda(prenda: dict) -> set[str]:
    hechos = set()
    if prenda.get("estilo") in ESTILOS_ARREGLADOS:
        hechos.add("formal")
    if prenda.get("estilo") == "deportivo":
        hechos.add("deportiva")
    if prenda.get("estilo") == "urbano":
        hechos.add("urbana")
    if prenda.get("estilo") == "casual":
        hechos.add("casual")
    if prenda["categoria"] == "accesorio":
        return hechos  # los accesorios dependen de la ocasión, pero no del clima
    hechos.add("ligera" if prenda["nivel_abrigo"] <= 2 else "abrigada")
    if prenda["impermeable"]:
        hechos.add("impermeable")
    return hechos


def es_estampada(prenda: dict) -> bool:
    return prenda.get("estampado") not in (None, "liso")


def hechos_de_colores(color_a: str, color_b: str) -> set[str]:
    hechos = set()
    if color_a in COLORES_NEUTROS or color_b in COLORES_NEUTROS:
        hechos.add("neutro")
    if color_a == color_b:
        hechos.add("mismo_color")
    if frozenset({color_a, color_b}) in COMPLEMENTARIOS:
        hechos.add("complementarios")
    return hechos


# ---------- Consultas a la base de conocimiento ----------

def razonar_clima(hechos: set[str]) -> tuple[set[str], list[str]]:
    """Devuelve los hechos del clima con sus deducciones y la explicación de cada una."""
    deducidos, disparadas = inferir(hechos, REGLAS_CLIMA)
    return deducidos, [regla.nombre for regla in disparadas]


def deducir_de_prenda(prenda: dict, hechos: set[str]) -> set[str]:
    return inferir(hechos | hechos_de_prenda(prenda), REGLAS_PRENDA)[0]


def es_apta(prenda: dict, hechos: set[str]) -> bool:
    return not {"no_apta", "fuera_de_ocasion"} & deducir_de_prenda(prenda, hechos)


def por_que_combinan(color_a: str, color_b: str) -> str | None:
    """Explicación de por qué combinan dos colores, o None si no combinan."""
    deducidos, disparadas = inferir(hechos_de_colores(color_a, color_b), REGLAS_COLOR)
    return disparadas[0].nombre if "combinan" in deducidos else None


def se_recargan(prenda_a: dict, prenda_b: dict) -> bool:
    """True si las reglas deducen que juntas recargan el atuendo (las dos tienen estampado)."""
    hechos = {"dos_estampados"} if es_estampada(prenda_a) and es_estampada(prenda_b) else set()
    deducidos, _ = inferir(hechos, REGLAS_ESTAMPADO)
    return "recargado" in deducidos


def ventajas_del_atuendo(prendas: list[dict], hechos_clima: set[str]) -> list[str]:
    """Aplica las reglas de atuendo y devuelve el nombre de cada ventaja deducida."""
    pares = combinations([p["color_principal"] for p in prendas], 2)

    hechos = set(hechos_clima)
    if any(p["impermeable"] for p in prendas):
        hechos.add("impermeable")
    if any("complementarios" in hechos_de_colores(a, b) for a, b in pares):
        hechos.add("complementarios")
    if any(p["categoria"] == "accesorio" for p in prendas):
        hechos.add("accesorio")
    if sum(es_estampada(p) for p in prendas) == 1:
        hechos.add("un_estampado")
    ropa = [p for p in prendas if p["categoria"] != "accesorio"]
    if all(p.get("estilo") in ESTILOS_ARREGLADOS for p in ropa):
        hechos.add("todo_formal")
    if all(p.get("estilo") == "deportivo" for p in ropa):
        hechos.add("todo_deportivo")

    _, disparadas = inferir(hechos, REGLAS_ATUENDO)
    return [regla.nombre for regla in disparadas]
