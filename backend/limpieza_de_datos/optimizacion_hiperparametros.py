"""Módulo de optimización de hiperparámetros con los votos de la persona (corazón sí / no).

Parámetros son lo que el modelo aprende (los pesos del perceptrón); hiperparámetros son lo que se fija antes
de entrenar para controlar cómo aprende. Aquí se buscan los mejores para los tres modelos de seleccion_del_modelo.py,
con las técnicas de scikit-learn, pero hechas a mano (el proyecto no usa scikit-learn):

  Modelo       Hiperparámetros que se prueban
  KNN          n_vecinos (k), pesos (uniform: todos igual; distance: el más cercano pesa más) y
               metrica (euclidean: línea recta; manhattan: suma de diferencias, la de la búsqueda A*)
  Perceptrón   epocas (vueltas a los votos) y tasa (η: cuánto se mueven los pesos al corregir)
  Parecido     peso del parecido (lo que usa la app: 90 % parecido + 10 % perceptrón)

  Técnica              Qué hace aquí
  StratifiedKFold      5 pliegues que conservan la proporción de corazones, con barajado (semilla 42)
  Validación cruzada   cada configuración aprende con 4 pliegues y se califica con el quinto, 5 veces; se
                       reporta el promedio y la desviación
  GridSearchCV         prueba TODAS las combinaciones de una lista corta (20 + 20 + 6 = 46)
  RandomizedSearchCV   prueba 10 combinaciones al azar por modelo de un espacio mucho más grande

La métrica es el "orden" (la de evaluacion_del_modelo.py): probabilidad de que un look con corazón quede
arriba de uno sin corazón. Como en seleccion_del_modelo.py, la prueba (20 %) se aparta antes de buscar y solo se usa una
vez, al final, con la mejor configuración. Esta ruta NO cambia lo que hace la app: solo informa.
"""

import itertools

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends

from limpieza_de_datos.evaluacion_del_modelo import CARPETA_CSV, SEMILLA, arriba, iniciales_de, metricas, orden, tabla_de_votos
from limpieza_de_datos.modelos import knn, parecido, perceptron
from limpieza_de_datos.seleccion_del_modelo import PROPORCION_PRUEBA, apartar
from servidor.aprendizaje import EPOCAS, PESO_PARECIDO, TASA
from servidor.seguridad import usuario_actual

PLIEGUES = 5
ITERACIONES_AL_AZAR = 10  # n_iter de RandomizedSearchCV, por modelo

# GridSearchCV: la lista corta con todas sus combinaciones (param_grid).
REJILLA = {
    "knn": {"n_vecinos": [1, 3, 5, 7, 9], "pesos": ["uniform", "distance"], "metrica": ["euclidean", "manhattan"]},
    "perceptron": {"epocas": [1, 5, 10, 20, 50], "tasa": [0.05, 0.1, 0.25, 0.5]},
    "parecido": {"peso": [0.0, 0.25, 0.5, 0.75, 0.9, 1.0]},
}
CONFIGURACION_DE_LA_APP = ("parecido", {"peso": PESO_PARECIDO})  # con el perceptrón de EPOCAS y TASA


# ------------------------------------------------------------
# 1. STRATIFIEDKFOLD: pliegues que conservan la proporción de corazones
# ------------------------------------------------------------

def pliegues_estratificados(df: pd.DataFrame, k: int, semilla: int = SEMILLA) -> list[tuple[pd.Index, pd.Index]]:
    """(entrenamiento, validación) para cada uno de los k pliegues. Cada clase se baraja y se reparte en turno."""
    rng = np.random.default_rng(semilla)
    pliegue_de = pd.Series(0, index=df.index)
    for _, grupo in df.groupby("me_gusta"):
        barajado = rng.permutation(grupo.index.to_numpy())
        pliegue_de[barajado] = np.arange(len(barajado)) % k
    return [(df.index[pliegue_de != i], df.index[pliegue_de == i]) for i in range(k)]


# ------------------------------------------------------------
# 2. LOS MODELOS, CON SUS HIPERPARÁMETROS (están en modelos.py)
# ------------------------------------------------------------

def calificar(familia: str, hiper: dict, entrenamiento: pd.DataFrame, evaluar: pd.DataFrame, iniciales: dict) -> pd.Series:
    if familia == "knn":
        return knn(entrenamiento, evaluar, **hiper)
    if familia == "perceptron":
        return perceptron(entrenamiento, evaluar, iniciales, **hiper)
    return parecido(entrenamiento, evaluar, iniciales, **hiper)


