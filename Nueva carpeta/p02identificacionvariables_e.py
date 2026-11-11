
# ============================================================
# PRACTICA 2 - PARTE E
# PREPARAR LAS VARIABLES DE ENTRADA Y EL OBJETIVO
# ============================================================

#Supongamos que queremos entrenar un modelo para estimar la calificación de un estudiante.

#Definimos:
#- Variables de entrada (X): horas de estudio, asistencia y actividades entregadas.
#- Variable objetivo (y): calificación.
#En notación habitual de aprendizaje automático:

#X = [horas de estudio, asistencia, actividades entregadas]

#y = [calificación]

#Todavía no estamos entrenando un modelo. 
#Únicamente estamos preparando la estructura de los datos que necesitará.

import pandas as pd

# Cargar el conjunto de datos original.
df = pd.read_csv("estudiantes.csv")

# ------------------------------------------------------------
# 1. SELECCIONAR LAS VARIABLES DE ENTRADA
# ------------------------------------------------------------
# X contiene las características que utilizaremos
# para explicar o estimar la calificación.

X = df[
    [
        "horas_estudio",
        "asistencia",
        "actividades_entregadas"
    ]
]

# ------------------------------------------------------------
# 2. SELECCIONAR LA VARIABLE OBJETIVO
# ------------------------------------------------------------
# y contiene el resultado que queremos estimar.

y = df["calificacion"]

# ------------------------------------------------------------
# 3. MOSTRAR LOS DATOS
# ------------------------------------------------------------
print("=== VARIABLES DE ENTRADA: X ===")
print(X.head())

print("\n=== VARIABLE OBJETIVO: y ===")
print(y.head())

print("\nDimensiones de X:", X.shape)
print("Dimensiones de y:", y.shape)

# ------------------------------------------------------------
# 4. COMPROBAR LA CORRESPONDENCIA ENTRE X E y
# ------------------------------------------------------------
# Cada fila de X debe corresponder al mismo estudiante
# que el valor ubicado en la misma posición de y.

assert len(X) == len(y), "X e y tienen diferente cantidad de filas"

print("\nLas entradas y el objetivo están alineados.")


#Un modelo supervisado utiliza ejemplos en los que conocemos 
#tanto las entradas como el resultado esperado. Durante el entrenamiento,
#el modelo busca relaciones entre ambos.

#Por ejemplo, el modelo recibirá información sobre las horas de estudio, 
#la asistencia y las actividades entregadas, y utilizará las calificaciones 
#conocidas para ajustar sus parámetros.

#Sin embargo, debemos tener cuidado: los datos de esta práctica son ficticios 
#y muy pequeños. Sirven para aprender el procedimiento, 
#no para crear un predictor académico fiable.