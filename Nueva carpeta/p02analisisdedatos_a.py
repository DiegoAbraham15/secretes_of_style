
# ============================================================
# PRACTICA 2 - PARTE A
# CREACION DE UN CONJUNTO DE DATOS
# ============================================================

# pandas es una biblioteca de Python para trabajar con tablas.

#Al ejecutar el código, se habrá creado una tabla y la habrán guardado en un archivo CSV.

#El archivo CSV es importante porque permite almacenar los datos de forma independiente del programa. 
#Más adelante podremos cargar ese archivo para entrenar distintos modelos sin tener que escribir 
#nuevamente toda la información.

#Actividad rápida: agregar mas estudiantes con datos inventados y comprobar cómo cambian las 
#dimensiones de la tabla.

import pandas as pd

# ------------------------------------------------------------
# PASO 1. CREAR LOS DATOS
# ------------------------------------------------------------
# Cada diccionario representa una columna.
# Las listas contienen los valores correspondientes a cada fila.

datos = {
    "estudiante": [
        "Ana", "Luis", "Maria", "Carlos", "Sofia",
        "Pedro", "Elena", "Jorge"
    ],

    "horas_estudio": [
        8, 3, 10, 5, 6, 2, 7, 4
    ],

    "asistencia": [
        95, 60, 98, 75, 85, 55, 90, 70
    ],

    "actividades_entregadas": [
        100, 50, 100, 80, 90, 40, 95, 65
    ],

    "calificacion": [
        92, 58, 96, 72, 81, 50, 88, 64
    ]
}

# ------------------------------------------------------------
# PASO 2. CONVERTIR LOS DATOS EN UN DATAFRAME
# ------------------------------------------------------------
# Un DataFrame es una estructura tabular de pandas.
# Podemos imaginarlo como una hoja de cálculo.

df = pd.DataFrame(datos)

# ------------------------------------------------------------
# PASO 3. MOSTRAR LA TABLA
# ------------------------------------------------------------
print("=== CONJUNTO DE DATOS ORIGINAL ===")
print(df)

# ------------------------------------------------------------
# PASO 4. CONSULTAR EL TAMANO DE LA TABLA
# ------------------------------------------------------------
# shape devuelve una tupla:
# (numero de filas, numero de columnas)

print("\nDimensiones de la tabla:")
print(df.shape)

print("Numero de estudiantes:", df.shape[0])
print("Numero de variables:", df.shape[1])

# ------------------------------------------------------------
# PASO 5. GUARDAR LOS DATOS EN UN ARCHIVO CSV
# ------------------------------------------------------------
# index=False evita agregar una columna adicional con
# los indices internos de pandas.

df.to_csv(
    "estudiantes.csv",
    index=False,
    encoding="utf-8"
)

print("\nArchivo estudiantes.csv creado correctamente.")
