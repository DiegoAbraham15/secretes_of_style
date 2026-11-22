"""ETAPA 1 · Generación de datos sintéticos: 10 000 personas × 5 looks calificados.

La app tiene 64 votos reales: muy pocos para entrenar una red. Aquí se simulan 10 000 personas que califican
5 looks cada una (50 000 registros) usando lo mismo que sabe la app:

  - Cada persona contesta el cuestionario al azar (paleta, ropa, estampados) y además tiene un GUSTO OCULTO:
    pesos propios que nadie le pregunta. Así la etiqueta no es una regla fija de la entrada: la red tiene que
    generalizar a personas nuevas, no memorizar una fórmula.
  - Cada look trae parte de arriba, parte de abajo y calzado; a veces abrigo y accesorio. Las prendas usan los
    catálogos reales (14 colores, abrigo 1–5, 5 estilos, estampados).
  - Utilidad = cuestionario·x (pesos_iniciales, el arranque en frío de la app) + gusto oculto·x
               + reglas entre prendas VECINAS (mismo estilo arriba-abajo-zapatos, colores que combinan,
                 choque formal/deportivo, dos estampados juntos) + ruido.
    x son las 13 características de caracteristicas_de(). Corazón ~ Bernoulli(sigmoide(utilidad)), con un
    sesgo que deja ~15 % de corazones (en los votos reales hay 6 de 64).

Salida: datos/atuendos_50000.csv (una fila por look; columnas por posición del cuerpo).
"""

import numpy as np
import pandas as pd

from comun import ARCHIVO_CSV, LOOKS_POR_PERSONA, PERSONAS, SEMILLA, TOTAL_REGISTROS, titulo
from servidor.aprendizaje import PESOS_DE_RESPUESTA, caracteristicas_de, pesos_iniciales
from servidor.logica import COLORES, COLORES_NEUTROS, ESTAMPADOS, ESTILOS, ESTILOS_ARREGLADOS, hechos_de_colores
from servidor.red_convolucional import ORDEN

TASA_CORAZONES = 0.15
COLORES_ORDENADOS = sorted(COLORES)
NEUTROS = sorted(COLORES_NEUTROS)
VIVOS = sorted(COLORES - COLORES_NEUTROS)
ABRIGO_POR_CATEGORIA = {  # (mínimo, máximo) de nivel_abrigo
    "abrigo": (3, 5), "parte_superior": (1, 4), "parte_inferior": (1, 3), "calzado": (1, 3), "accesorio": (1, 2),
}
PROBABILIDAD_OPCIONAL = {"abrigo": 0.4, "accesorio": 0.5}
VECINOS = [("parte_superior", "parte_inferior"), ("parte_inferior", "calzado"), ("abrigo", "parte_superior")]

rng = np.random.default_rng(SEMILLA)


def prenda_al_azar(categoria: str) -> dict:
    color = rng.choice(NEUTROS) if rng.random() < 0.6 else rng.choice(VIVOS)  # en un armario abundan los neutros
    minimo, maximo = ABRIGO_POR_CATEGORIA[categoria]
    return {
        "categoria": categoria,
        "color_principal": str(color),
        "nivel_abrigo": int(rng.integers(minimo, maximo + 1)),
        "estampado": "liso" if rng.random() < 0.75 else str(rng.choice(ESTAMPADOS[1:])),
        "estilo": str(rng.choice(ESTILOS)),
    }


def look_al_azar() -> list[dict]:
    return [prenda_al_azar(c) for c in ORDEN if rng.random() < PROBABILIDAD_OPCIONAL.get(c, 1.0)]


def reglas_entre_vecinos(look: list[dict]) -> float:
    """Lo que solo se ve mirando prendas contiguas: es lo que una convolución puede aprender y un promedio no."""
    por_categoria = {p["categoria"]: p for p in look}
    puntos = 0.0
    for a, b in VECINOS:
        if a not in por_categoria or b not in por_categoria:
            continue
        pa, pb = por_categoria[a], por_categoria[b]
        if pa["estilo"] == pb["estilo"]:
            puntos += 0.8
        estilos = {pa["estilo"], pb["estilo"]}
        if "deportivo" in estilos and estilos & ESTILOS_ARREGLADOS:
            puntos -= 1.2
        if pa["estampado"] != "liso" and pb["estampado"] != "liso":
            puntos -= 1.0
        hechos = hechos_de_colores(pa["color_principal"], pb["color_principal"])
        if "complementarios" in hechos or "mismo_color" in hechos:
            puntos += 0.6
        elif "neutro" not in hechos:
            puntos -= 0.6  # dos colores vivos que no combinan
    return puntos