# ------------------------------------------------------------
# 3. VALIDACIÓN CRUZADA
# ------------------------------------------------------------

def validacion_cruzada(familia: str, hiper: dict, df: pd.DataFrame, pliegues: list, iniciales: dict) -> tuple[float, float]:
    """Promedio y desviación del orden en los k pliegues (cada uno se califica con lo que aprendió de los otros)."""
    calificaciones = [orden(df.loc[validar, "me_gusta"],
                            calificar(familia, hiper, df.loc[entrenar_con], df.loc[validar], iniciales))
                      for entrenar_con, validar in pliegues]
    return round(float(np.mean(calificaciones)), 3), round(float(np.std(calificaciones)), 3)


# ------------------------------------------------------------
# 4. GRIDSEARCHCV Y RANDOMIZEDSEARCHCV
# ------------------------------------------------------------

def busqueda_en_rejilla() -> list[tuple[str, dict]]:
    """Todas las combinaciones de REJILLA, como param_grid."""
    return [(familia, dict(zip(valores, combinacion)))
            for familia, valores in REJILLA.items()
            for combinacion in itertools.product(*valores.values())]


def busqueda_al_azar(maximo_vecinos: int, semilla: int = SEMILLA) -> list[tuple[str, dict]]:
    """ITERACIONES_AL_AZAR configuraciones por modelo, sacadas de espacios más grandes (param_distributions)."""
    rng = np.random.default_rng(semilla)
    configuraciones = []
    for _ in range(ITERACIONES_AL_AZAR):
        configuraciones.append(("knn", {"n_vecinos": int(rng.integers(1, maximo_vecinos + 1)),
                                        "pesos": str(rng.choice(["uniform", "distance"])),
                                        "metrica": str(rng.choice(["euclidean", "manhattan"]))}))
        configuraciones.append(("perceptron", {"epocas": int(rng.integers(1, 101)),
                                               "tasa": round(float(10 ** rng.uniform(-2, 0)), 3)}))  # de 0.01 a 1
        configuraciones.append(("parecido", {"peso": round(float(rng.uniform(0, 1)), 2)}))
    return configuraciones


def evaluar_todas(busqueda: str, configuraciones: list, df: pd.DataFrame, pliegues: list, iniciales: dict) -> list[dict]:
    filas = []
    for familia, hiper in configuraciones:
        media, desviacion = validacion_cruzada(familia, hiper, df, pliegues, iniciales)
        filas.append({"busqueda": busqueda, "modelo": familia, "hiperparametros": hiper,
                      "orden_promedio": media, "desviacion": desviacion})
    return filas


def describir(familia: str, hiper: dict) -> str:
    if familia == "knn":
        return f"KNN (k = {hiper['n_vecinos']}, {hiper['pesos']}, {hiper['metrica']})"
    if familia == "perceptron":
        return f"Perceptrón ({hiper['epocas']} épocas, η = {hiper['tasa']})"
    return f"Parecido {round(hiper['peso'] * 100)} %"


# ------------------------------------------------------------
# 5. PRUEBA FINAL Y CONCLUSIÓN
# ------------------------------------------------------------

def probar(familia: str, hiper: dict, resto: pd.DataFrame, prueba: pd.DataFrame, iniciales: dict) -> dict:
    """Aprende con todo el 80 % y se mide una sola vez con la prueba."""
    puntaje = calificar(familia, hiper, resto, prueba, iniciales)
    cuantos = max(1, round(len(prueba) * resto["me_gusta"].mean()))
    return {"modelo": describir(familia, hiper), **metricas(prueba["me_gusta"], arriba(puntaje, cuantos), puntaje)}


def mejores_por_modelo(tabla: pd.DataFrame) -> list[dict]:
    """Para cada modelo y cada búsqueda, la configuración con mayor orden (en empate, menor desviación)."""
    ordenada = tabla.sort_values(["orden_promedio", "desviacion"], ascending=[False, True], kind="stable")
    return ordenada.groupby(["modelo", "busqueda"], sort=False).head(1).to_dict(orient="records")


