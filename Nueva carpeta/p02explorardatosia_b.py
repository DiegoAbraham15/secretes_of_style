
# ============================================================
# PRACTICA 2 - PARTE B
# EXPLORACION DEL CONJUNTO DE DATOS
# ============================================================

#No basta con tener datos. Antes de utilizarlos, 
#necesitamos conocer su estructura, sus tipos y sus características estadísticas.

import pandas as pd

# Leer el archivo CSV creado en la parte anterior.
df = pd.read_csv("estudiantes.csv")

# ------------------------------------------------------------
# 1. MOSTRAR LOS PRIMEROS REGISTROS
# ------------------------------------------------------------
# head() muestra las primeras cinco filas por defecto.

print("=== PRIMEROS REGISTROS ===")
print(df.head())

# ------------------------------------------------------------
# 2. MOSTRAR LOS ULTIMOS REGISTROS
# ------------------------------------------------------------
print("\n=== ULTIMOS REGISTROS ===")
print(df.tail())

# ------------------------------------------------------------
# 3. CONOCER LOS TIPOS DE DATOS
# ------------------------------------------------------------
# Los nombres de estudiantes son texto.
# Las horas, porcentajes y calificaciones son numericos.

print("\n=== TIPOS DE DATOS ===")
print(df.dtypes)

# ------------------------------------------------------------
# 4. OBTENER INFORMACION GENERAL
# ------------------------------------------------------------
# info() muestra las columnas, los valores no nulos
# y los tipos de datos.

print("\n=== INFORMACION GENERAL ===")
df.info()

# ------------------------------------------------------------
# 5. CALCULAR ESTADISTICAS DESCRIPTIVAS
# ------------------------------------------------------------
# describe() calcula estadisticas para las columnas numericas.
# Incluye media, desviacion estandar, minimo, maximo
# y algunos percentiles.

print("\n=== ESTADISTICAS DESCRIPTIVAS ===")
print(df.describe())

# ------------------------------------------------------------
# 6. CONSULTAR UNA COLUMNA
# ------------------------------------------------------------
print("\n=== HORAS DE ESTUDIO ===")
print(df["horas_estudio", "estudiante"])

# ------------------------------------------------------------
# 7. CALCULAR EL PROMEDIO DE CALIFICACIONES
# ------------------------------------------------------------
promedio = df["calificacion"].mean()

print("\nPromedio de calificaciones:", round(promedio, 2))

#Función	¿Para qué sirve?
#head()	    Muestra las primeras filas.
#tail()	    Muestra las últimas filas.
#shape	    Devuelve filas y columnas.
#dtypes	    Indica el tipo de cada columna.
#info()	    Resume la estructura y los valores no nulos.
#describe()	Calcula estadísticas descriptivas.
#mean()	    Calcula la media aritmética.

#Las estadísticas permiten conocer los datos, 
#pero no demuestran por sí mismas que una variable cause otra. 
#Por ejemplo, que los estudiantes con más horas de estudio 
#tengan mejores calificaciones en esta tabla no demuestra 
#una relación causal ni garantiza el mismo comportamiento en otros grupos.