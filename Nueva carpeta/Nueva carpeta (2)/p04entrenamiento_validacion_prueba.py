
# ============================================================
# FUNDAMENTOS DE INTELIGENCIA ARTIFICIAL
# PRACTICA 04:
# ENTRENAMIENTO, VALIDACION Y PRUEBA
# ============================================================
#
# CASO DE ESTUDIO: SMARTACADEMY
# Una institución educativa desea implementar un sistema inteligente 
# que permita identificar patrones relacionados con el desempeño académico de sus estudiantes.

# OBJETIVO:
# Comprender como evaluar un modelo de Machine Learning
# y detectar problemas de sobreajuste (overfitting) El modelo aprende demasiado los detalles 
# de los datos de entrenamiento, incluyendo ruido, y pierde capacidad para generalizar. 
# y subajuste (underfitting), El modelo es demasiado sencillo y no logra aprender 
# adecuadamente los patrones de los datos, Buen ajuste El modelo aprende patrones útiles 
# y mantiene un desempeño razonable en datos nuevos.
#
# Variable	        Descripción
# horas_estudio	    Horas de estudio semanales
# asistencia	    Porcentaje de asistencia
# actividades	    Porcentaje de actividades entregadas
# participacion	    Nivel de participación de 0 a 10
# calificacion	    Calificación final
# aprueba	        1 = aprueba, 0 = no aprueba
#
# Division  de los datos 
# 
# 60% entrenamiento
# 20% validación
# 20% prueba 

# Diferencias entre los tres conjuntos

# Conjunto	        ¿Para qué sirve?

# Entrenamiento	    Aprender patrones.
# Validación	    Ajustar parámetros y elegir modelos.
# Prueba	        Evaluar el desempeño final con datos no utilizados anteriormente.
#
#
# NOTA:
# Los datos generados son sinteticos y tienen fines educativos.
# No representan resultados reales de estudiantes.
# ============================================================


# ------------------------------------------------------------
# 1. IMPORTAR BIBLIOTECAS
# ------------------------------------------------------------

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Herramienta para separar los conjuntos de datos.
from sklearn.model_selection import train_test_split

# Herramienta para validacion cruzada.
from sklearn.model_selection import cross_val_score

# Modelo de clasificacion.
from sklearn.tree import DecisionTreeClassifier

# Metricas de evaluacion.
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)


# ------------------------------------------------------------
# 2. CREAR CARPETA DE RESULTADOS
# ------------------------------------------------------------

# os.makedirs permite crear directorios.
# exist_ok=True evita errores si ya existe la carpeta.

os.makedirs("resultados", exist_ok=True)


# ------------------------------------------------------------
# 3. GENERAR DATOS SINTETICOS
# ------------------------------------------------------------

# Fijamos una semilla para reproducir los datos.
# Esto permite que los alumnos obtengan resultados
# consistentes al ejecutar nuevamente el programa.

np.random.seed(42)

# Definimos el numero de estudiantes ficticios.
cantidad_estudiantes = 500

# Generamos las variables de entrada.
horas_estudio = np.random.uniform(
    0, 15, cantidad_estudiantes
)

asistencia = np.random.uniform(
    30, 100, cantidad_estudiantes
)

actividades = np.random.uniform(
    10, 100, cantidad_estudiantes
)

participacion = np.random.uniform(
    0, 10, cantidad_estudiantes
)

# Construimos una puntuacion sintetica.
#
# Esta formula sirve para producir una variable objetivo
# con patrones que el modelo pueda intentar aprender.
#
# El ruido evita que todos los registros sigan una regla
# perfectamente determinista y puedan estar apegados a la realidad.

ruido = np.random.normal(
    0, 7, cantidad_estudiantes
)

puntuacion = (
    horas_estudio * 2.5
    + asistencia * 0.25
    + actividades * 0.15
    + participacion * 1.5
    + ruido
)

# Creamos la variable objetivo.
# 1 = aprueba.
# 0 = no aprueba.
#
# El umbral es una regla de generacion de datos ficticios,
# no un criterio institucional real.