def conclusion(mejor: dict, final: dict, app: dict, app_cv: float, corazones_prueba: int) -> str:
    frase = (f"En validación cruzada ganó {mejor['descripcion']} (orden {mejor['orden_promedio']} ± "
             f"{mejor['desviacion']}); la configuración de la app saca {app_cv}. En la prueba final: "
             f"{final['orden']} contra {app['orden']} de la app.")
    if mejor["orden_promedio"] - app_cv < 0.03:
        frase += " La diferencia es pequeña: no conviene cambiar la configuración de la app."
    elif final["orden"] <= app["orden"]:
        frase += " La prueba final no confirma la mejora: por ahora no conviene cambiar la configuración de la app."
    else:
        frase += " La mejora se sostiene en la prueba final: se podría probar esta configuración en la app."
    if corazones_prueba < 3:
        frase += (f" Ojo: la prueba solo tiene {corazones_prueba} look(s) con corazón; con más votos el resultado "
                  "será más confiable.")
    return frase


# ------------------------------------------------------------
# RUTA
# ------------------------------------------------------------

rutas = APIRouter()


@rutas.get("/api/votos/optimizacion")
def optimizar_hiperparametros(usuario: dict = Depends(usuario_actual)):
    """GridSearch y RandomizedSearch con validación cruzada estratificada; la mejor se mide una vez en prueba."""
    df = tabla_de_votos(usuario["id"]).reset_index(drop=True)
    corazones = int(df["me_gusta"].sum())
    if corazones < 3 or len(df) - corazones < 3:
        return {"listo": False, "mensaje": "Hacen falta al menos 3 looks con corazón y 3 sin corazón para la "
                                           "validación cruzada y la prueba."}
    iniciales = iniciales_de(usuario["id"])

    resto, prueba = apartar(df, PROPORCION_PRUEBA, SEMILLA)  # la prueba no se toca hasta el final
    k = max(2, min(PLIEGUES, int(resto["me_gusta"].sum()), int((resto["me_gusta"] == 0).sum())))
    pliegues = pliegues_estratificados(resto, k)

    filas = evaluar_todas("GridSearchCV", busqueda_en_rejilla(), resto, pliegues, iniciales)
    filas += evaluar_todas("RandomizedSearchCV", busqueda_al_azar(min(20, len(pliegues[0][0]))), resto, pliegues, iniciales)
    tabla = pd.DataFrame(filas)
    tabla["descripcion"] = [describir(f, h) for f, h in zip(tabla["modelo"], tabla["hiperparametros"])]

    mejor = tabla.sort_values(["orden_promedio", "desviacion"], ascending=[False, True], kind="stable").iloc[0].to_dict()
    app_cv, _ = validacion_cruzada(*CONFIGURACION_DE_LA_APP, resto, pliegues, iniciales)
    final = probar(mejor["modelo"], mejor["hiperparametros"], resto, prueba, iniciales)
    app = probar(*CONFIGURACION_DE_LA_APP, resto, prueba, iniciales)

    CARPETA_CSV.mkdir(exist_ok=True)
    tabla.assign(hiperparametros=tabla["hiperparametros"].astype(str)).to_csv(
        CARPETA_CSV / f"optimizacion_usuario_{usuario['id']}.csv", index=False, encoding="utf-8")

    return {
        "listo": True,
        "datos": {"votos_validos": len(df), "con_corazon": corazones, "para_buscar": len(resto), "prueba": len(prueba),
                  "pliegues": k, "corazones_por_pliegue": [int(resto.loc[v, "me_gusta"].sum()) for _, v in pliegues]},
        "configuraciones_probadas": {"GridSearchCV": int((tabla["busqueda"] == "GridSearchCV").sum()),
                                     "RandomizedSearchCV": int((tabla["busqueda"] == "RandomizedSearchCV").sum())},
        "mejores_por_modelo": [{"busqueda": m["busqueda"], "modelo": m["descripcion"], "orden_promedio": m["orden_promedio"],
                                "desviacion": m["desviacion"]} for m in mejores_por_modelo(tabla)],
        "mejor": {"modelo": mejor["descripcion"], "busqueda": mejor["busqueda"], "hiperparametros": mejor["hiperparametros"],
                  "orden_promedio": mejor["orden_promedio"], "desviacion": mejor["desviacion"]},
        "configuracion_de_la_app": {"modelo": describir(*CONFIGURACION_DE_LA_APP) + f" (perceptrón de {EPOCAS} épocas, η = {TASA})",
                                    "orden_promedio": app_cv},
        "prueba_final": {"mejor": final, "app": app},
        "conclusion": conclusion(mejor, final, app, app_cv, int(prueba["me_gusta"].sum())),
        "archivo": f"limpieza_de_datos/datos/optimizacion_usuario_{usuario['id']}.csv",
    }
