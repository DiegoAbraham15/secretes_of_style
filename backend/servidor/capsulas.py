"""Cápsulas de guardarropa: pocas prendas de tu armario que juntas arman muchos looks.

Escenarios: "Cápsula del mes" (15 prendas) o "Maleta de viaje" (10 prendas), con el clima y la ocasión.

Un LOOK VÁLIDO es parte de arriba + parte de abajo + calzado (+ abrigo si la lógica deduce que hace falta) donde
todas las parejas combinan por color (logica.por_que_combinan) y no hay dos estampados juntos (se_recargan). Solo
entran prendas disponibles y aptas para el clima y la ocasión (es_apta).

El problema es combinatorio (elegir 15 de 40 prendas tiene millones de opciones), así que se resuelve en dos pasos:
  1. GREEDY: se agrega una por una la prenda que más looks nuevos aporta, respetando la cuota de cada categoría.
     Mientras todavía no hay looks completos, cuenta también las parejas que combinan, para no elegir a ciegas.
     En un empate gana la neutra, la que va con tu colorimetría y la que más usas.
  2. BÚSQUEDA LOCAL (hill climbing): se intercambia cada prenda elegida por otra de su categoría mientras el número
     de looks suba. Nunca empeora lo que encontró el greedy y siempre da lo mismo con el mismo armario.
  3. ACENTOS: solo con neutros salen muchos looks pero aburridos. Si faltan colores de acento (2 en la del mes, 1 en
     la maleta), se cambia una neutra por la de color que menos looks quite, si no se pierde más del 15 %.
"""

from itertools import combinations, product

from servidor import colorimetria
from servidor.logica import COLORES_NEUTROS, es_apta, por_que_combinan, razonar_clima, se_recargan

ESCENARIOS = {
    "mensual": {"nombre": "Cápsula del mes", "acentos": 2,
                "cuotas": {"parte_superior": 5, "parte_inferior": 4, "calzado": 3, "abrigo": 2, "accesorio": 1}},
    "viaje": {"nombre": "Maleta de viaje", "acentos": 1,
              "cuotas": {"parte_superior": 4, "parte_inferior": 3, "calzado": 2, "abrigo": 1}},
}
PERDIDA_ACEPTABLE = 0.15  # para meter un color de acento se acepta perder hasta el 15 % de los looks
NUCLEO = ["parte_superior", "parte_inferior", "calzado"]
META_LOOKS = 25
MAXIMO_LOOKS_EN_RESPUESTA = 60
VUELTAS_MAXIMAS = 30


class Combinaciones:
    """Qué parejas de prendas combinan, calculado una sola vez (la lógica de colores es lo más caro)."""

    def __init__(self, prendas: list[dict]):
        self.pareja = {}
        for a, b in combinations(prendas, 2):
            ok = bool(por_que_combinan(a["color_principal"], b["color_principal"])) and not se_recargan(a, b)
            self.pareja[(a["id"], b["id"])] = self.pareja[(b["id"], a["id"])] = ok

    def todas(self, prendas) -> bool:
        return all(self.pareja.get((a["id"], b["id"]), False) for a, b in combinations(prendas, 2))


def looks_de(seleccion: list[dict], combina: Combinaciones, con_abrigo: bool) -> list[tuple[dict, ...]]:
    """Todos los looks válidos que se arman con la selección."""
    por_categoria = {c: [p for p in seleccion if p["categoria"] == c] for c in NUCLEO + ["abrigo"]}
    looks = []
    for arriba, abajo, calzado in product(*(por_categoria[c] for c in NUCLEO)):
        base = (arriba, abajo, calzado)
        if not combina.todas(base):
            continue
        if con_abrigo:
            looks += [base + (abrigo,) for abrigo in por_categoria["abrigo"] if combina.todas(base + (abrigo,))]
        else:
            looks.append(base)
    return looks


def puntaje(seleccion: list[dict], combina: Combinaciones, con_abrigo: bool) -> tuple[int, int]:
    """(looks, parejas que combinan entre categorías distintas): lo segundo guía al greedy al principio."""
    parejas = sum(1 for a, b in combinations(seleccion, 2)
                  if a["categoria"] != b["categoria"] and combina.pareja.get((a["id"], b["id"])))
    return len(looks_de(seleccion, combina, con_abrigo)), parejas


def preferencia(prenda: dict, perfil_color: dict | None, usos: dict) -> tuple:
    """Desempate: neutra, que vaya con la colorimetría, la más usada y, al final, el id (para que sea repetible)."""
    color = colorimetria.nivel_de_color(prenda["color_principal"], perfil_color)
    return (prenda["color_principal"] in COLORES_NEUTROS, {"favorece": 1, "neutral": 0, "evitar": -1}[color],
            usos.get(prenda["id"], 0), -prenda["id"])