def utilidad(look: list[dict], cuestionario: dict, gusto_oculto: dict) -> float:
    x = caracteristicas_de(look)
    iniciales = pesos_iniciales(cuestionario)
    lineal = sum((iniciales.get(nombre, 0.0) + gusto_oculto[nombre]) * valor for nombre, valor in x.items())
    return lineal + reglas_entre_vecinos(look) + rng.normal(0, 0.5)


def sesgo_para(utilidades: np.ndarray, tasa: float) -> float:
    """El sesgo b tal que el promedio de sigmoide(u + b) sea la tasa de corazones buscada (bisección)."""
    bajo, alto = -20.0, 20.0
    for _ in range(60):
        medio = (bajo + alto) / 2
        if np.mean(1 / (1 + np.exp(-(utilidades + medio)))) < tasa:
            bajo = medio
        else:
            alto = medio
    return (bajo + alto) / 2


def fila_de(id_registro: int, id_persona: str, cuestionario: dict, look: list[dict]) -> dict:
    fila = {"id_registro": id_registro, "id_persona": id_persona, **cuestionario}
    por_categoria = {p["categoria"]: p for p in look}
    for posicion in ORDEN:
        prenda = por_categoria.get(posicion, {})
        fila[f"{posicion}_color"] = prenda.get("color_principal")
        fila[f"{posicion}_abrigo"] = prenda.get("nivel_abrigo")
        fila[f"{posicion}_estampado"] = prenda.get("estampado")
        fila[f"{posicion}_estilo"] = prenda.get("estilo")
    return fila


def main():
    titulo("SECRETS OF STYLE · ETAPA 1 · GENERACIÓN DE LOOKS SINTÉTICOS")
    print(f"Personas: {PERSONAS:,} · looks por persona: {LOOKS_POR_PERSONA} · registros: {TOTAL_REGISTROS:,}")
    nombres = list(caracteristicas_de(look_al_azar()))
    filas, utilidades = [], []
    for numero in range(1, PERSONAS + 1):
        id_persona = f"PERSONA-{numero:05d}"
        cuestionario = {pregunta: str(rng.choice(list(opciones))) for pregunta, opciones in PESOS_DE_RESPUESTA.items()}
        gusto_oculto = {nombre: float(rng.normal(0, 0.8)) for nombre in nombres}
        for _ in range(LOOKS_POR_PERSONA):
            look = look_al_azar()
            utilidades.append(utilidad(look, cuestionario, gusto_oculto))
            filas.append(fila_de(len(filas) + 1, id_persona, cuestionario, look))
        if numero % 2000 == 0:
            print(f"Personas simuladas: {numero:,}")

    utilidades = np.array(utilidades)
    sesgo = sesgo_para(utilidades, TASA_CORAZONES)
    probabilidad = 1 / (1 + np.exp(-(utilidades + sesgo)))
    datos = pd.DataFrame(filas)
    datos["me_gusta"] = (rng.random(len(datos)) < probabilidad).astype(int)

    assert len(datos) == TOTAL_REGISTROS, "La cantidad de registros no coincide"
    assert datos["id_registro"].is_unique, "Hay identificadores repetidos"
    datos.to_csv(ARCHIVO_CSV, index=False, encoding="utf-8")

    print(f"\nSesgo calibrado: {sesgo:.3f}")
    print(f"Corazones: {datos['me_gusta'].sum():,} ({datos['me_gusta'].mean():.1%})")
    print(f"Mejor resultado posible (si se supiera la probabilidad real): {np.mean(np.maximum(probabilidad, 1 - probabilidad)):.1%} de aciertos")
    print(f"Archivo: {ARCHIVO_CSV} ({ARCHIVO_CSV.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
