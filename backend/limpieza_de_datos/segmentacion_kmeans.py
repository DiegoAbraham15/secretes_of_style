"""Módulo de segmentación del armario con K-means (aprendizaje no supervisado).

Se agrupan las PRENDAS de la persona para descubrir qué tipos de
ropa tiene (por ejemplo "neutras oscuras y formales" o "de color vivo") sin decirle al algoritmo cuáles son.
No se usa la categoría (parte superior, calzado...): los grupos salen solo de cómo es cada prenda.

Cuatro variables numéricas:
  Variable      De dónde sale                                   Rango
  abrigo        nivel_abrigo                                    1 (ligera) a 5 (muy abrigadora)
  tono          TONO del color en busqueda.py                   1 (muy claro) a 5 (muy oscuro)
  formalidad    estilo: deportivo 1, casual y urbano 2,         1 a 4
                semiformal 3, formal 4
  neutro        color en COLORES_NEUTROS de logica.py           0 o 1
Estampado e impermeable se probaron y se dejaron fuera: casi ninguna prenda los tiene (3 de 35 son
impermeables) y, al escalar, K-means solo separaba esas pocas prendas del resto.

Pasos:
  1. Escalar con StandardScaler (media 0, desviación 1): si no, el abrigo (1 a 5) pesaría más que neutro (0/1).
  2. Método del codo: WCSS (inercia) para K = 1 … 8.
  3. Silhouette Score para K = 2 … 4: qué tan juntos están los de un grupo y qué tan separados de los demás.
  4. Modelo final con el K de mejor silhouette en el que cada grupo tenga al menos el 10 % de las prendas
     (k-means++, 20 inicializaciones, semilla 42).
  5. Interpretar cada grupo por su centroide y ponerle nombre.

K-means, el escalador y silhouette están hechos a mano con numpy (el proyecto no usa scikit-learn);
analisis_de_segmentos.py y pca_prendas.py los reutilizan. Esta ruta NO cambia lo que hace la app: solo informa y exporta un CSV.
"""

from math import ceil, comb

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends

from limpieza_de_datos.evaluacion_del_modelo import CARPETA_CSV
from servidor.consultas import prendas_de
from servidor.busqueda import TONO
from servidor.logica import COLORES_NEUTROS
from servidor.seguridad import usuario_actual

SEMILLA = 42
INICIALIZACIONES = 20  # n_init: se queda la de menor inercia
MAXIMO_ITERACIONES = 300
K_MAXIMO_CODO = 8
# Más grupos dejan grupos de 2 o 3 prendas, que no dicen nada del armario, y en el mapa de la app (pestaña
# Estadísticas) ya no hay colores que se distingan entre sí, también con daltonismo.
K_MAXIMO = 4
MINIMO_POR_GRUPO = 0.10  # de las prendas
MINIMO_PRENDAS = 6
PERCENTIL_ATIPICOS = 95  # atípicos (analisis_de_segmentos.py y la app): arriba de esta distancia, la prenda no encaja en su grupo
FORMALIDAD = {"deportivo": 1, "casual": 2, "urbano": 2, "semiformal": 3, "formal": 4}
VARIABLES = ["abrigo", "tono", "formalidad", "neutro"]
# Cómo se lee un centroide: (si está por arriba del promedio, si está por abajo).
RASGOS = {"abrigo": ("abrigadoras", "ligeras"), "tono": ("oscuras", "claras"),
          "formalidad": ("formales", "deportivas o casuales"), "neutro": ("neutras", "de color vivo")}


# ------------------------------------------------------------
# 1. LAS PRENDAS COMO TABLA DE VARIABLES
# ------------------------------------------------------------

def tabla_de_prendas(usuario_id: int) -> pd.DataFrame:
    filas = [{
        "id": p["id"],
        "prenda": p["subcategoria"] or p["categoria"].replace("_", " ").capitalize(),
        "categoria": p["categoria"],
        "color": p["color_principal"],
        "abrigo": p["nivel_abrigo"],
        "tono": TONO[p["color_principal"]],
        "formalidad": FORMALIDAD[p["estilo"]],
        "neutro": int(p["color_principal"] in COLORES_NEUTROS),
    } for p in prendas_de(usuario_id)]
    return pd.DataFrame(filas, columns=["id", "prenda", "categoria", "color", *VARIABLES])


# ------------------------------------------------------------
# 2. ESCALADORES (StandardScaler y MinMaxScaler)
# ------------------------------------------------------------

def estandarizar(X: np.ndarray) -> np.ndarray:
    """(x - media) / desviación, por columna. Una columna constante queda en 0."""
    desviacion = X.std(axis=0)
    return (X - X.mean(axis=0)) / np.where(desviacion == 0, 1, desviacion)


def min_max(X: np.ndarray) -> np.ndarray:
    """(x - mínimo) / (máximo - mínimo), por columna: todo queda entre 0 y 1."""
    rango = X.max(axis=0) - X.min(axis=0)
    return (X - X.min(axis=0)) / np.where(rango == 0, 1, rango)