aprueba = (puntuacion >= 55).astype(int)

# Construimos el DataFrame.
df = pd.DataFrame({
    "horas_estudio": horas_estudio,
    "asistencia": asistencia,
    "actividades": actividades,
    "participacion": participacion,
    "aprueba": aprueba
})

print("\n==========================================")
print("1. DATOS GENERADOS")
print("==========================================")

print(df.head(10))

print("\nCantidad de registros:")
print(len(df))

print("\nDistribucion de las clases:")
print(df["aprueba"].value_counts())


# ------------------------------------------------------------
# 4. DEFINIR VARIABLES DE ENTRADA Y OBJETIVO
# ------------------------------------------------------------

# X contiene las caracteristicas utilizadas para aprender.

X = df[
    [
        "horas_estudio",
        "asistencia",
        "actividades",
        "participacion"
    ]
]

# y contiene la clase que queremos predecir.

y = df["aprueba"]


# ------------------------------------------------------------
# 5. SEPARAR ENTRENAMIENTO Y DATOS TEMPORALES
# ------------------------------------------------------------

# Primero reservamos el 40 % de los datos.
#
# El 60 % restante sera utilizado para entrenamiento.
# El 40 % temporal se dividira despues entre validacion
# y prueba.

X_entrenamiento, X_temporal, y_entrenamiento, y_temporal = (
    train_test_split(
        X,
        y,
        test_size=0.40,
        random_state=42,
        stratify=y
    )
)


# ------------------------------------------------------------
# 6. DIVIDIR VALIDACION Y PRUEBA
# ------------------------------------------------------------

# Del conjunto temporal tomamos la mitad para validacion
# y la otra mitad para prueba.
#
# Resultado final:
# 60 % entrenamiento.
# 20 % validacion.
# 20 % prueba.

X_validacion, X_prueba, y_validacion, y_prueba = (
    train_test_split(
        X_temporal,
        y_temporal,
        test_size=0.50,
        random_state=42,
        stratify=y_temporal
    )
)

print("\n==========================================")
print("2. DISTRIBUCION DE LOS CONJUNTOS")
print("==========================================")

print("Entrenamiento:", len(X_entrenamiento))
print("Validacion:", len(X_validacion))
print("Prueba:", len(X_prueba))


# ------------------------------------------------------------
# 7. ENTRENAR MODELOS CON DIFERENTES PROFUNDIDADES
# ------------------------------------------------------------

# La profundidad determina cuantas divisiones puede
# desarrollar el arbol de decisiones.
#
# Un arbol muy profundo puede aprender detalles excesivos.
# Un arbol demasiado pequeño puede no aprender suficiente.

profundidades = [1, 2, 3, 5, 10, None]

# Diccionario para guardar los resultados.
resultados = []

# Guardamos los modelos para analizarlos despues.
modelos = {}

for profundidad in profundidades:

    print("\n--------------------------------------")
    print("Entrenando modelo:", profundidad)
    print("--------------------------------------")

    # Creamos el clasificador.
    modelo = DecisionTreeClassifier(
        max_depth=profundidad,
        random_state=42
    )

    # Entrenamos utilizando exclusivamente
    # el conjunto de entrenamiento.
    modelo.fit(
        X_entrenamiento,
        y_entrenamiento
    )

    # Evaluamos el conjunto de entrenamiento.
    pred_entrenamiento = modelo.predict(
        X_entrenamiento
    )

    # Evaluamos el conjunto de validacion.
    pred_validacion = modelo.predict(
        X_validacion
    )

    # Calculamos exactitud en entrenamiento.
    exactitud_entrenamiento = accuracy_score(
        y_entrenamiento,
        pred_entrenamiento
    )

    # Calculamos exactitud en validacion.
    exactitud_validacion = accuracy_score(
        y_validacion,
        pred_validacion
    )

    # Guardamos el modelo.
    modelos[profundidad] = modelo

    # Guardamos las metricas.
    resultados.append({
        "profundidad": (
            "Sin limite"
            if profundidad is None
            else str(profundidad)
        ),
    
    #Valor numerico para construir las graficas
    #Utilizamos 12 como posicion visual del modelo
    #cuya profundidad no tiene limite
        "profundidad_grafica": (
            12
            if profundidad is None
            else profundidad
        ),

        "entrenamiento": exactitud_entrenamiento,

        "validacion": exactitud_validacion
    })


