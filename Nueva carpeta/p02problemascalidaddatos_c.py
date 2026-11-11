
# ============================================================
# PRACTICA 2 - PARTE C
# DETECCION DE ERRORES EN LOS DATOS
# ============================================================

#¿Por qué es importante limpiar los datos?
#Imagina que alguien registra por error:
#- Una asistencia de 110%.
#- Una calificación vacía.
#- El mismo estudiante dos veces.
#- Un valor de horas de estudio como texto en lugar de número.
#Si utilizamos esos datos sin revisarlos, los resultados del análisis podrían ser incorrectos.

#Para practicar, introduciremos algunos errores deliberadamente.


import pandas as pd

# Crear un conjunto pequeño con errores intencionales.
datos_prueba = {
    "estudiante": [
        "Ana", "Luis", "Maria", "Luis", "Carlos"
    ],

    "horas_estudio": [
        8, 3, None, 3, 5
    ],

    "asistencia": [
        95, 60, 98, 60, 110
    ],

    "calificacion": [
        92, 58, 96, 58, None
    ]
}

df = pd.DataFrame(datos_prueba)

print("=== DATOS CON PROBLEMAS ===")
print(df)

# ------------------------------------------------------------
# 1. BUSCAR VALORES FALTANTES
# ------------------------------------------------------------
# isnull() identifica los valores ausentes.
# sum() cuenta cuántos hay en cada columna.

print("\n=== VALORES FALTANTES POR COLUMNA ===")
print(df.isnull().sum())

# ------------------------------------------------------------
# 2. CONTAR FILAS CON ALGUN DATO FALTANTE
# ------------------------------------------------------------
filas_incompletas = df.isnull().any(axis=1).sum()

print("\nFilas con al menos un valor faltante:")
print(filas_incompletas)

# ------------------------------------------------------------
# 3. DETECTAR REGISTROS DUPLICADOS
# ------------------------------------------------------------
# duplicated() detecta filas completamente repetidas.
# No identifica necesariamente personas repetidas
# cuando sus otros datos son diferentes.

print("\n=== FILAS DUPLICADAS ===")
print(df[df.duplicated()])

# ------------------------------------------------------------
# 4. REVISAR LOS RANGOS DE LAS VARIABLES
# ------------------------------------------------------------
# En este ejemplo, asistencia y calificacion
# deberían estar entre 0 y 100.

asistencia_invalida = (
    (df["asistencia"] < 0) |
    (df["asistencia"] > 100)
)

print("\n=== ASISTENCIAS FUERA DE RANGO ===")
print(df[asistencia_invalida])

calificacion_invalida = (
    (df["calificacion"] < 0) |
    (df["calificacion"] > 100)
)

print("\n=== CALIFICACIONES FUERA DE RANGO ===")
print(df[calificacion_invalida])
