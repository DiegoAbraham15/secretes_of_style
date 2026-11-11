
# ============================================================
# PRACTICA 2 - PARTE D
# LIMPIEZA BASICA Y EXPORTACION
# ============================================================

#Estrategia de limpieza
#Para este ejercicio utilizaremos una estrategia sencilla:
#- Eliminar filas completamente duplicadas.
#- Conservar los valores faltantes como tales durante la inspección.
#- Marcar los registros con valores fuera de rango.
#- Excluir los registros incompletos o inválidos de un archivo de práctica, 
# explicando por qué se excluyeron.

#En un proyecto real, eliminar filas no siempre es la mejor opción. 
#La estrategia debe elegirse según la cantidad de datos, 
#la causa de los valores faltantes y el objetivo del análisis.

import pandas as pd

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

# ------------------------------------------------------------
# PASO 1. ELIMINAR FILAS COMPLETAMENTE DUPLICADAS
# ------------------------------------------------------------
df_limpio = df.drop_duplicates().copy()

# ------------------------------------------------------------
# PASO 2. IDENTIFICAR REGISTROS VALIDOS
# ------------------------------------------------------------
# Comprobar que no existan valores faltantes en las columnas
# requeridas y que los porcentajes y calificaciones estén
# dentro de sus rangos permitidos.

columnas_requeridas = [
    "estudiante",
    "horas_estudio",
    "asistencia",
    "calificacion"
]

completo = df_limpio[columnas_requeridas].notna().all(axis=1)

asistencia_valida = df_limpio["asistencia"].between(0, 100)

calificacion_valida = df_limpio["calificacion"].between(0, 100)

horas_validas = df_limpio["horas_estudio"] >= 0

# Combinar las condiciones.
valido = (
    completo
    & asistencia_valida
    & calificacion_valida
    & horas_validas
)

# ------------------------------------------------------------
# PASO 3. SEPARAR LOS REGISTROS VALIDOS
# ------------------------------------------------------------
df_validos = df_limpio.loc[valido].copy()

# Los registros descartados se conservan para poder auditarlos.
df_revision = df_limpio.loc[~valido].copy()

print("=== REGISTROS VALIDOS ===")
print(df_validos)

print("\n=== REGISTROS QUE REQUIEREN REVISION ===")
print(df_revision)

# ------------------------------------------------------------
# PASO 4. EXPORTAR LOS RESULTADOS
# ------------------------------------------------------------
df_validos.to_csv(
    "estudiantes_limpios.csv",
    index=False,
    encoding="utf-8"
)

df_revision.to_csv(
    "estudiantes_revision.csv",
    index=False,
    encoding="utf-8"
)

print("\nArchivos generados:")
print("- estudiantes_limpios.csv")
print("- estudiantes_revision.csv")


#Ahora tenemos dos archivos:
#- estudiantes_limpios.csv: contiene los registros que cumplen las condiciones definidas para el ejercicio.
#- estudiantes_revision.csv: conserva los registros que requieren revisión.
#Esta separación ayuda a evitar que los datos problemáticos desaparezcan sin explicación. 

#En un sistema profesional, también convendría registrar el motivo de exclusión y 
#revisar los valores con la persona responsable de los datos.