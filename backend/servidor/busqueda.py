"""Búsqueda A* para armar los mejores atuendos.

El problema de búsqueda:
  Estado    el atuendo parcial; empieza con la prenda base.
  Acción    agregar una prenda de una categoría que falta. Si su color no combina con alguna
            prenda del atuendo, la rama se poda (reglas de color de la lógica).
  Objetivo  parte superior, parte inferior y calzado, y abrigo si la lógica deduce que hace falta.

Plano de estilo: cada prenda es un punto (nivel de abrigo, tono del color) y el clima de hoy define
el punto ideal. La distancia al ideal se mide en cuadrícula (manhattan): |Δabrigo| + |Δtono|.

Costo g de agregar una prenda:
  color    armonía con lo que ya llevas: neutro 1, mismo color 2, complementarios 3
  clima    distancia de la prenda al punto ideal
  lógica   +3 si las reglas dicen que la prenda no es apta para el clima (p. ej. ligera con frío)
  ocasión  +20 si no va con la ocasión (p. ej. jeans o tenis en una ocasión formal): vale más que todo
           lo demás junto, así la ocasión siempre gana y una prenda fuera de lugar solo sale si no hay otra
  lluvia   +2 si llueve y es un abrigo que no es impermeable
  estampado +2 si la prenda tiene estampado y ya hay otra estampada en el atuendo (se recargan)

Heurística h: por cada categoría que falta, el costo más bajo posible entre sus prendas (contando
el color como 1 y sin el castigo de estampados). Nunca sobreestima y es consistente, así que A* saca los atuendos completos de la
frontera de menor a mayor costo: si no se detiene en el primero, los primeros son los más baratos.
"""

import heapq
import math
from itertools import count

from servidor.logica import (deducir_de_prenda, es_apta, hechos_de_colores, por_que_combinan, razonar_clima,
                             se_recargan, ventajas_del_atuendo)

REQUERIDAS = ["parte_superior", "parte_inferior", "calzado"]
PENALIZACION_NO_APTA = 3
PENALIZACION_OCASION = 20  # lo más que suman clima, lógica, lluvia, estampados y color es 17
PENALIZACION_LLUVIA = 2
PENALIZACION_ESTAMPADOS = 2

# Tono de cada color, de 1 (muy claro) a 5 (muy oscuro): el segundo eje del plano de estilo.
TONO = {
    "blanco": 1, "beige": 1, "amarillo": 1,
    "gris": 2, "rosa": 2, "naranja": 2,
    "rojo": 3, "verde": 3, "azul": 3, "mezclilla": 3,
    "morado": 4, "cafe": 4,
    "negro": 5, "azul_marino": 5,
}


# ------------------------------------------------
# 1. EL PROBLEMA
# ------------------------------------------------

def punto_ideal(hechos: set[str]) -> tuple[int, int]:
    """(abrigo, tono) que conviene: con frío, abrigada y oscura (absorbe calor); con calor, fresca y clara."""
    if "frio" in hechos:
        return 4, 5
    if "calor" in hechos:
        return 1, 1
    return 2, 3


def distancia_al_ideal(prenda: dict, ideal: tuple[int, int]) -> int:
    return abs(prenda["nivel_abrigo"] - ideal[0]) + abs(TONO[prenda["color_principal"]] - ideal[1])


def costo_par(a: dict, b: dict) -> int:
    """Armonía entre dos prendas que combinan: neutro 1, mismo color 2, complementarios 3."""
    hechos = hechos_de_colores(a["color_principal"], b["color_principal"])
    if "neutro" in hechos:
        return 1
    if "mismo_color" in hechos:
        return 2
    return 3  # complementarios


