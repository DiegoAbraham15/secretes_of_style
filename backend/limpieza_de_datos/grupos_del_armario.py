"""Lo que la pestaña Estadísticas muestra de la segmentación, los atípicos y el PCA, en una sola petición.

  Tus grupos de ropa        los segmentos de K-means (segmentacion_kmeans.py), con sus prendas.
  Mapa de tu armario        cada prenda en PC1 y PC2 (pca_prendas.py), del color de su grupo, y qué significa
                            moverse en cada eje (sale de las cargas de las componentes).
  Prendas que no encajan    las que están más lejos del centro de su grupo: arriba del percentil 95 de las
                            distancias (analisis_de_segmentos.py).
Los grupos se numeran del más grande al más chico; la app pinta cada número siempre con el mismo color.
"""

import numpy as np
from fastapi import APIRouter, Depends

from limpieza_de_datos.pca_prendas import pca
from limpieza_de_datos.segmentacion_kmeans import (MINIMO_PRENDAS, VARIABLES, distancia_al_centro, segmentar, silhouette,
                                                   tabla_de_prendas)
from servidor.consultas import prendas_de
from servidor.seguridad import usuario_actual

CARGA_QUE_CUENTA = 0.4  # una variable describe un eje si su carga pesa al menos esto
HACIA_ARRIBA = {"abrigo": "más abrigadoras", "tono": "más oscuras", "formalidad": "más formales", "neutro": "más neutras"}
HACIA_ABAJO = {"abrigo": "más ligeras", "tono": "más claras", "formalidad": "más casuales", "neutro": "de color más vivo"}


def describir_eje(cargas: dict) -> dict:
    """Qué tienen las prendas de cada extremo del eje, p. ej. {"positivo": "más formales y más neutras", ...}."""
    pesadas = sorted(((v, c) for v, c in cargas.items() if abs(c) >= CARGA_QUE_CUENTA), key=lambda par: -abs(par[1]))
    positivo = [HACIA_ARRIBA[v] if c > 0 else HACIA_ABAJO[v] for v, c in pesadas]
    negativo = [HACIA_ABAJO[v] if c > 0 else HACIA_ARRIBA[v] for v, c in pesadas]
    return {"positivo": " y ".join(positivo), "negativo": " y ".join(negativo)}


rutas = APIRouter()


@rutas.get("/api/prendas/grupos")
def grupos_del_armario(usuario: dict = Depends(usuario_actual)):
    df = tabla_de_prendas(usuario["id"])
    if len(df) < MINIMO_PRENDAS:
        return {"listo": False, "minimo": MINIMO_PRENDAS, "prendas": len(df)}
    completas = {p["id"]: p for p in prendas_de(usuario["id"])}
    segmentos = segmentar(df)
    X, modelo = segmentos["X"], segmentos["modelo"]
    etiquetas = modelo["etiquetas"]

    # Número de grupo por tamaño: el 1 es el más grande.
    por_tamaño = sorted(range(segmentos["k"]), key=lambda j: (-(etiquetas == j).sum(), j))
    numero = {j: i + 1 for i, j in enumerate(por_tamaño)}
    grupos = [{"numero": numero[j], "nombre": segmentos["nombres"][j].removeprefix("Prendas ").capitalize(),
               "prendas": [int(i) for i in df.loc[etiquetas == j, "id"]]} for j in por_tamaño]

    resultado = pca(X)
    coordenadas = X @ resultado["componentes"]
    cargas = [dict(zip(VARIABLES, resultado["componentes"][:, i])) for i in range(2)]

    distancia, umbral = distancia_al_centro(X, modelo)
    lejanas = sorted(np.flatnonzero(distancia > umbral), key=lambda i: -distancia[i])

    return {
        "listo": True,
        "silhouette": silhouette(X, etiquetas),
        "grupos": grupos,
        "mapa": {
            "conservado": round(float(resultado["proporcion"][:2].sum()), 3),  # varianza de PC1 + PC2
            "eje_x": describir_eje(cargas[0]),
            "eje_y": describir_eje(cargas[1]),
            "puntos": [{"id": int(df.loc[i, "id"]), "grupo": numero[etiquetas[i]],
                        "x": round(float(coordenadas[i, 0]), 4), "y": round(float(coordenadas[i, 1]), 4)}
                       for i in range(len(df))],
        },
        "no_encajan": [{"id": int(df.loc[i, "id"]), "grupo": numero[etiquetas[i]]} for i in lejanas],
        "prendas": {str(i): completas[i] for i in completas},
    }
