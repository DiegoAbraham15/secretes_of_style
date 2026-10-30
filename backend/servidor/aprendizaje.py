"""Perceptrón y parecido con los looks con corazón: reordenan los atuendos que propone A* según los gustos.

El modelo: s = b + w·x
  x  características del atuendo, todas de 0 a 1 (ver caracteristicas_de)
  w  un peso por característica; b es el sesgo. Son propios de cada persona.
  s  mayor que 0: cree que le gusta; menor que 0: cree que no.

Regla de aprendizaje, con y = +1 (le dio corazón) o -1 (se le mostró y no le dio corazón):
  si y·s <= 0 (se equivocó):  w_i <- w_i + η·y·x_i   y   b <- b + η·y

Parecido: el perceptrón necesita varios votos para generalizar, y los looks sin corazón suelen ser casi iguales
al que gustó. Por eso también se mide la distancia manhattan de cada candidato al look con corazón más cercano,
la misma idea del plano de estilo de la búsqueda. El puntaje final es el promedio de las dos señales.

Quién decide qué:
  La lógica dice qué es válido, A* propone los mejores y el perceptrón solo desempata entre candidatos
  cercanos. Su ajuste mueve el costo a lo mucho ±1.25, o sea 2.5 entre dos atuendos: menos que el +3 del
  clima y que el +20 de la ocasión. Con pesos en 0, el orden es exactamente el de A*.
"""

from itertools import combinations

from servidor.busqueda import TONO
from servidor.logica import COLORES_NEUTROS, ESTILOS, es_estampada, hechos_de_colores

TASA = 0.25  # η: cuánto se mueven los pesos en cada corrección
EPOCAS = 10  # veces que se repasan los votos al entrenar
CANDIDATOS = 12  # atuendos que A* propone para elegir los que se muestran
AJUSTE_MAXIMO = 1.25  # debe quedar por debajo de la mitad de PENALIZACION_NO_APTA (ver el docstring)


# Arranque en frío: lo que dice el cuestionario se vuelve el punto de partida del perceptrón, para que los
# primeros atuendos ya vayan con la persona. Cada respuesta suma estos pesos; lo que no dice nada no suma.
# La pregunta de accesorios no está aquí: no pasa por el modelo, decide si el atuendo lleva accesorio.
PESOS_DE_RESPUESTA = {
    "paleta": {
        "sin_preferencia": {},
        "neutros": {"neutros": 1.0},
        "vivos": {"neutros": -1.0},
        "oscuros": {"tono": 1.0},
        "claros": {"tono": -1.0},
    },
    "ropa": {
        "sin_preferencia": {},
        "casual": {"estilo_casual": 1.0, "estilo_formal": -0.5},
        "urbano": {"estilo_urbano": 1.0, "estilo_formal": -0.5},
        "arreglado": {"estilo_formal": 1.0, "estilo_semiformal": 1.0, "estilo_deportivo": -0.5},
        "deportiva": {"estilo_deportivo": 1.0, "estilo_casual": 0.5, "estilo_formal": -1.0},
    },
    "estampados": {"encantan": {"estampado": 1.0}, "uno": {}, "liso": {"estampado": -1.0}},
}
ACCESORIOS = ["casi_siempre", "a_veces", "casi_nunca"]
RESPUESTA_POR_DEFECTO = {"paleta": "sin_preferencia", "ropa": "sin_preferencia", "estampados": "uno", "accesorios": "a_veces"}


# ------------------------------------------------
# 1. DEL ATUENDO A SUS CARACTERÍSTICAS
# ------------------------------------------------

def caracteristicas_de(atuendo: list[dict]) -> dict[str, float]:
    """El vector x del atuendo. Es un diccionario para que agregar una característica no rompa los pesos guardados."""
    ropa = [p for p in atuendo if p["categoria"] != "accesorio"] or atuendo
    tonos = [TONO[p["color_principal"]] for p in atuendo]
    pares = [hechos_de_colores(a["color_principal"], b["color_principal"]) for a, b in combinations(atuendo, 2)]

    caracteristicas = {
        "neutros": sum(p["color_principal"] in COLORES_NEUTROS for p in atuendo) / len(atuendo),
        "contraste": (max(tonos) - min(tonos)) / 4,
        "tono": (sum(tonos) / len(tonos) - 1) / 4,
        "complementarios": float(any("complementarios" in par for par in pares)),
        "monocromo": sum("mismo_color" in par for par in pares) / len(pares) if pares else 0.0,
        "abrigo": (sum(p["nivel_abrigo"] for p in ropa) / len(ropa) - 1) / 4,
        "estampado": sum(es_estampada(p) for p in atuendo) / len(atuendo),
        "accesorio": float(any(p["categoria"] == "accesorio" for p in atuendo)),
    }
    for estilo in ESTILOS:
        caracteristicas[f"estilo_{estilo}"] = sum(p.get("estilo") == estilo for p in ropa) / len(ropa)
    return caracteristicas