def costo_sin_color(prenda: dict, problema: dict) -> int:
    """La parte del costo que no depende del atuendo: clima, lógica y lluvia."""
    hechos = problema["hechos"]
    lluvia = "lluvia" in hechos and prenda["categoria"] == "abrigo" and not prenda["impermeable"]
    deducidos = deducir_de_prenda(prenda, hechos)
    return (
        distancia_al_ideal(prenda, problema["ideal"])
        + (PENALIZACION_NO_APTA if "no_apta" in deducidos else 0)
        + (PENALIZACION_OCASION if "fuera_de_ocasion" in deducidos else 0)
        + (PENALIZACION_LLUVIA if lluvia else 0)
    )


def costo_prenda(atuendo: list[dict], prenda: dict, problema: dict) -> int:
    """Costo g de agregar una prenda: su combinación más difícil con lo que ya está, más clima, lógica,
    lluvia y estampados que se recargan."""
    recargado = any(se_recargan(p, prenda) for p in atuendo)
    return (max(costo_par(p, prenda) for p in atuendo) + costo_sin_color(prenda, problema)
            + (PENALIZACION_ESTAMPADOS if recargado else 0))


def combinan_todas(atuendo: list[dict], prenda: dict) -> bool:
    return all(por_que_combinan(p["color_principal"], prenda["color_principal"]) for p in atuendo)


def preparar_problema(base: dict, armario: list[dict], hechos_clima: set[str]) -> dict:
    """Candidatas, categorías que debe cubrir el atuendo, punto ideal y costo mínimo de cada categoría."""
    hechos, _ = razonar_clima(hechos_clima)
    requeridas = REQUERIDAS + (["abrigo"] if "necesita_abrigo" in hechos else [])
    requeridas = [c for c in requeridas if c != base["categoria"]]

    # Disponibles y que combinan con la base. No se descartan por el clima: si no son aptas, cuestan más.
    disponibles = [
        p for p in armario
        if p["id"] != base["id"] and p["estado"] == "disponible"
        and por_que_combinan(base["color_principal"], p["color_principal"])
    ]
    candidatas = [p for p in disponibles if p["categoria"] in requeridas]
    faltantes = [c for c in requeridas if not any(p["categoria"] == c for p in candidatas)]

    problema = {
        "base": base,
        "candidatas": candidatas,
        "accesorios": [p for p in disponibles if p["categoria"] == "accesorio"],
        "necesarias": {base["categoria"]} | (set(requeridas) - set(faltantes)),
        "faltantes": faltantes,
        "ideal": punto_ideal(hechos),
        "hechos": hechos,
    }

    # Para h: el costo más bajo posible de cada categoría (el color cuesta al menos 1).
    problema["minimo"] = {}
    for p in candidatas:
        minimo = 1 + costo_sin_color(p, problema)
        problema["minimo"][p["categoria"]] = min(problema["minimo"].get(p["categoria"], math.inf), minimo)
    return problema


# ------------------------------------------------
# 2. A*
# ------------------------------------------------

def estado(atuendo: list[dict]) -> frozenset:
    """El mismo atuendo armado en otro orden es el mismo estado."""
    return frozenset(p["id"] for p in atuendo)


def faltan(atuendo: list[dict], problema: dict) -> int:
    return len(problema["necesarias"] - {p["categoria"] for p in atuendo})


def h(atuendo: list[dict], problema: dict) -> int:
    ocupadas = {p["categoria"] for p in atuendo}
    return sum(v for c, v in problema["minimo"].items() if c not in ocupadas)