# Convertimos los resultados en una tabla.
df_resultados = pd.DataFrame(resultados)

print("\n==========================================")
print("3. COMPARACION DE MODELOS")
print("==========================================")

print(
    df_resultados[
        ["profundidad", "entrenamiento", "validacion"]
    ].to_string(index=False)
)


# ------------------------------------------------------------
# 8. IDENTIFICAR POSIBLES PROBLEMAS DE AJUSTE
# ------------------------------------------------------------

print("\n==========================================")
print("4. ANALISIS DE AJUSTE")
print("==========================================")

for _, fila in df_resultados.iterrows():

    diferencia = (
        fila["entrenamiento"]
        - fila["validacion"]
    )

    profundidad = fila["profundidad"]

    print("\nModelo:", profundidad)

    print(
        "Exactitud entrenamiento:",
        f"{fila['entrenamiento']:.2%}"
    )

    print(
        "Exactitud validacion:",
        f"{fila['validacion']:.2%}"
    )

    print(
        "Diferencia:",
        f"{diferencia:.2%}"
    )

    # Estas condiciones son indicadores didacticos,
    # no una prueba definitiva de sobreajuste.

    if (
        fila["entrenamiento"] < 0.70
        and fila["validacion"] < 0.70
    ):
        print("Posible subajuste.")

    elif diferencia > 0.10:
        print("Posible sobreajuste.")

    else:
        print("No se observa una brecha grande.")


# ------------------------------------------------------------
# 9. SELECCIONAR EL MODELO CON MEJOR VALIDACION
# ------------------------------------------------------------

# Buscamos el registro que obtuvo la mayor exactitud
# en el conjunto de validacion.

indice_mejor = df_resultados[
    "validacion"
].idxmax()

mejor_registro = df_resultados.loc[indice_mejor]

# Recuperamos la profundidad seleccionada.
profundidad_seleccionada = int(
    df_resultados.loc[
    indice_mejor, 
    "profundidad_grafica"
]
)

if profundidad_seleccionada == 12:
    profundidad_seleccionada = None

# Recuperamos el modelo correspondiente.
mejor_modelo = modelos[profundidad_seleccionada]

print("\n==========================================")
print("5. MODELO SELECCIONADO")
print("==========================================")

print(
    "Profundidad seleccionada:",
    mejor_registro["profundidad"]
)

print(
    "Exactitud de validacion:",
    f"{mejor_registro['validacion']:.2%}"
)
print(
    "Configuracion interna del modelo:",
    mejor_modelo.get_params()["max_depth"]
)

# ------------------------------------------------------------
# 10. EVALUACION FINAL CON EL CONJUNTO DE PRUEBA
# ------------------------------------------------------------

# IMPORTANTE:
# El conjunto de prueba no se utilizo para entrenar
# ni para seleccionar la profundidad del modelo.
#
# Ahora lo utilizamos para estimar el rendimiento final.

pred_prueba = mejor_modelo.predict(X_prueba)

exactitud = accuracy_score(
    y_prueba,
    pred_prueba
)

precision = precision_score(
    y_prueba,
    pred_prueba,
    zero_division=0
)

recall = recall_score(
    y_prueba,
    pred_prueba,
    zero_division=0
)

f1 = f1_score(
    y_prueba,
    pred_prueba,
    zero_division=0
)

print("\n==========================================")
print("6. EVALUACION FINAL")
print("==========================================")

print(f"Exactitud: {exactitud:.2%}")
print(f"Precision: {precision:.2%}")
print(f"Recall: {recall:.2%}")
print(f"F1-score: {f1:.2%}")


