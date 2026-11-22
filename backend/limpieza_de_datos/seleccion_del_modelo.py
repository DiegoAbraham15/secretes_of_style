"""entrenamiento, validación y prueba
  Los votos limpios se dividen en tres partes, conservando la proporción de corazones (como stratify=y):
    60 % entrenamiento  aprender los gustos.
    20 % validación     comparar modelos y elegir sus parámetros (k, épocas, peso del parecido).
    20 % prueba         medir UNA vez, al final, el modelo elegido con votos que nunca se usaron para decidir.
  Antes, PESO_PARECIDO se eligió mirando la misma evaluación que daba el resultado; así el número sale más alto
  de lo que es. Aquí la prueba se aparta primero y no se toca hasta el final.
  Cada modelo se mide en entrenamiento y en validación para ver si hay
  sobreajuste (le va muy bien con lo que ya vio y mal con lo nuevo) o subajuste (le va mal hasta con lo que vio).

(comparar algoritmos)
  Se comparan tres familias, cada una con varios parámetros:
    Perceptrón   el de servidor/aprendizaje.py, con 1, 10 o 50 épocas.
    KNN          hecho a mano: el puntaje de un atuendo es la fracción de corazones entre los k votos más
                 cercanos (distancia manhattan, la misma de la búsqueda y del parecido).
    Parecido     mezcla de perceptrón y parecido al look con corazón más cercano, con 50 %, 90 % o 100 %.
    CNN 1D       (solo si hay modelo entrenado en entrenamiento_cnn/) la red sola, y lo que usa la app:
                 parecido 90 % con la red mezclada al perceptrón al 25, 50, 75 (PESO_CNN) o 100 %. La red ya
                 viene entrenada con 50 000 looks simulados, así que con estos votos solo predice.
  Decision Tree y Random Forest no entran: piden scikit-learn, que el proyecto no usa, y un bosque necesita
  muchos más votos de los que da una sola persona.

La medida es el "orden" de evaluacion_del_modelo.py: la probabilidad de que un atuendo con corazón quede por
encima de uno sin corazón (0.5 = al azar, 1 = perfecto). Es lo que hace la app: ordena y muestra los de arriba.

Con pocos votos, una sola división de entrenamiento y validación depende de la suerte. Por eso la prueba se
aparta una vez (semilla 42) y el resto se vuelve a dividir 20 veces en entrenamiento y validación; cada modelo
se califica con el promedio de las 20.
"""

import pandas as pd
from fastapi import APIRouter, Depends

from limpieza_de_datos.evaluacion_del_modelo import (CARPETA_CSV, REPETICIONES, SEMILLA, arriba, iniciales_de,
                                                     metricas, orden, tabla_de_votos)
from limpieza_de_datos.modelos import knn, parecido, perceptron
from servidor import red_convolucional
from servidor.aprendizaje import PESO_CNN, PESO_PARECIDO
from servidor.seguridad import usuario_actual

PROPORCION_PRUEBA = 0.20
PROPORCION_VALIDACION = 0.25  # del 80 % que queda: 0.25 × 80 % = 20 % del total
MODELOS = [  # (familia, parámetro): cada familia con los valores que se comparan
    ("perceptron", 1), ("perceptron", 10), ("perceptron", 50),
    ("knn", 1), ("knn", 3), ("knn", 5), ("knn", 9),
    ("parecido", 0.5), ("parecido", PESO_PARECIDO), ("parecido", 1.0),
]
# CNN 1D: la red sola y el sistema de la app con la red mezclada al perceptrón con varios pesos.
# Solo entran si hay modelo entrenado (columna "cnn" de tabla_de_votos). De aquí salió PESO_CNN.
MODELOS_CNN = [("cnn_sola", 1.0), ("cnn", 0.25), ("cnn", 0.5), ("cnn", 0.75), ("cnn", 1.0)]
SOBREAJUSTE = 0.15  # si entrenamiento le gana a validación por más de esto, memorizó
SUBAJUSTE = 0.60  # si ni en entrenamiento llega a esto, no aprendió


# ------------------------------------------------------------
# 1. DIVIDIR EN ENTRENAMIENTO, VALIDACIÓN Y PRUEBA (estratificado)
# ------------------------------------------------------------