def mejores_atuendos(problema: dict, cantidad: int) -> list[dict]:
    """A* que no se detiene en el primer atuendo completo: sigue hasta juntar `cantidad`.

    La frontera se ordena por f = g + h (si empatan, menor h). Devuelve nodos {atuendo, g}.
    """
    desempate = count()  # evita comparar nodos cuando f y h empatan
    inicio = {"atuendo": [problema["base"]], "g": 0}
    frontera = [(h(inicio["atuendo"], problema), 0, next(desempate), inicio)]
    mejor_g = {estado(inicio["atuendo"]): 0}
    cerrados, encontrados = set(), []

    while frontera and len(encontrados) < cantidad:
        *_, nodo = heapq.heappop(frontera)
        actual = estado(nodo["atuendo"])
        # Se ignoran entradas viejas: ya se expandió ese atuendo o se encontró uno más barato.
        if actual in cerrados or nodo["g"] != mejor_g[actual]:
            continue
        cerrados.add(actual)

        if faltan(nodo["atuendo"], problema) == 0:
            encontrados.append(nodo)
            continue

        ocupadas = {p["categoria"] for p in nodo["atuendo"]}
        for prenda in problema["candidatas"]:
            # Poda: solo categorías que faltan y prendas que combinan con todo el atuendo.
            if prenda["categoria"] in ocupadas or not combinan_todas(nodo["atuendo"], prenda):
                continue
            hijo = {"atuendo": nodo["atuendo"] + [prenda], "g": nodo["g"] + costo_prenda(nodo["atuendo"], prenda, problema)}
            nuevo = estado(hijo["atuendo"])
            if nuevo in cerrados or hijo["g"] >= mejor_g.get(nuevo, math.inf):
                continue
            mejor_g[nuevo] = hijo["g"]
            h_hijo = h(hijo["atuendo"], problema)
            heapq.heappush(frontera, (hijo["g"] + h_hijo, h_hijo, next(desempate), hijo))

    return encontrados


# ------------------------------------------------
# 3. LAS SUGERENCIAS
# ------------------------------------------------

def elegir_accesorio(atuendo: list[dict], problema: dict) -> dict | None:
    """El accesorio que combina con todo el atuendo, va con la ocasión y cuesta menos, si hay alguno.

    Es opcional: si ninguno va con la ocasión, el atuendo queda mejor sin accesorio.
    """
    if any(p["categoria"] == "accesorio" for p in atuendo):
        return None
    opciones = [a for a in problema["accesorios"]
                if combinan_todas(atuendo, a) and es_apta(a, problema["hechos"])]
    return min(opciones, key=lambda a: (costo_prenda(atuendo, a, problema), a["id"]), default=None)


def crear_sugerencia(atuendo: list[dict], costo: int, hechos: set[str]) -> dict:
    """El atuendo como lo muestra la app: cada prenda con por qué combina con la base, y sus ventajas."""
    base = atuendo[0]
    ventajas = ventajas_del_atuendo(atuendo, hechos)
    elementos = [
        {
            "rol": p["categoria"],
            "prenda": p,
            "motivo": por_que_combinan(base["color_principal"], p["color_principal"]) if i > 0 else None,
        }
        for i, p in enumerate(atuendo)
    ]
    return {"elementos": elementos, "costo": costo, "puntuacion": len(ventajas), "ventajas": ventajas}


def recomendar(base: dict, armario: list[dict], hechos_clima: set[str], cantidad: int = 3,
               buscar=mejores_atuendos, con_accesorio: bool = True) -> dict:
    """Los `cantidad` atuendos más baratos según A*, cada uno con un accesorio si alguno combina.

    `buscar` puede ser otro algoritmo de algoritmos.py (BFS, DFS, UCS, Greedy o las heurísticas).
    """
    problema = preparar_problema(base, armario, hechos_clima)

    sugerencias = []
    for nodo in buscar(problema, cantidad):
        if len(nodo["atuendo"]) == 1:
            continue  # nada combina con la base: la app muestra lo que falta en vez de la prenda sola
        accesorio = elegir_accesorio(nodo["atuendo"], problema) if con_accesorio else None
        atuendo = nodo["atuendo"] + ([accesorio] if accesorio else [])
        sugerencias.append(crear_sugerencia(atuendo, nodo["g"], problema["hechos"]))

    avisos = []
    if not es_apta(base, problema["hechos"]):
        avisos.append("La prenda base no es ideal para el clima o la ocasión de hoy")
    if "abrigo" in problema["faltantes"]:
        avisos.append("No tienes un abrigo que combine con tu prenda para este clima")

    return {
        "sugerencias": sugerencias,
        "categorias_faltantes": [c for c in problema["faltantes"] if c != "abrigo"],
        "avisos": avisos,
    }
