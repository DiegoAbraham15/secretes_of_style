"""Los otros algoritmos de búsqueda de la práctica, sobre el mismo problema de busqueda.py.

Solo viven en el servidor: la app no los muestra. La recomendación usa A* (busqueda.mejores_atuendos)
porque da los atuendos más baratos expandiendo pocos estados; los demás se usan solo si se pide otro
algoritmo en /api/recomendaciones.

  BFS                  cola (FIFO): atuendos nivel por nivel; no mira los costos.
  DFS                  pila (LIFO): baja por la primera opción de cada categoría; no mira los costos.
  UCS                  cola de prioridad por g: los atuendos más baratos, igual que A*.
  Greedy               cola de prioridad por la h del clima: rápido, pero no garantiza el más barato.
  A*                   cola de prioridad por f = g + h (está en busqueda.py).
  Heurística simple    la prenda con menor h del clima en cada paso, sin poder regresar (p30heuristica2).
  Heurística mejorada  la heurística simple con las cuatro mejoras de la práctica: orden de exploración,
                       estados repetidos, todos los atuendos y límite de profundidad.

h del clima: categorías que faltan + distancia de la última prenda al punto ideal. Ignora el color,
así que no es admisible: Greedy y las heurísticas pueden elegir un atuendo más caro.

Todos comparten con A* la poda por color, el control de estados repetidos y el formato de los
nodos {atuendo, g}, así que cualquiera puede ir en busqueda.recomendar.
"""

import heapq
from collections import deque
from itertools import count

from servidor.busqueda import combinan_todas, costo_prenda, distancia_al_ideal, estado, faltan, h, mejores_atuendos


# ------------------------------------------------
# 1. FUNCIONES COMUNES
# ------------------------------------------------

def nodo_inicial(problema: dict) -> dict:
    return {"atuendo": [problema["base"]], "g": 0}


def hijos(nodo: dict, problema: dict) -> list[dict]:
    """Agregar una prenda de una categoría que falta. Poda: la prenda debe combinar con todo el atuendo."""
    atuendo = nodo["atuendo"]
    ocupadas = {p["categoria"] for p in atuendo}
    return [
        {"atuendo": atuendo + [prenda], "g": nodo["g"] + costo_prenda(atuendo, prenda, problema)}
        for prenda in problema["candidatas"]
        if prenda["categoria"] not in ocupadas and combinan_todas(atuendo, prenda)
    ]


def h_clima(atuendo: list[dict], problema: dict) -> int:
    return faltan(atuendo, problema) + distancia_al_ideal(atuendo[-1], problema["ideal"])


# ------------------------------------------------
# 2. BFS y DFS: no miran los costos
# ------------------------------------------------

def bfs(problema: dict, cantidad: int = 1) -> list[dict]:
    """Cola: saca el atuendo más antiguo. Devuelve los primeros `cantidad` atuendos completos."""
    inicio = nodo_inicial(problema)
    frontera = deque([inicio])
    descubiertos = {estado(inicio["atuendo"])}
    encontrados = []

    while frontera and len(encontrados) < cantidad:
        nodo = frontera.popleft()
        if faltan(nodo["atuendo"], problema) == 0:
            encontrados.append(nodo)
            continue
        for hijo in hijos(nodo, problema):
            nuevo = estado(hijo["atuendo"])
            if nuevo not in descubiertos:
                descubiertos.add(nuevo)
                frontera.append(hijo)
    return encontrados


def dfs(problema: dict, cantidad: int = 1) -> list[dict]:
    """Pila: saca el atuendo más reciente y baja por la primera opción de cada categoría."""
    inicio = nodo_inicial(problema)
    pila = [inicio]
    descubiertos = {estado(inicio["atuendo"])}
    encontrados = []

    while pila and len(encontrados) < cantidad:
        nodo = pila.pop()
        if faltan(nodo["atuendo"], problema) == 0:
            encontrados.append(nodo)
            continue
        # Se meten al revés para que la primera opción sea la primera en salir de la pila.
        for hijo in reversed(hijos(nodo, problema)):
            nuevo = estado(hijo["atuendo"])
            if nuevo not in descubiertos:
                descubiertos.add(nuevo)
                pila.append(hijo)
    return encontrados