# ------------------------------------------------------------
# 3. K-MEANS
# ------------------------------------------------------------

def distancias_cuadradas(X: np.ndarray, centroides: np.ndarray) -> np.ndarray:
    return ((X[:, None, :] - centroides[None, :, :]) ** 2).sum(axis=2)


def centroides_iniciales(X: np.ndarray, k: int, rng: np.random.Generator, inicio: str) -> np.ndarray:
    """random: k registros al azar. k-means++: el primero al azar y cada siguiente con probabilidad
    proporcional a su distancia² al centroide más cercano (así los iniciales quedan separados)."""
    if inicio == "random":
        return X[rng.choice(len(X), size=k, replace=False)].copy()
    centroides = [X[rng.integers(len(X))]]
    for _ in range(1, k):
        d2 = distancias_cuadradas(X, np.array(centroides)).min(axis=1)
        probabilidad = d2 / d2.sum() if d2.sum() > 0 else np.full(len(X), 1 / len(X))
        centroides.append(X[rng.choice(len(X), p=probabilidad)])
    return np.array(centroides, dtype=float)


def kmeans(X: np.ndarray, k: int, semilla: int = SEMILLA, inicio: str = "k-means++",
           inicializaciones: int = INICIALIZACIONES) -> dict:
    """Inicialización → asignación → actualización → convergencia; se repite `inicializaciones` veces."""
    rng = np.random.default_rng(semilla)
    mejor = None
    for _ in range(inicializaciones):
        centroides = centroides_iniciales(X, k, rng, inicio)
        for iteracion in range(1, MAXIMO_ITERACIONES + 1):
            etiquetas = distancias_cuadradas(X, centroides).argmin(axis=1)  # asignación
            nuevos = np.array([X[etiquetas == j].mean(axis=0) if (etiquetas == j).any() else centroides[j]
                               for j in range(k)])  # actualización (un grupo vacío conserva su centroide)
            if np.allclose(nuevos, centroides):  # convergencia
                break
            centroides = nuevos
        d2 = distancias_cuadradas(X, nuevos)
        etiquetas = d2.argmin(axis=1)
        inercia = float(d2[np.arange(len(X)), etiquetas].sum())  # WCSS
        if mejor is None or inercia < mejor["inercia"] - 1e-9:
            mejor = {"etiquetas": etiquetas, "centroides": nuevos, "inercia": inercia, "iteraciones": iteracion}
    return mejor


# ------------------------------------------------------------
# 4. MÉTRICAS: SILHOUETTE Y ADJUSTED RAND INDEX
# ------------------------------------------------------------

def silhouette_por_registro(X: np.ndarray, etiquetas: np.ndarray) -> np.ndarray:
    """s = (b - a) / max(a, b). a: distancia media a los de su grupo; b: a los del grupo vecino más cercano."""
    d = np.sqrt(distancias_cuadradas(X, X))
    grupos = np.unique(etiquetas)
    s = np.zeros(len(X))
    for i in range(len(X)):
        mismo = etiquetas == etiquetas[i]
        if mismo.sum() == 1 or len(grupos) == 1:
            continue  # un grupo de uno vale 0, como en scikit-learn
        a = d[i, mismo].sum() / (mismo.sum() - 1)
        b = min(d[i, etiquetas == g].mean() for g in grupos if g != etiquetas[i])
        s[i] = (b - a) / max(a, b) if max(a, b) > 0 else 0.0
    return s


def silhouette(X: np.ndarray, etiquetas: np.ndarray) -> float:
    return round(float(silhouette_por_registro(X, etiquetas).mean()), 4)


def ari(a, b) -> float:
    """Adjusted Rand Index: 1 = mismas agrupaciones (aunque los números de grupo cambien), 0 = como al azar."""
    tabla = pd.crosstab(pd.Series(a), pd.Series(b)).to_numpy()
    pares = sum(comb(int(x), 2) for x in tabla.flat)
    pares_a = sum(comb(int(x), 2) for x in tabla.sum(axis=1))
    pares_b = sum(comb(int(x), 2) for x in tabla.sum(axis=0))
    esperado = pares_a * pares_b / comb(int(tabla.sum()), 2)
    maximo = (pares_a + pares_b) / 2
    return 1.0 if maximo == esperado else round(float((pares - esperado) / (maximo - esperado)), 4)


# ------------------------------------------------------------
# 5. CODO, SILHOUETTE Y MODELO FINAL
# ------------------------------------------------------------

def metodo_del_codo(X: np.ndarray) -> list[dict]:
    return [{"k": k, "inercia": round(kmeans(X, k)["inercia"], 3)} for k in range(1, min(K_MAXIMO_CODO, len(X) - 1) + 1)]


def silhouette_por_k(X: np.ndarray) -> list[dict]:
    """Silhouette de cada K y el tamaño de su grupo más chico (para descartar grupos de 2 o 3 prendas)."""
    filas = []
    for k in range(2, min(K_MAXIMO, len(X) - 1) + 1):
        etiquetas = kmeans(X, k)["etiquetas"]
        filas.append({"k": k, "silhouette": silhouette(X, etiquetas), "grupo_mas_chico": int(np.bincount(etiquetas).min())})
    return filas


