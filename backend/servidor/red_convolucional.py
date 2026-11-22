"""Módulo de inferencia CNN 1D: estima si un look va a gustar.

Se entrena aparte y una sola vez, en backend/entrenamiento_cnn/ (pandas + PyTorch, con 50 000 looks simulados). Aquí solo
se usa: los pesos están en modelos_entrenados/cnn_atuendos.npz y la cuenta se hace a mano con numpy, así el
servidor no necesita PyTorch. Si el archivo no existe, probabilidades() devuelve None y la app ordena igual que
antes (perceptrón + parecido).

El look como secuencia (una serie ordenada de prendas):
  posiciones  ORDEN: abrigo, parte de arriba, parte de abajo, calzado y accesorio, de afuera hacia adentro y de
              arriba abajo. La convolución con kernel 2 mira prendas VECINAS (arriba con abajo, abajo con
              zapatos), algo que las 13 características del perceptrón, que promedian todo el look, no ven.
  canales     por prenda: si está, abrigo, tono, si es neutra, si es estampada y su estilo (uno por estilo);
              y el cuestionario de la persona (una columna por respuesta), igual en las 5 posiciones.

La red: Conv1d → BatchNorm → ReLU → Conv1d → BatchNorm → ReLU → promedio →
lineal → sigmoide = probabilidad de corazón.
"""

import warnings
from pathlib import Path

import numpy as np

from servidor.aprendizaje import PESOS_DE_RESPUESTA, RESPUESTA_POR_DEFECTO
from servidor.busqueda import TONO
from servidor.logica import COLORES_NEUTROS, ESTILOS, es_estampada

ARCHIVO_MODELO = Path(__file__).resolve().parent.parent / "modelos_entrenados" / "cnn_atuendos.npz"

ORDEN = ["abrigo", "parte_superior", "parte_inferior", "calzado", "accesorio"]
CANALES_PRENDA = ["presente", "abrigo", "tono", "neutro", "estampado"] + [f"estilo_{e}" for e in ESTILOS]
CANALES_PERFIL = [f"{pregunta}_{respuesta}" for pregunta, opciones in PESOS_DE_RESPUESTA.items() for respuesta in opciones]
CANALES = CANALES_PRENDA + CANALES_PERFIL


# ------------------------------------------------
# 1. DEL LOOK A SU SECUENCIA
# ------------------------------------------------

def secuencia_de(atuendo: list[dict], preferencias: dict | None) -> np.ndarray:
    """La entrada de la red: una matriz [canales, 5 posiciones] con valores de 0 a 1.

    La usan igual el entrenamiento (entrenamiento_cnn/preparacion_tensores.py) y la app, así lo que aprendió la red es lo mismo que recibe.
    A* arma una prenda por categoría; si llegaran dos de la misma, cuenta la primera.
    """
    x = np.zeros((len(CANALES), len(ORDEN)), dtype=np.float32)
    ocupadas = set()
    for prenda in atuendo:
        j = ORDEN.index(prenda["categoria"])
        if j in ocupadas:
            continue
        ocupadas.add(j)
        x[0, j] = 1.0
        x[1, j] = (prenda["nivel_abrigo"] - 1) / 4
        x[2, j] = (TONO[prenda["color_principal"]] - 1) / 4
        x[3, j] = prenda["color_principal"] in COLORES_NEUTROS
        x[4, j] = es_estampada(prenda)
        if prenda.get("estilo") in ESTILOS:
            x[5 + ESTILOS.index(prenda["estilo"]), j] = 1.0
    preferencias = preferencias or {}
    for pregunta, opciones in PESOS_DE_RESPUESTA.items():
        respuesta = preferencias.get(pregunta)
        if respuesta not in opciones:
            respuesta = RESPUESTA_POR_DEFECTO[pregunta]
        x[CANALES.index(f"{pregunta}_{respuesta}"), :] = 1.0
    return x


# ------------------------------------------------
# 2. LA RED, CON NUMPY
# ------------------------------------------------

_cargado = {}


def modelo() -> dict | None:
    """Los pesos entrenados (se leen una vez). None si todavía no se entrena o si son de otra versión de canales."""
    if "pesos" not in _cargado:
        pesos = None
        if ARCHIVO_MODELO.exists():
            with np.load(ARCHIVO_MODELO, allow_pickle=False) as archivo:
                pesos = {nombre: archivo[nombre] for nombre in archivo.files}
            if list(pesos["canales"]) != CANALES:
                warnings.warn("cnn_atuendos.npz se entrenó con otros canales: vuelve a correr preparacion_tensores.py y entrenamiento_cnn.py")
                pesos = None
        _cargado["pesos"] = pesos
    return _cargado["pesos"]


def convolucion(x: np.ndarray, w: np.ndarray, b: np.ndarray, relleno: int) -> np.ndarray:
    """Conv1d de PyTorch: x [n, entrada, largo], w [salida, entrada, kernel]."""
    if relleno:
        x = np.pad(x, ((0, 0), (0, 0), (relleno, relleno)))
    kernel = w.shape[2]
    ventanas = np.stack([x[:, :, i:i + kernel] for i in range(x.shape[2] - kernel + 1)], axis=2)
    return np.einsum("nilk,oik->nol", ventanas, w) + b[None, :, None]


def normalizacion_por_lotes(x: np.ndarray, p: dict, capa: str) -> np.ndarray:
    """BatchNorm1d en modo evaluación: usa la media y la varianza que guardó el entrenamiento."""
    media, varianza = p[f"{capa}.running_mean"], p[f"{capa}.running_var"]
    escala = p[f"{capa}.weight"] / np.sqrt(varianza + p["eps"])
    return (x - media[None, :, None]) * escala[None, :, None] + p[f"{capa}.bias"][None, :, None]


def probabilidad_de_lote(x: np.ndarray, p: dict) -> np.ndarray:
    """x [n, canales, 5] sin normalizar → probabilidad de corazón de cada look."""
    x = (x - p["media"]) / p["desviacion"]  # con la media y desviación del entrenamiento (preparacion_tensores.py)
    x = np.maximum(normalizacion_por_lotes(convolucion(x, p["conv1.weight"], p["conv1.bias"], 1), p, "bn1"), 0)
    x = np.maximum(normalizacion_por_lotes(convolucion(x, p["conv2.weight"], p["conv2.bias"], 0), p, "bn2"), 0)
    x = x.mean(axis=2)  # AdaptiveAvgPool1d(1); el Dropout no hace nada al predecir
    logit = x @ p["clasificador.weight"].T + p["clasificador.bias"]
    return 1 / (1 + np.exp(-logit[:, 0]))


def probabilidades(atuendos: list[list[dict]], preferencias: dict | None) -> list[float] | None:
    """Probabilidad de corazón de cada look, o None si no hay modelo entrenado."""
    p = modelo()
    if p is None or not atuendos:
        return None
    x = np.stack([secuencia_de(atuendo, preferencias) for atuendo in atuendos])
    return [float(v) for v in probabilidad_de_lote(x, p)]
