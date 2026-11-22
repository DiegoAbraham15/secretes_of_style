"""Módulo de reducción de dimensionalidad con PCA (Análisis de Componentes Principales).

Cada prenda se describe con las 4 variables de segmentacion_kmeans.py: abrigo, tono, formalidad y neutro. Cuatro
dimensiones no se pueden dibujar; PCA las transforma en componentes principales:
  PC1   la dirección con la mayor variabilidad del armario.
  PC2   la mayor variabilidad restante, sin correlación con PC1. Y así hasta PC4.
Con PC1 y PC2 cada prenda queda como un punto (x, y) que se puede graficar junto con su segmento de K-means.

Pasos (hechos a mano con numpy: el proyecto no usa scikit-learn):
  1. Estandarizar (StandardScaler): sin esto, el abrigo y el tono (1 a 5) dominarían a neutro (0/1).
  2. Matriz de covarianza y sus vectores y valores propios: los vectores son las componentes y cada valor
     propio, la varianza que explica.
  3. Varianza explicada y acumulada; cuántas componentes hacen falta para conservar el 85 %.
  4. Cargas (loadings): cuánto aporta cada variable original a cada componente.
  5. Coordenadas en 2 y 3 dimensiones, con el segmento de K-means de cada prenda.
  6. Error de reconstrucción (MSE): cuánto se pierde al regresar de k componentes a las 4 variables.
  7. Exportar coordenadas y reconstrucción a CSV.
PCA conserva varianza, no separa grupos: si en 2D los segmentos se ven mezclados, la diferencia puede estar en
PC3 o más. Esta ruta NO cambia lo que hace la app.
"""

import numpy as np
from fastapi import APIRouter, Depends

from limpieza_de_datos.evaluacion_del_modelo import CARPETA_CSV
from limpieza_de_datos.segmentacion_kmeans import MINIMO_PRENDAS, VARIABLES, estandarizar, segmentar, tabla_de_prendas
from servidor.seguridad import usuario_actual

VARIANZA_OBJETIVO = 0.85


def pca(X: np.ndarray) -> dict:
    """Componentes (columnas), varianza de cada una y proporción explicada, de mayor a menor."""
    covarianza = np.cov(X, rowvar=False)
    valores, vectores = np.linalg.eigh(covarianza)  # eigh: la covarianza es simétrica
    orden = np.argsort(valores)[::-1]
    valores, vectores = np.clip(valores[orden], 0, None), vectores[:, orden]
    # El signo de un vector propio es arbitrario: se fija para que su carga más grande sea positiva.
    signos = np.sign(vectores[np.abs(vectores).argmax(axis=0), np.arange(vectores.shape[1])])
    vectores = vectores * np.where(signos == 0, 1, signos)
    total = valores.sum() or 1.0
    return {"componentes": vectores, "varianza": valores, "proporcion": valores / total}


def reconstruir(X: np.ndarray, componentes: np.ndarray, k: int) -> np.ndarray:
    """Proyecta en k componentes y regresa al espacio original (estandarizado)."""
    return X @ componentes[:, :k] @ componentes[:, :k].T


rutas = APIRouter()


@rutas.get("/api/prendas/pca")
def analizar_pca(usuario: dict = Depends(usuario_actual)):
    """Varianza explicada, cargas, coordenadas 2D/3D con su segmento y error de reconstrucción."""
    df = tabla_de_prendas(usuario["id"])
    if len(df) < MINIMO_PRENDAS:
        return {"listo": False, "mensaje": f"Hacen falta al menos {MINIMO_PRENDAS} prendas para el análisis."}
    datos = df[VARIABLES].to_numpy(dtype=float)
    X = estandarizar(datos)
    resultado = pca(X)
    componentes, proporcion = resultado["componentes"], resultado["proporcion"]
    acumulada = np.cumsum(proporcion)
    necesarias = int(np.searchsorted(acumulada, VARIANZA_OBJETIVO - 1e-9) + 1)
    segmentos = segmentar(df)  # el modelo final de segmentacion_kmeans.py
    etiquetas = segmentos["modelo"]["etiquetas"]

    coordenadas = X @ componentes
    errores = [{"componentes": k, "mse": round(float(((X - reconstruir(X, componentes, k)) ** 2).mean()), 4)}
               for k in range(1, len(VARIABLES) + 1)]
    # Reconstrucción con 2 componentes, regresada a las unidades originales (deshace la estandarización).
    desviacion = datos.std(axis=0)
    reconstruidos = reconstruir(X, componentes, 2) * np.where(desviacion == 0, 1, desviacion) + datos.mean(axis=0)

    CARPETA_CSV.mkdir(exist_ok=True)
    salida = df.assign(segmento=etiquetas + 1, nombre_segmento=[segmentos["nombres"][j] for j in etiquetas],
                       **{f"PC{i + 1}": coordenadas[:, i].round(4) for i in range(3)},
                       **{f"{v}_reconstruido_2pc": reconstruidos[:, i].round(2) for i, v in enumerate(VARIABLES)})
    salida.to_csv(CARPETA_CSV / f"pca_prendas_usuario_{usuario['id']}.csv", index=False, encoding="utf-8")

    cargas = [{"componente": f"PC{i + 1}", **{v: round(float(componentes[j, i]), 3) for j, v in enumerate(VARIABLES)}}
              for i in range(len(VARIABLES))]
    principal = lambda i: max(VARIABLES, key=lambda v: abs(cargas[i][v]))  # noqa: E731
    return {
        "listo": True,
        "prendas": len(df),
        "variables": VARIABLES,
        "varianza": [{"componente": f"PC{i + 1}", "explicada": round(float(p), 4), "acumulada": round(float(a), 4)}
                     for i, (p, a) in enumerate(zip(proporcion, acumulada))],
        "componentes_para_85": necesarias,
        "cargas": cargas,
        "coordenadas": [{"id": int(f.id), "prenda": f.prenda, "color": f.color, "segmento": int(f.segmento),
                         "nombre_segmento": f.nombre_segmento, "pc1": float(f.PC1), "pc2": float(f.PC2), "pc3": float(f.PC3)}
                        for f in salida.itertuples()],
        "error_de_reconstruccion": errores,
        "conclusion": (f"PC1 y PC2 conservan el {round(float(acumulada[1]) * 100, 1)} % de la variabilidad del armario; "
                       f"para llegar al {round(VARIANZA_OBJETIVO * 100)} % hacen falta {necesarias} componentes. PC1 la "
                       f"marca sobre todo {principal(0)} y PC2, {principal(1)}. Con 2 componentes el error de "
                       f"reconstrucción es {errores[1]['mse']} (en unidades estandarizadas)."),
        "archivo": f"limpieza_de_datos/datos/pca_prendas_usuario_{usuario['id']}.csv",
    }