def elegir_k(puntajes: list[dict], prendas: int) -> int:
    """El de mejor silhouette entre los que dejan cada grupo con al menos el 10 % (en empate, el K menor)."""
    minimo = max(2, ceil(MINIMO_POR_GRUPO * prendas))
    validos = [fila for fila in puntajes if fila["grupo_mas_chico"] >= minimo] or puntajes
    return max(validos, key=lambda fila: fila["silhouette"])["k"]


def nombrar(centroide_estandar: np.ndarray) -> str:
    """Los dos rasgos que más se alejan del promedio del armario (al menos media desviación)."""
    rasgos = sorted(zip(VARIABLES, centroide_estandar), key=lambda par: -abs(par[1]))
    palabras = [RASGOS[v][0] if z > 0 else RASGOS[v][1] for v, z in rasgos[:2] if abs(z) >= 0.5]
    return "Prendas " + " y ".join(palabras) if palabras else "Prendas de todo un poco"


def distancia_al_centro(X: np.ndarray, modelo: dict) -> tuple[np.ndarray, float]:
    """Distancia de cada prenda al centro de su grupo y el umbral (percentil 95) arriba del cual es atípica."""
    distancia = np.sqrt(((X - modelo["centroides"][modelo["etiquetas"]]) ** 2).sum(axis=1))
    return distancia, float(np.percentile(distancia, PERCENTIL_ATIPICOS))


def segmentar(df: pd.DataFrame, k: int | None = None) -> dict:
    """El modelo final y la descripción de cada grupo. Lo usan también analisis_de_segmentos.py y pca_prendas.py."""
    X = estandarizar(df[VARIABLES].to_numpy(dtype=float))
    k = k or elegir_k(silhouette_por_k(X), len(X))
    modelo = kmeans(X, k)
    nombres = {}
    for j in range(k):
        nombre = nombrar(modelo["centroides"][j])
        nombres[j] = nombre if nombre not in nombres.values() else f"{nombre} ({j + 1})"
    return {"X": X, "k": k, "modelo": modelo, "nombres": nombres}


def perfiles(df: pd.DataFrame, segmentos: dict) -> list[dict]:
    etiquetas = segmentos["modelo"]["etiquetas"]
    resultado = []
    for j, nombre in segmentos["nombres"].items():
        miembros = df[etiquetas == j]
        resultado.append({
            "segmento": j + 1,
            "nombre": nombre,
            "prendas": len(miembros),
            "centroide": {v: round(float(miembros[v].mean()), 2) for v in VARIABLES},  # en unidades originales
            "integrantes": [{"id": int(f.id), "prenda": f.prenda, "color": f.color} for f in miembros.itertuples()],
        })
    return sorted(resultado, key=lambda p: -p["prendas"])


# ------------------------------------------------------------
# RUTA
# ------------------------------------------------------------

rutas = APIRouter()


@rutas.get("/api/prendas/segmentos")
def segmentar_armario(usuario: dict = Depends(usuario_actual)):
    """Agrupa las prendas con K-means: codo, silhouette, K elegido y perfil de cada grupo."""
    df = tabla_de_prendas(usuario["id"])
    if len(df) < MINIMO_PRENDAS:
        return {"listo": False, "mensaje": f"Hacen falta al menos {MINIMO_PRENDAS} prendas para formar grupos."}
    X = estandarizar(df[VARIABLES].to_numpy(dtype=float))
    codo, puntajes = metodo_del_codo(X), silhouette_por_k(X)
    segmentos = segmentar(df, elegir_k(puntajes, len(df)))

    salida = df.assign(segmento=segmentos["modelo"]["etiquetas"] + 1,
                       nombre_segmento=[segmentos["nombres"][j] for j in segmentos["modelo"]["etiquetas"]])
    CARPETA_CSV.mkdir(exist_ok=True)
    salida.to_csv(CARPETA_CSV / f"segmentos_prendas_usuario_{usuario['id']}.csv", index=False, encoding="utf-8")

    grupos = perfiles(df, segmentos)
    return {
        "listo": True,
        "prendas": len(df),
        "variables": VARIABLES,
        "metodo_del_codo": codo,
        "silhouette_por_k": puntajes,
        "k_elegido": segmentos["k"],
        "silhouette": silhouette(X, segmentos["modelo"]["etiquetas"]),
        "inercia": round(segmentos["modelo"]["inercia"], 3),
        "segmentos": grupos,
        "conclusion": (f"Tu armario se divide mejor en {segmentos['k']} grupos (silhouette "
                       f"{silhouette(X, segmentos['modelo']['etiquetas'])}): "
                       + "; ".join(f"{g['nombre'].lower()} ({g['prendas']})" for g in grupos) + "."),
        "archivo": f"limpieza_de_datos/datos/segmentos_prendas_usuario_{usuario['id']}.csv",
    }