def apartar(df: pd.DataFrame, proporcion: float, semilla: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Saca `proporcion` de los corazones y de los "no"; devuelve (lo que queda, lo apartado)."""
    apartado = df.groupby("me_gusta", group_keys=False).sample(frac=proporcion, random_state=semilla)
    return df.drop(apartado.index), apartado


# ------------------------------------------------------------
# 2. LOS MODELOS: aprenden de `entrenamiento` y califican `evaluar`
# ------------------------------------------------------------

def calificar(modelo: tuple, entrenamiento: pd.DataFrame, evaluar: pd.DataFrame, iniciales: dict) -> pd.Series:
    familia, parametro = modelo
    if familia == "perceptron":
        return perceptron(entrenamiento, evaluar, iniciales, epocas=parametro)
    if familia == "knn":
        return knn(entrenamiento, evaluar, parametro)  # distancia manhattan, todos los vecinos pesan igual
    if familia == "cnn_sola":
        return evaluar["cnn"]  # ya viene entrenada: no aprende de estos votos
    if familia == "cnn":
        return parecido(entrenamiento, evaluar, iniciales, PESO_PARECIDO, parametro)
    return parecido(entrenamiento, evaluar, iniciales, parametro)


def modelo_de_la_app(df: pd.DataFrame) -> tuple:
    return ("cnn", PESO_CNN) if "cnn" in df else ("parecido", PESO_PARECIDO)


def nombre(modelo: tuple) -> str:
    familia, parametro = modelo
    if familia == "perceptron":
        return f"Perceptrón ({parametro} épocas)"
    if familia == "knn":
        return f"KNN (k = {parametro})"
    if familia == "cnn_sola":
        return "CNN 1D sola"
    if familia == "cnn":
        actual = " (el de la app)" if parametro == PESO_CNN else ""
        return f"Parecido {round(PESO_PARECIDO * 100)} % + CNN {round(parametro * 100)} %{actual}"
    actual = ""
    if parametro == PESO_PARECIDO:
        actual = " (el de la app sin CNN)" if red_convolucional.modelo() else " (el de la app)"
    return f"Parecido {round(parametro * 100)} %{actual}"


# ------------------------------------------------------------
# 3. ENTRENAMIENTO CONTRA VALIDACIÓN (sobreajuste y subajuste)
# ------------------------------------------------------------

def diagnostico(entrenamiento: float, validacion: float) -> str:
    if entrenamiento < SUBAJUSTE:
        return "subajuste"
    if entrenamiento - validacion > SOBREAJUSTE:
        return "sobreajuste"
    return "buen ajuste"


def comparar(resto: pd.DataFrame, iniciales: dict, modelos: list[tuple]) -> pd.DataFrame:
    """Orden promedio de cada modelo en entrenamiento y en validación, con 20 divisiones del 80 % que queda."""
    suma = {modelo: [0.0, 0.0] for modelo in modelos}
    for semilla in range(REPETICIONES):
        entrenamiento, validacion = apartar(resto, PROPORCION_VALIDACION, semilla)
        for modelo in modelos:
            suma[modelo][0] += orden(entrenamiento["me_gusta"], calificar(modelo, entrenamiento, entrenamiento, iniciales))
            suma[modelo][1] += orden(validacion["me_gusta"], calificar(modelo, entrenamiento, validacion, iniciales))
    tabla = pd.DataFrame([{"modelo": nombre(m), "entrenamiento": round(e / REPETICIONES, 3),
                           "validacion": round(v / REPETICIONES, 3)} for m, (e, v) in suma.items()])
    tabla["diagnostico"] = [diagnostico(e, v) for e, v in zip(tabla["entrenamiento"], tabla["validacion"])]
    return tabla


# ------------------------------------------------------------
# 4. PRUEBA FINAL: solo el elegido (y el de la app, para comparar)
# ------------------------------------------------------------

def probar(modelo: tuple, resto: pd.DataFrame, prueba: pd.DataFrame, iniciales: dict) -> dict:
    """Aprende con entrenamiento + validación (todo el 80 %) y se mide una vez con la prueba."""
    puntaje = calificar(modelo, resto, prueba, iniciales)
    cuantos = max(1, round(len(prueba) * resto["me_gusta"].mean()))
    return {"modelo": nombre(modelo), **metricas(prueba["me_gusta"], arriba(puntaje, cuantos), puntaje)}


def conclusion(elegido: dict, actual: dict, tabla: pd.DataFrame, corazones_prueba: int) -> str:
    frase = (f"En validación ganó {elegido['modelo']} (orden {tabla['validacion'].max()}). "
             f"En la prueba final ordena {elegido['orden']} contra {actual['orden']} del modelo de la app.")
    sobreajustados = tabla.loc[tabla["diagnostico"] == "sobreajuste", "modelo"].tolist()
    if sobreajustados:
        frase += f" Con sobreajuste: {', '.join(sobreajustados)}."
    if corazones_prueba < 3:
        frase += (f" Ojo: la prueba solo tiene {corazones_prueba} atuendo(s) con corazón; con más votos el"
                  " resultado será más confiable.")
    return frase


# ------------------------------------------------------------
# RUTA
# ------------------------------------------------------------

rutas = APIRouter()


@rutas.get("/api/votos/seleccion")
def seleccionar_modelo(usuario: dict = Depends(usuario_actual)):
    """Compara los modelos con validación, elige el mejor y lo mide una sola vez con la prueba."""
    df = tabla_de_votos(usuario["id"])
    corazones = int(df["me_gusta"].sum())
    if corazones < 3 or len(df) - corazones < 3:
        return {"listo": False, "mensaje": "Hacen falta al menos 3 atuendos con corazón y 3 sin corazón para "
                                           "dividir en entrenamiento, validación y prueba."}
    iniciales = iniciales_de(usuario["id"])

    resto, prueba = apartar(df, PROPORCION_PRUEBA, SEMILLA)  # la prueba se aparta primero y no se toca
    modelos = MODELOS + (MODELOS_CNN if "cnn" in df else [])
    tabla = comparar(resto, iniciales, modelos)
    mejor = modelos[tabla["validacion"].idxmax()]  # se elige SOLO con validación (la tabla va en el orden de modelos)
    elegido = probar(mejor, resto, prueba, iniciales)
    actual = probar(modelo_de_la_app(df), resto, prueba, iniciales)

    CARPETA_CSV.mkdir(exist_ok=True)
    tabla.to_csv(CARPETA_CSV / f"seleccion_usuario_{usuario['id']}.csv", index=False, encoding="utf-8")
    entrenamiento, validacion = apartar(resto, PROPORCION_VALIDACION, SEMILLA)  # solo para contar

    return {
        "listo": True,
        "datos": {"votos_validos": len(df), "con_corazon": corazones, "entrenamiento": len(entrenamiento),
                  "validacion": len(validacion), "prueba": len(prueba),
                  "corazones_en_prueba": int(prueba["me_gusta"].sum())},
        "comparacion": tabla.to_dict(orient="records"),
        "elegido": elegido,
        "modelo_de_la_app": actual,
        "conclusion": conclusion(elegido, actual, tabla, int(prueba["me_gusta"].sum())),
        "archivo": f"limpieza_de_datos/datos/seleccion_usuario_{usuario['id']}.csv",
    }
