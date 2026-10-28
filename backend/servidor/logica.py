"""Lógica proposicional de Secrets of Style: reglas, motor de inferencia y hechos.

Proposiciones (10):
  Clima:    frio, calor, lluvia
  Prenda:   ligera (abrigo 1-2), abrigada (abrigo 3-5), impermeable
  Colores:  neutro, mismo_color, complementarios
  Atuendo:  accesorio
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

# Una prenda es apta si NO se deduce "no_apta".
REGLAS_PRENDA = [
    Regla("Una prenda ligera no sirve con frío", ("frio", "ligera"), "no_apta"),
    Regla("Una prenda abrigada no sirve con calor", ("calor", "abrigada"), "no_apta"),
]

# Se evalúa para cada par de prendas.
REGLAS_COLOR = [
    Regla("combina porque es un color neutro", ("neutro",), "combinan"),
    Regla("mismo color, look monocromático", ("mismo_color",), "combinan"),
    Regla("colores complementarios", ("complementarios",), "combinan"),
]

# Se evalúa para el atuendo completo; cada ventaja suma una estrella.
REGLAS_ATUENDO = [
    Regla("Incluye una prenda impermeable para la lluvia", ("lluvia", "impermeable"), "ventaja_lluvia"),
    Regla("Tiene un contraste de colores complementarios", ("complementarios",), "ventaja_contraste"),
    Regla("Se completa con un accesorio", ("accesorio",), "ventaja_accesorio"),
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


def hechos_de_prenda(prenda: dict) -> set[str]:
    if prenda["categoria"] == "accesorio":
        return set()  # los accesorios no dependen del clima
    hechos = {"ligera" if prenda["nivel_abrigo"] <= 2 else "abrigada"}
    if prenda["impermeable"]:
        hechos.add("impermeable")
    return hechos


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


def es_apta(prenda: dict, hechos_clima: set[str]) -> bool:
    deducidos, _ = inferir(hechos_clima | hechos_de_prenda(prenda), REGLAS_PRENDA)
    return "no_apta" not in deducidos


def por_que_combinan(color_a: str, color_b: str) -> str | None:
    """Explicación de por qué combinan dos colores, o None si no combinan."""
    deducidos, disparadas = inferir(hechos_de_colores(color_a, color_b), REGLAS_COLOR)
    return disparadas[0].nombre if "combinan" in deducidos else None


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

    _, disparadas = inferir(hechos, REGLAS_ATUENDO)
    return [regla.nombre for regla in disparadas]