def firma_de(prenda_ids: list[int]) -> str:
    """Identifica un atuendo por sus prendas, sin importar el orden: '3-16-28'."""
    return "-".join(str(i) for i in sorted(prenda_ids))


# ------------------------------------------------
# 2. EL PERCEPTRÓN
# ------------------------------------------------

def puntuar(pesos: dict[str, float], x: dict[str, float]) -> float:
    return pesos.get("sesgo", 0.0) + sum(pesos.get(nombre, 0.0) * valor for nombre, valor in x.items())


def ajustar(pesos: dict[str, float], x: dict[str, float], y: int) -> None:
    """Regla del perceptrón: solo aprende si se equivocó."""
    if y * puntuar(pesos, x) <= 0:
        pesos["sesgo"] = pesos.get("sesgo", 0.0) + TASA * y
        for nombre, valor in x.items():
            pesos[nombre] = pesos.get(nombre, 0.0) + TASA * y * valor


def pesos_iniciales(preferencias: dict) -> dict[str, float]:
    """Suma los pesos de las respuestas del cuestionario. Sin respuestas, todo queda en cero."""
    pesos: dict[str, float] = {}
    for pregunta, respuestas in PESOS_DE_RESPUESTA.items():
        for nombre, valor in respuestas.get(preferencias.get(pregunta), {}).items():
            pesos[nombre] = pesos.get(nombre, 0.0) + valor
    return pesos


def entrenar(votos: list[dict], iniciales: dict[str, float] | None = None) -> dict[str, float]:
    """Repasa los votos en orden, EPOCAS veces, desde los pesos del cuestionario.

    Se entrena con todos para que un voto cambiado no deje rastro del anterior.
    """
    pesos = dict(iniciales or {})
    for _ in range(EPOCAS):
        for voto in votos:
            ajustar(pesos, voto["caracteristicas"], voto["me_gusta"])
    return pesos


# ------------------------------------------------
# 3. REORDENAR LO QUE PROPUSO A*
# ------------------------------------------------

def distancia(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(abs(a[nombre] - b.get(nombre, 0.0)) for nombre in a)


def escalar(valores: list[float]) -> list[float]:
    """Lleva los valores de -1 a +1: el mayor vale +1, el menor -1 y los demás en proporción."""
    alto, bajo = max(valores, default=0.0), min(valores, default=0.0)
    centro, mitad = (alto + bajo) / 2, (alto - bajo) / 2 or 1.0  # si todos valen igual, quedan en 0
    return [(valor - centro) / mitad for valor in valores]


def reordenar(sugerencias: list[dict], pesos: dict[str, float], votos: dict[str, int], gustados: tuple | list = ()) -> list[dict]:
    """Ordena por costo_final = costo de A* - ajuste por gustos.

    votos: firma -> +1 o -1 de lo ya votado. gustados: características de los looks con corazón.

    El perceptrón deja de aprender en cuanto acierta, así que sus pesos pueden quedar muy chicos. Por eso los
    puntajes se escalan dentro de la lista: lo que cuenta es qué tanto gusta un atuendo frente a los otros, y el
    ajuste queda acotado.

    Lo ya votado no se adivina: el perceptrón predice los atuendos nuevos, pero uno con corazón vale +1 y uno
    que ya se mostró sin corazón vale -1. Hace falta porque dos atuendos pueden tener las mismas características
    (dos pares de zapatos café formales): con uno marcado y otro no, el modelo lineal no puede separarlos. Así lo
    que gustó se queda y lo demás deja lugar a opciones nuevas.
    """
    caracteristicas = [caracteristicas_de([e["prenda"] for e in s["elementos"]]) for s in sugerencias]
    puntajes = escalar([puntuar(pesos, x) for x in caracteristicas])
    if gustados:
        parecidos = escalar([-min(distancia(x, gustado) for gustado in gustados) for x in caracteristicas])
        puntajes = [(puntaje + parecido) / 2 for puntaje, parecido in zip(puntajes, parecidos)]
    for sugerencia, puntaje in zip(sugerencias, puntajes):
        voto = votos.get(firma_de([e["prenda"]["id"] for e in sugerencia["elementos"]]))
        sugerencia["voto"] = voto
        sugerencia["costo_final"] = sugerencia["costo"] - AJUSTE_MAXIMO * (voto or puntaje)
    # En un empate va primero lo que la persona no ha visto.
    return sorted(sugerencias, key=lambda s: (s["costo_final"], s["costo"], s["voto"] == -1))
