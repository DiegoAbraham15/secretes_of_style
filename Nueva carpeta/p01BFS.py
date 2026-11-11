
# ============================================================
# PRACTICA 1: BUSQUEDA FRENTE A APRENDIZAJE AUTOMATICO
# PARTE A: ENCONTRAR UNA RUTA MEDIANTE BFS
# ============================================================

#Objetivo de aprendizaje
#Que el estudiante identifique las diferencias entre resolver 
#un problema mediante reglas y algoritmos de búsqueda, 
#y resolverlo mediante un modelo que aprende de datos.

#Planteamiento del problema
#Imagina que una universidad quiere desarrollar un asistente académico.

#El sistema necesita realizar dos tareas:

#Problema A. Encontrar una ruta desde el laboratorio hasta la biblioteca, 
#utilizando un mapa de edificios y conexiones conocidas.

#Problema B. Estimar si un estudiante aprobará una asignatura, 
#utilizando ejemplos históricos de horas de estudio y calificaciones.

#La pregunta central es: ¿podemos resolver ambos problemas con el mismo tipo de algoritmo?

#En esta práctica comprobaremos que, 
#aunque ambos pueden formar parte de un sistema inteligente, 
#requieren enfoques diferentes.

#Al terminar, deberá ser capaz de:
#- Identificar entradas, estados, objetivos y resultados.
#- Distinguir un algoritmo tradicional de un modelo de aprendizaje automático.
#- Implementar dos soluciones sencillas en Python.
#- Explicar en qué situaciones conviene utilizar cada enfoque.

from collections import deque

# ------------------------------------------------------------
# 1. REPRESENTAR EL MAPA COMO UN GRAFO
# ------------------------------------------------------------
# Cada edificio es un nodo.
# Cada conexión representa un camino directo.
#
# Por ejemplo:
# Laboratorio -> Cafeteria significa que existe un camino
# directo entre ambos edificios.

mapa = {
    "Laboratorio": ["Cafeteria", "Aulas"],
    "Cafeteria": ["Biblioteca"],
    "Aulas": ["Auditorio", "Biblioteca"],
    "Auditorio": ["Biblioteca"],
    "Biblioteca": []
}


# ------------------------------------------------------------
# 2. DEFINIR EL ALGORITMO DE BUSQUEDA EN ANCHURA
# ------------------------------------------------------------
def buscar_ruta(grafo, inicio, objetivo):

    # La cola almacena las rutas pendientes de explorar.
    # BFS utiliza una cola FIFO: primero entra, primero sale.
    cola = deque([[inicio]])

    # Registrar los nodos visitados evita repetir exploraciones.
    visitados = {inicio}

    # Continuar mientras existan rutas por explorar.
    while cola:

        # Extraer la ruta más antigua de la cola.
        ruta = cola.popleft()

        # El último nodo de la ruta es nuestra posición actual.
        nodo_actual = ruta[-1]

        # Comprobar si llegamos al destino.
        if nodo_actual == objetivo:
            return ruta

        # Explorar los vecinos del nodo actual.
        for vecino in grafo[nodo_actual]:

            # Solo incorporar nodos que todavía no visitamos.
            if vecino not in visitados:

                visitados.add(vecino)

                # Crear una nueva ruta sin modificar la anterior.
                nueva_ruta = ruta + [vecino]

                # Agregar la nueva ruta a la cola.
                cola.append(nueva_ruta)

    # Si agotamos la cola, no encontramos una ruta.
    return None


# ------------------------------------------------------------
# 3. EJECUTAR EL ALGORITMO
# ------------------------------------------------------------
inicio = "Laboratorio"
objetivo = "Biblioteca"

ruta = buscar_ruta(mapa, inicio, objetivo)

print("=== RESULTADO DE LA BUSQUEDA ===")

if ruta is not None:
    print("Ruta encontrada:")
    print(" -> ".join(ruta))
    print("Numero de conexiones:", len(ruta) - 1)
else:
    print("No existe una ruta hacia el destino.")