# ------------------------------------------------
# 3. UCS y GREEDY: colas de prioridad
# ------------------------------------------------
#   UCS     menor g(n)          Greedy  menor h(n) del clima          A*  menor f(n) = g(n) + h(n)

def con_prioridad(problema: dict, cantidad: int, prioridad, reabre: bool) -> list[dict]:
    """Saca de la frontera el nodo con menor `prioridad`. Si `reabre`, un camino más barato a un
    atuendo ya descubierto lo reemplaza (UCS); Greedy se queda con el primero que encontró."""
    desempate = count()  # evita comparar nodos cuando la prioridad empata
    inicio = nodo_inicial(problema)
    frontera = [(prioridad(inicio), next(desempate), inicio)]
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

        for hijo in hijos(nodo, problema):
            nuevo = estado(hijo["atuendo"])
            if nuevo in cerrados or (nuevo in mejor_g and (not reabre or hijo["g"] >= mejor_g[nuevo])):
                continue
            mejor_g[nuevo] = hijo["g"]
            heapq.heappush(frontera, (prioridad(hijo), next(desempate), hijo))
    return encontrados


def ucs(problema: dict, cantidad: int = 1) -> list[dict]:
    return con_prioridad(problema, cantidad, lambda n: n["g"], reabre=True)


def greedy(problema: dict, cantidad: int = 1) -> list[dict]:
    return con_prioridad(problema, cantidad, lambda n: h_clima(n["atuendo"], problema), reabre=False)


# ------------------------------------------------
# 4. HEURÍSTICAS
# ------------------------------------------------

def heuristica_simple(problema: dict, cantidad: int = 1) -> list[dict]:
    """Avanza siempre a la prenda con menor h del clima y nunca regresa: encuentra uno o ninguno."""
    nodo = nodo_inicial(problema)
    while faltan(nodo["atuendo"], problema) > 0:
        opciones = hijos(nodo, problema)
        if not opciones:
            return []  # nada combina y no puede regresar
        nodo = min(opciones, key=lambda hijo: h_clima(hijo["atuendo"], problema))
    return [nodo]


def heuristica_mejorada(problema: dict, cantidad: int | None = None, limite: int | None = None) -> list[dict]:
    """La heurística simple con las cuatro mejoras de las prácticas:

      1. Orden de exploración: primero se prueba la prenda con menor h del clima y los atuendos
         se devuelven en el orden en que se encontraron.
      2. Estados repetidos: el mismo atuendo armado en otro orden no se vuelve a explorar.
      3. Todos los atuendos: al completar uno regresa y sigue probando (hasta `cantidad`, o todos).
      4. Límite de profundidad: máximo de prendas que se agregan a la base.
    """
    visitados, encontrados = set(), []

    def explorar(nodo):
        visitados.add(estado(nodo["atuendo"]))
        if faltan(nodo["atuendo"], problema) == 0:
            encontrados.append(nodo)
            return
        if limite is not None and len(nodo["atuendo"]) - 1 >= limite:
            return  # la rama se corta
        for hijo in sorted(hijos(nodo, problema), key=lambda x: h_clima(x["atuendo"], problema)):
            if cantidad is not None and len(encontrados) >= cantidad:
                return
            if estado(hijo["atuendo"]) not in visitados:  # una rama anterior ya llegó a este atuendo
                explorar(hijo)

    explorar(nodo_inicial(problema))
    return encontrados


def costo_estimado(problema: dict) -> int:
    """La h de A* en la prenda base: ningún atuendo puede costar menos (la heurística es admisible)."""
    return h([problema["base"]], problema)


# Todos reciben (problema, cantidad) y devuelven nodos {atuendo, g}: se pueden usar en busqueda.recomendar.
ALGORITMOS = {
    "astar": mejores_atuendos,
    "bfs": bfs,
    "dfs": dfs,
    "ucs": ucs,
    "greedy": greedy,
    "heuristica_simple": heuristica_simple,
    "heuristica_mejorada": heuristica_mejorada,
}