# ------------------------------------------------------------
# 11. REPORTE DE CLASIFICACION
# ------------------------------------------------------------

print("\n==========================================")
print("7. REPORTE DE CLASIFICACION")
print("==========================================")

print(
    classification_report(
        y_prueba,
        pred_prueba,
        labels=[0, 1],
        target_names=["No aprueba", "Aprueba"],
        zero_division=0
    )
)


# ------------------------------------------------------------
# 12. MATRIZ DE CONFUSION
# ------------------------------------------------------------

matriz = confusion_matrix(
    y_prueba,
    pred_prueba,
    labels=[0, 1]
)

print("\n==========================================")
print("8. MATRIZ DE CONFUSION")
print("==========================================")

print(matriz)


# ------------------------------------------------------------
# 13. VALIDACION CRUZADA
# ------------------------------------------------------------

# La validacion cruzada divide los datos de entrenamiento
# en diferentes particiones.
#
# En cada iteracion:
# - una parte se utiliza para validar;
# - las restantes se utilizan para entrenar.
#
# No utilizamos el conjunto de prueba en este proceso.

modelo_cv = DecisionTreeClassifier(
    max_depth=profundidad_seleccionada,
    random_state=42
)

puntuaciones_cv = cross_val_score(
    modelo_cv,
    X_entrenamiento,
    y_entrenamiento,
    cv=5,
    scoring="accuracy"
)

print("\n==========================================")
print("9. VALIDACION CRUZADA")
print("==========================================")

print("Resultados de cada particion:")
print(puntuaciones_cv)

print(
    "Promedio:",
    f"{puntuaciones_cv.mean():.2%}"
)

print(
    "Desviacion estandar:",
    f"{puntuaciones_cv.std():.2%}"
)


# ------------------------------------------------------------
# 14. GRAFICA: ENTRENAMIENTO VS VALIDACION
# ------------------------------------------------------------

plt.figure(figsize=(11, 6))

# Eje X: utilizamos exclusivamente valores numericos.
x = df_resultados["profundidad_grafica"]

# Graficamos el rendimiento de entrenamiento.
plt.plot(
    x,
    df_resultados["entrenamiento"],
    marker="o",
    linewidth=2,
    label="Entrenamiento"
)

# Graficamos el rendimiento de validacion.
plt.plot(
    x,
    df_resultados["validacion"],
    marker="s",
    linewidth=2,
    label="Validacion"
)

# Etiquetas personalizadas para el eje X.
etiquetas = df_resultados["profundidad"]

plt.xticks(
    x,
    etiquetas
)

plt.title(
    "Comparacion del rendimiento de los modelos",
    fontsize=14
)

plt.xlabel(
    "Profundidad del arbol"
)

plt.ylabel(
    "Exactitud"
)

plt.ylim(0, 1.05)

plt.grid(
    True,
    linestyle="--",
    alpha=0.5
)

plt.legend()

plt.tight_layout()

