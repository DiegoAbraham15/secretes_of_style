"""Los modelos que comparan la evaluación, la selección y la optimización de hiperparámetros, en un solo lugar.

Todos reciben dos tablas de votos (DataFrame con las 13 características y me_gusta en 1 o 0): `entrenamiento`,
de donde aprenden, y `evaluar`, los atuendos que califican. Devuelven un puntaje por atuendo: mientras más alto,
más probable que tenga corazón.
"""

import numpy as np
import pandas as pd

from limpieza_de_datos.limpieza_de_datos import CARACTERISTICAS
from servidor.aprendizaje import EPOCAS, TASA, entrenar, escalar, puntuar


def votos_para_entrenar(df: pd.DataFrame) -> list[dict]:
    """El formato que espera entrenar(): me_gusta en +1/-1 y las características en un diccionario."""
    return [{"me_gusta": 1 if fila["me_gusta"] == 1 else -1,
             "caracteristicas": {c: float(fila[c]) for c in CARACTERISTICAS}} for _, fila in df.iterrows()]


def puntajes(pesos: dict, df: pd.DataFrame) -> pd.Series:
    """El puntaje del perceptrón con esos pesos para cada atuendo."""
    return df.apply(lambda fila: puntuar(pesos, {c: float(fila[c]) for c in CARACTERISTICAS}), axis=1)


def matriz(df: pd.DataFrame) -> np.ndarray:
    return df[CARACTERISTICAS].to_numpy(dtype=float)


def distancias(a: np.ndarray, b: np.ndarray, metrica: str = "manhattan") -> np.ndarray:
    """Distancia de cada fila de a contra cada fila de b: manhattan (la de A* y del parecido) o euclidiana."""
    diferencia = a[:, None, :] - b[None, :, :]
    if metrica == "manhattan":
        # Con sum() de Python, como distancia() de aprendizaje.py: desde Python 3.12 sum() compensa el redondeo
        # y numpy no, así que dos distancias iguales podrían desempatar distinto que en la app.
        return np.array([[sum(abs(x - y) for x, y in zip(fila_a, fila_b)) for fila_b in b.tolist()] for fila_a in a.tolist()])
    return np.sqrt((diferencia ** 2).sum(axis=2))


def perceptron(entrenamiento: pd.DataFrame, evaluar: pd.DataFrame, iniciales: dict,
               epocas: int = EPOCAS, tasa: float = TASA) -> pd.Series:
    """El perceptrón de servidor/aprendizaje.py, entrenado desde los pesos del cuestionario."""
    return puntajes(entrenar(votos_para_entrenar(entrenamiento), iniciales, epocas=epocas, tasa=tasa), evaluar)


def cercania(entrenamiento: pd.DataFrame, evaluar: pd.DataFrame) -> pd.Series:
    """Qué tan parecido es cada atuendo al look con corazón más cercano (menos distancia = más alto)."""
    gustados = matriz(entrenamiento[entrenamiento["me_gusta"] == 1])
    return pd.Series(-distancias(matriz(evaluar), gustados).min(axis=1), index=evaluar.index)


def parecido(entrenamiento: pd.DataFrame, evaluar: pd.DataFrame, iniciales: dict, peso: float,
             peso_cnn: float = 0.0) -> pd.Series:
    """Lo que hace la app (reordenar en aprendizaje.py): perceptrón y cercanía, escalados de -1 a +1 y mezclados.

    Con peso_cnn, la CNN (columna "cnn" de tabla_de_votos) se mezcla con el perceptrón antes, como en reordenar.
    """
    perc, cerca = escalar(list(perceptron(entrenamiento, evaluar, iniciales))), escalar(list(cercania(entrenamiento, evaluar)))
    if peso_cnn:
        perc = [(1 - peso_cnn) * a + peso_cnn * b for a, b in zip(perc, escalar(list(evaluar["cnn"])))]
    return pd.Series([(1 - peso) * a + peso * b for a, b in zip(perc, cerca)], index=evaluar.index)


def knn(entrenamiento: pd.DataFrame, evaluar: pd.DataFrame, n_vecinos: int, pesos: str = "uniform",
        metrica: str = "manhattan") -> pd.Series:
    """Fracción de corazones entre los k vecinos más cercanos; con pesos = distance, el más cercano pesa más."""
    d = distancias(matriz(evaluar), matriz(entrenamiento), metrica)
    y = entrenamiento["me_gusta"].to_numpy(dtype=float)
    k = min(n_vecinos, len(entrenamiento))
    cercanos = np.argsort(d, axis=1, kind="stable")[:, :k]
    puntaje = []
    for fila, indices in enumerate(cercanos):
        if pesos == "distance":
            dist = d[fila, indices]
            # Como en scikit-learn: si hay vecinos a distancia 0, solo ellos cuentan.
            w = (dist == 0).astype(float) if (dist == 0).any() else 1 / dist
        else:
            w = np.ones(k)
        puntaje.append(float((w * y[indices]).sum() / w.sum()))
    return pd.Series(puntaje, index=evaluar.index)