def armar(armario: list[dict], escenario: str, dias_de_clima: list[set[str]], perfil_color: dict | None = None,
          usos: dict | None = None) -> dict:
    """La cápsula: dias_de_clima son los hechos de cada día (uno para la del mes, uno por día en un viaje)."""
    usos = usos or {}
    cuotas = dict(ESCENARIOS[escenario]["cuotas"])
    razonados = [razonar_clima(hechos)[0] for hechos in dias_de_clima] or [set()]
    con_abrigo = any("necesita_abrigo" in hechos for hechos in razonados)
    # Apta si sirve al menos un día del viaje (en uno frío entra la chamarra; en uno de calor, la playera).
    candidatas = [p for p in armario if p["estado"] == "disponible" and p["categoria"] in cuotas
                  and any(es_apta(p, hechos) for hechos in razonados)]
    combina = Combinaciones(candidatas)

    # 1. Greedy
    seleccion: list[dict] = []
    while True:
        libres = [p for p in candidatas if p not in seleccion and cuotas.get(p["categoria"], 0) > 0]
        if not libres:
            break
        actual = puntaje(seleccion, combina, con_abrigo)
        mejor = max(libres, key=lambda p: (tuple(n - a for n, a in zip(puntaje(seleccion + [p], combina, con_abrigo), actual)),
                                           preferencia(p, perfil_color, usos)))
        seleccion.append(mejor)
        cuotas[mejor["categoria"]] -= 1
    greedy = len(looks_de(seleccion, combina, con_abrigo))

    # 2. Búsqueda local: cambiar una prenda por otra de su categoría mientras suban los looks.
    for _ in range(VUELTAS_MAXIMAS):
        mejoro = False
        for i, elegida in enumerate(list(seleccion)):
            base = len(looks_de(seleccion, combina, con_abrigo))
            for otra in candidatas:
                if otra in seleccion or otra["categoria"] != elegida["categoria"]:
                    continue
                prueba = seleccion[:i] + [otra] + seleccion[i + 1:]
                if len(looks_de(prueba, combina, con_abrigo)) > base:
                    seleccion, mejoro = prueba, True
                    break
        if not mejoro:
            break

    # 3. Acentos: color sin perder demasiados looks.
    for _ in range(ESCENARIOS[escenario]["acentos"] - sum(p["color_principal"] not in COLORES_NEUTROS for p in seleccion)):
        actuales = len(looks_de(seleccion, combina, con_abrigo))
        opciones = []
        for i, elegida in enumerate(seleccion):
            if elegida["color_principal"] not in COLORES_NEUTROS:
                continue
            for otra in candidatas:
                if otra not in seleccion and otra["categoria"] == elegida["categoria"] and otra["color_principal"] not in COLORES_NEUTROS:
                    prueba = seleccion[:i] + [otra] + seleccion[i + 1:]
                    opciones.append((len(looks_de(prueba, combina, con_abrigo)), preferencia(otra, perfil_color, usos), prueba))
        if not opciones:
            break
        mejores_looks, _, mejor = max(opciones, key=lambda o: (o[0], o[1]))
        if mejores_looks < actuales * (1 - PERDIDA_ACEPTABLE):
            break
        seleccion = mejor

    looks = looks_de(seleccion, combina, con_abrigo)
    return {
        "escenario": escenario,
        "nombre": ESCENARIOS[escenario]["nombre"],
        "prendas": sorted(seleccion, key=lambda p: (list(ESCENARIOS["mensual"]["cuotas"]).index(p["categoria"]), p["id"])),
        "looks": len(looks),
        "looks_greedy": greedy,
        "combinaciones": [[p["id"] for p in look] for look in looks[:MAXIMO_LOOKS_EN_RESPUESTA]],
        "con_abrigo": con_abrigo,
        "neutros": sum(p["color_principal"] in COLORES_NEUTROS for p in seleccion),
        "acentos": sum(p["color_principal"] not in COLORES_NEUTROS for p in seleccion),
        "meta": META_LOOKS,
        "sugerencia": None if len(looks) >= META_LOOKS else que_falta(seleccion, candidatas, armario, combina, con_abrigo),
    }


def que_falta(seleccion, candidatas, armario, combina, con_abrigo) -> str:
    """Cuando no se llega a la meta: qué prenda de tu armario (fuera de cuota) sumaría más, o qué comprar."""
    actual = len(looks_de(seleccion, combina, con_abrigo))
    mejor, ganancia = None, 0
    for prenda in candidatas:
        if prenda in seleccion:
            continue
        nuevos = len(looks_de(seleccion + [prenda], combina, con_abrigo)) - actual
        if nuevos > ganancia:
            mejor, ganancia = prenda, nuevos
    if mejor:
        nombre = mejor.get("subcategoria") or mejor["categoria"].replace("_", " ")
        return f"Con tu {nombre.lower()} también llegarías a {actual + ganancia} looks."
    faltan = [c for c in NUCLEO if sum(p["categoria"] == c for p in seleccion) < 2]
    que = {"parte_superior": "Una parte de arriba", "parte_inferior": "Una parte de abajo",
           "calzado": "Un par de zapatos"}[faltan[0] if faltan else "parte_inferior"]
    return f"{que} en un color neutro (negro, blanco, gris o beige) multiplicaría tus looks."