# Guardamos la grafica.
plt.savefig(
    "resultados/comparacion_modelos.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()


# ------------------------------------------------------------
# 15. GRAFICA: MATRIZ DE CONFUSION
# ------------------------------------------------------------

plt.figure(figsize=(7, 6))

plt.imshow(matriz)

plt.title("Matriz de confusion")

plt.xlabel("Prediccion del modelo")

plt.ylabel("Resultado real")

plt.xticks(
    [0, 1],
    ["No aprueba", "Aprueba"]
)

plt.yticks(
    [0, 1],
    ["No aprueba", "Aprueba"]
)

# Agregamos el numero de casos dentro de cada celda.
for fila in range(2):

    for columna in range(2):

        plt.text(
            columna,
            fila,
            str(matriz[fila, columna]),
            ha="center",
            va="center",
            fontsize=14
        )

plt.colorbar()

plt.tight_layout()

plt.savefig(
    "resultados/matriz_confusion.png",
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 16. EXPORTAR RESULTADOS
# ------------------------------------------------------------

# Guardamos la tabla comparativa en formato CSV.

df_resultados.to_csv(
    "resultados/comparacion_modelos.csv",
    index=False
)

# Guardamos las predicciones finales.

df_predicciones = X_prueba.copy()

df_predicciones["resultado_real"] = y_prueba

df_predicciones["prediccion"] = pred_prueba

df_predicciones.to_csv(
    "resultados/predicciones_prueba.csv",
    index=False
)


# ------------------------------------------------------------
# 17. CONCLUSIONES AUTOMATICAS
# ------------------------------------------------------------

print("\n==========================================")
print("10. CONCLUSIONES")
print("==========================================")

print(
    "El entrenamiento permite aprender patrones "
    "a partir de ejemplos."
)

print(
    "La validacion ayuda a seleccionar configuraciones "
    "sin utilizar los datos de prueba."
)

print(
    "La prueba permite estimar el comportamiento "
    "del modelo en registros no utilizados anteriormente."
)

print(
    "Una diferencia grande entre entrenamiento y validacion "
    "puede indicar sobreajuste."
)

print(
    "La validacion cruzada permite estudiar la estabilidad "
    "del rendimiento en distintas particiones."
)

print("\nArchivos generados en la carpeta resultados.")

print("\nPRACTICA 04 FINALIZADA.")


#¿Qué se aprende de la comparación?

# Profundidad	Entrenamiento	Validación	Interpretación

#       1	        83.67%	        78%	    Ajuste limitado
#       2	        83.67%	        78%	    Ajuste limitado
#       3	        86.67%	        81%	    Buen comportamiento
#       5	        92.67%	        87%	    Mejor resultado
#       10	        99.67%	        76%	    Sobreajuste
#   Sin límite	    100%	        75%	    Sobreajuste

#La profundidad 5 obtuvo el mejor resultado de validación. 
#En cambio, los modelos de profundidad 10 y sin límite memorizaron prácticamente 
#los datos de entrenamiento, pero perdieron capacidad de generalización.

#Concepto importante: un modelo que obtiene 100% 
#durante el entrenamiento no necesariamente es el mejor modelo. 

#Lo importante es su capacidad para trabajar correctamente con datos que no conoce.

#Interpretación de la matriz de confusión

#El resultado fue:

#   [[60  1]
#   [11 28]]

#Considerando que la clase positiva es Aprueba = 1:

#Resultado	            Cantidad	    Interpretación

#Verdaderos negativos	    60	        Predijo que no aprobaba y efectivamente no aprobó.
#Falsos positivos	        1	        Predijo que aprobaba, pero no aprobó.
#Falsos negativos	        11	        Predijo que no aprobaba, pero sí aprobó.
#Verdaderos positivos	    28	        Predijo que aprobaba y efectivamente aprobó.

#Un aspecto importante es que el modelo tiene una precisión alta (96.55%), pero su recall es de 71.79%.

#Esto significa que, de los 39 estudiantes que realmente aprobaron, 
#identificó correctamente a 28 y no detectó a 11.

#Para un sistema educativo real, esto merece atención: si el propósito es identificar 
#estudiantes que pueden aprobar, convendría mejorar la capacidad del modelo para reconocer esa clase, 
#por lo cual dependerá de lo que se quiere buscar en un ambiente real.

#La validación cruzada obtuvo:

#- Promedio: 79.67%.
#- Desviación estándar: 1.63%.

#Hay una diferencia entre el 87% de validación y el 79.67% de validación cruzada. 

#No necesariamente significa que exista un error.

#Puede deberse a que las particiones utilizadas son diferentes y a que la validación 
#cruzada evalúa el modelo en cinco particiones del conjunto que se le proporcionó.
#o incluso un problema con los datos.

#Para que la comparación sea metodológicamente más clara, 
#verifica que la validación cruzada se esté aplicando al conjunto de entrenamiento y no al conjunto completo. 

#También conviene utilizar StratifiedKFold para conservar la proporción de las clases.