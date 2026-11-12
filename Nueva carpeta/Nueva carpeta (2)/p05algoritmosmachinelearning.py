
# ================================================================
# PROYECTO: SMARTACADEMY
# PRACTICA 05: COMPARACION DE ALGORITMOS DE MACHINE LEARNING
#
# Archivo:
# p05comparacion_algoritmos_clasificacion.py
#
# Objetivo:
# Comparar tres algoritmos de clasificacion:
#
# 1. Decision Tree
# 2. Random Forest
# 3. K-Nearest Neighbors (KNN)
#
# Se utilizara un problema de clasificacion binaria:
# 0 = El estudiante NO aprueba.
# 1 = El estudiante SI aprueba.
#
#1.- Decision Tree — Árbol de decisión
#Construye reglas de decisión a partir de las características de los estudiantes.

#2.- Random Forest — Bosque aleatorio
#Combina múltiples árboles de decisión para producir una predicción.

#3.- K-Nearest Neighbors (KNN)
#Clasifica a un estudiante considerando los registros más cercanos según sus características.

#Caso de estudio
#SmartAcademy necesita desarrollar un módulo inteligente que permita 
#estimar si un estudiante aprobará una asignatura.

#Para ello se utilizará las siguientes variables:

#Variable	        Descripción	                            Tipo

#horas_estudio	    Horas dedicadas al estudio	            Numérica
#asistencia	        Porcentaje de asistencia	            Numérica
#actividades	    Porcentaje de actividades entregadas	Numérica
#participacion	    Nivel de participación	                Numérica
#aprueba	        0 = No, 1 = Sí	                        Objetivo

#Pregunta: ¿Cuál de los tres algoritmos consigue predecir mejor 
#el resultado académico de los estudiantes cuando trabaja con datos que nunca ha visto?

# IMPORTANTE:
# Los datos de esta practica son sinteticos y se utilizan
# exclusivamente con fines educativos.
# ================================================================


# ================================================================
# 1. IMPORTAR LAS BIBLIOTECAS
# ================================================================

# NumPy permite realizar operaciones matematicas y generar datos.
import numpy as np

# Pandas permite organizar los datos en tablas.
import pandas as pd

# Matplotlib permite crear graficas.
import matplotlib.pyplot as plt

# train_test_split divide los datos en entrenamiento,
# validacion y prueba.
from sklearn.model_selection import train_test_split

# cross_val_score realiza validacion cruzada.
from sklearn.model_selection import cross_val_score

# DecisionTreeClassifier implementa arboles de decision.
from sklearn.tree import DecisionTreeClassifier

# RandomForestClassifier implementa bosques aleatorios.
from sklearn.ensemble import RandomForestClassifier

# KNeighborsClassifier implementa el algoritmo KNN.
from sklearn.neighbors import KNeighborsClassifier

# StandardScaler normaliza las variables numericas.
from sklearn.preprocessing import StandardScaler

# Pipeline permite unir el escalamiento y el algoritmo.
from sklearn.pipeline import Pipeline

# clone permite crear una copia de un modelo
# conservando su configuracion.
from sklearn.base import clone

# Metricas para evaluar los modelos.
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay
)


# ================================================================
# 2. CONFIGURACION GENERAL
# ================================================================

# Fijamos una semilla para obtener resultados reproducibles.
# Esto permite que se obtengan los mismos datos
# cuando vuelvan a ejecutar el programa.
SEMILLA = 42

# Generador de numeros aleatorios.
rng = np.random.default_rng(SEMILLA)

# Cantidad de estudiantes que vamos a simular.
CANTIDAD_ESTUDIANTES = 500

print("\n==========================================")
print("SMARTACADEMY")
print("COMPARACION DE ALGORITMOS")
print("==========================================")


# ================================================================
# 3. GENERACION DEL CONJUNTO DE DATOS
# ================================================================

# Generamos las horas de estudio de cada estudiante.
# Valores posibles: entre 0 y 20 horas.
horas_estudio = rng.uniform(
    0,
    20,
    CANTIDAD_ESTUDIANTES
)

# Generamos el porcentaje de asistencia.
# Valores posibles: entre 40% y 100%.
asistencia = rng.uniform(
    40,
    100,
    CANTIDAD_ESTUDIANTES
)

# Generamos el porcentaje de actividades entregadas.
actividades = rng.uniform(
    0,
    100,
    CANTIDAD_ESTUDIANTES
)

# Generamos el nivel de participacion.
# Valores posibles: entre 0 y 10.
participacion = rng.uniform(
    0,
    10,
    CANTIDAD_ESTUDIANTES
)

# ------------------------------------------------
# Construimos un indicador sintetico de rendimiento.
# ------------------------------------------------

# Cada variable se convierte a una escala de 0 a 1.
#
# Se asignan diferentes ponderaciones:
# Horas de estudio: 30%
# Asistencia: 25%
# Actividades: 30%
# Participacion: 15%

puntaje = (
    (horas_estudio / 20) * 0.30
    +
    (asistencia / 100) * 0.25
    +
    (actividades / 100) * 0.30
    +
    (participacion / 10) * 0.15
)

# Agregamos ruido aleatorio para simular variaciones
# que no pueden explicarse completamente con las variables.
ruido = rng.normal(
    loc=0,
    scale=0.12,
    size=CANTIDAD_ESTUDIANTES
)

# Calculamos el resultado final.
puntaje_final = puntaje + ruido

# Convertimos el resultado en una variable binaria.
#
# Si el puntaje es igual o superior a 0.58:
# El estudiante aprueba (1).
#
# En caso contrario:
# El estudiante no aprueba (0).
aprueba = (puntaje_final >= 0.58).astype(int)


# ================================================================
# 4. CONSTRUIR EL DATAFRAME
# ================================================================

# Creamos una tabla con todas las variables.
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

# Mostramos los primeros diez registros.
print(df.head(10))

# Mostramos la cantidad de registros.
print("\nCantidad de estudiantes:")
print(len(df))

# Mostramos cuantos aprobaron y cuantos no aprobaron.
print("\nDistribucion de resultados:")
print(df["aprueba"].value_counts().sort_index())


# ================================================================
# 5. SEPARAR VARIABLES PREDICTORAS Y OBJETIVO
# ================================================================

# X contiene las variables que utilizaran los algoritmos
# para realizar sus predicciones.
X = df[
    [
        "horas_estudio",
        "asistencia",
        "actividades",
        "participacion"
    ]
]

# y contiene el resultado que queremos predecir.
y = df["aprueba"]


# ================================================================
# 6. DIVIDIR LOS DATOS
# ================================================================

# Primera division:
# 80% para entrenamiento + validacion.
# 20% para prueba.

X_entrenamiento_validacion, X_prueba, \
y_entrenamiento_validacion, y_prueba = train_test_split(

    X,
    y,

    test_size=0.20,

    random_state=SEMILLA,

    # Mantiene una proporcion similar de las clases.
    stratify=y

)

# Segunda division:
# Del 80% restante:
# 75% sera entrenamiento.
# 25% sera validacion.
#
# Resultado total:
# 60% entrenamiento.
# 20% validacion.
# 20% prueba.

X_entrenamiento, X_validacion, \
y_entrenamiento, y_validacion = train_test_split(

    X_entrenamiento_validacion,
    y_entrenamiento_validacion,

    test_size=0.25,

    random_state=SEMILLA,

    stratify=y_entrenamiento_validacion

)

print("\n==========================================")
print("2. DISTRIBUCION DE LOS CONJUNTOS")
print("==========================================")

print("Entrenamiento:", len(X_entrenamiento))
print("Validacion:", len(X_validacion))
print("Prueba:", len(X_prueba))


# ================================================================
# 7. DEFINIR LOS ALGORITMOS
# ================================================================

# Creamos un diccionario para almacenar los modelos.
modelos = {

    # ------------------------------------------------------------
    # MODELO 1: ARBOL DE DECISION
    # ------------------------------------------------------------

    "Decision Tree": DecisionTreeClassifier(

        # Limita el crecimiento del arbol.
        # Configuracion final (aumentada): None = sin limite.
        # (Experimento C: se probaron 2, 3, 5, 7, 8, 9, 15 y None)
        max_depth=None,

        # Evita crear hojas con muy pocos registros.
        min_samples_leaf=4,

        # Semilla para reproducibilidad.
        random_state=SEMILLA
    ),


    # ------------------------------------------------------------
    # MODELO 2: RANDOM FOREST
    # ------------------------------------------------------------

    "Random Forest": RandomForestClassifier(

        # Cantidad de arboles que formaran el bosque.
        # Configuracion final (aumentada): 600 arboles.
        # (Experimento B: se probaron 50, 100, 200 y 500)
        n_estimators=600,

        # Limita la profundidad de los arboles.
        max_depth=None,

        # Cantidad minima de registros por hoja.
        min_samples_leaf=2,

        # Permite utilizar todos los nucleos disponibles.
        n_jobs=-1,

        random_state=SEMILLA
    ),


    # ------------------------------------------------------------
    # MODELO 3: K-NEAREST NEIGHBORS
    # ------------------------------------------------------------

    # KNN necesita datos en escalas comparables.
    # Por eso utilizamos Pipeline.
    #
    # Primero se normalizan los datos.
    # Despues se ejecuta KNN.
    #
    # El escalamiento se aprende durante el entrenamiento,
    # evitando utilizar informacion de validacion o prueba.

    "KNN": Pipeline([

        (
            "escalador",
            StandardScaler()
        ),

        (
            "clasificador",
            KNeighborsClassifier(

                # Cantidad de vecinos que se consultaran.
                # Configuracion final (aumentada): 25 vecinos.
                # (Experimento A: se probaron 3, 5, 7, 9 y 15)
                n_neighbors=25,

                # Los vecinos cercanos tienen mayor peso.
                weights="distance"
            )
        )

    ])

}


# ================================================================
# 8. ENTRENAMIENTO Y COMPARACION
# ================================================================

# Aqui almacenaremos los resultados de cada algoritmo.
resultados = []

# Aqui almacenaremos los modelos ya entrenados.
modelos_entrenados = {}

print("\n==========================================")
print("3. ENTRENAMIENTO DE LOS ALGORITMOS")
print("==========================================")

# Recorremos todos los modelos.
for nombre, modelo in modelos.items():

    print("\n--------------------------------------")
    print("Entrenando:", nombre)
    print("--------------------------------------")

    # Entrenamos el algoritmo utilizando exclusivamente
    # el conjunto de entrenamiento.
    modelo.fit(
        X_entrenamiento,
        y_entrenamiento
    )

    # Guardamos el modelo entrenado.
    modelos_entrenados[nombre] = modelo

    # Realizamos predicciones con los datos de validacion.
    predicciones = modelo.predict(X_validacion)

    # Calculamos las metricas de evaluacion.
    exactitud = accuracy_score(
        y_validacion,
        predicciones
    )

    precision = precision_score(
        y_validacion,
        predicciones,
        zero_division=0
    )

    recall = recall_score(
        y_validacion,
        predicciones,
        zero_division=0
    )

    f1 = f1_score(
        y_validacion,
        predicciones,
        zero_division=0
    )

    # Guardamos los resultados.
    resultados.append({

        "algoritmo": nombre,

        "exactitud": exactitud,

        "precision": precision,

        "recall": recall,

        "f1_score": f1

    })

    print("Exactitud:", f"{exactitud:.2%}")
    print("Precision:", f"{precision:.2%}")
    print("Recall:", f"{recall:.2%}")
    print("F1-score:", f"{f1:.2%}")


# ================================================================
# 9. TABLA COMPARATIVA
# ================================================================

# Convertimos los resultados en un DataFrame.
df_resultados = pd.DataFrame(resultados)

# Ordenamos los algoritmos por su F1-score.
# Utilizaremos esta metrica para seleccionar el modelo.
df_resultados = df_resultados.sort_values(
    by="f1_score",
    ascending=False
).reset_index(drop=True)

print("\n==========================================")
print("4. COMPARACION DE ALGORITMOS")
print("==========================================")

print(
    df_resultados.to_string(
        index=False,
        formatters={
            "exactitud": "{:.2%}".format,
            "precision": "{:.2%}".format,
            "recall": "{:.2%}".format,
            "f1_score": "{:.2%}".format
        }
    )
)


# ================================================================
# 10. SELECCIONAR EL MEJOR MODELO
# ================================================================

# Seleccionamos el primer registro de la tabla ordenada.
mejor_registro = df_resultados.iloc[0]

# Recuperamos el nombre del algoritmo.
mejor_nombre = mejor_registro["algoritmo"]

# Recuperamos su modelo entrenado.
mejor_modelo = modelos_entrenados[mejor_nombre]

print("\n==========================================")
print("5. MODELO SELECCIONADO")
print("==========================================")

print("Algoritmo:", mejor_nombre)

print(
    "F1-score de validacion:",
    f"{mejor_registro['f1_score']:.2%}"
)

print(
    "Criterio de seleccion: mayor F1-score"
)


# ================================================================
# 11. REENTRENAR CON ENTRENAMIENTO + VALIDACION
# ================================================================

# Una vez seleccionado el algoritmo, podemos aprovechar
# tanto los datos de entrenamiento como los de validacion.
#
# El conjunto de prueba permanece separado y sin utilizar.

X_entrenamiento_final = pd.concat(
    [
        X_entrenamiento,
        X_validacion
    ]
)

y_entrenamiento_final = pd.concat(
    [
        y_entrenamiento,
        y_validacion
    ]
)

# Creamos una copia independiente del modelo seleccionado.
modelo_final = clone(
    modelos[mejor_nombre]
)

# Entrenamos el modelo final con el 80% de los datos.
modelo_final.fit(
    X_entrenamiento_final,
    y_entrenamiento_final
)


# ================================================================
# 12. EVALUACION FINAL CON DATOS DE PRUEBA
# ================================================================

# El conjunto de prueba se utiliza hasta este momento.
predicciones_finales = modelo_final.predict(X_prueba)

# Calculamos las metricas finales.
accuracy_final = accuracy_score(
    y_prueba,
    predicciones_finales
)

precision_final = precision_score(
    y_prueba,
    predicciones_finales,
    zero_division=0
)

recall_final = recall_score(
    y_prueba,
    predicciones_finales,
    zero_division=0
)

f1_final = f1_score(
    y_prueba,
    predicciones_finales,
    zero_division=0
)

print("\n==========================================")
print("6. EVALUACION FINAL")
print("==========================================")

print("Algoritmo:", mejor_nombre)

print("Exactitud:", f"{accuracy_final:.2%}")

print("Precision:", f"{precision_final:.2%}")

print("Recall:", f"{recall_final:.2%}")

print("F1-score:", f"{f1_final:.2%}")


# ================================================================
# 13. REPORTE DE CLASIFICACION
# ================================================================

print("\n==========================================")
print("7. REPORTE DE CLASIFICACION")
print("==========================================")

print(

    classification_report(

        y_prueba,

        predicciones_finales,

        labels=[0, 1],

        target_names=[
            "No aprueba",
            "Aprueba"
        ],

        zero_division=0

    )

)


# ================================================================
# 14. MATRIZ DE CONFUSION
# ================================================================

matriz = confusion_matrix(
    y_prueba,
    predicciones_finales,
    labels=[0, 1]
)

print("\n==========================================")
print("8. MATRIZ DE CONFUSION")
print("==========================================")

print(matriz)


# ================================================================
# 15. VALIDACION CRUZADA DEL MODELO SELECCIONADO
# ================================================================

# Utilizamos los datos de entrenamiento y validacion.
# El conjunto de prueba sigue sin participar.

resultados_cv = cross_val_score(

    clone(modelos[mejor_nombre]),

    X_entrenamiento_final,

    y_entrenamiento_final,

    cv=5,

    scoring="f1",

    n_jobs=-1

)

print("\n==========================================")
print("9. VALIDACION CRUZADA")
print("==========================================")

print("Resultados por particion:")

print(resultados_cv)

print(
    "Promedio F1:",
    f"{resultados_cv.mean():.2%}"
)

print(
    "Desviacion estandar:",
    f"{resultados_cv.std():.2%}"
)


# ================================================================
# 16. GRAFICA COMPARATIVA DE METRICAS
# ================================================================

# Definimos los nombres de las metricas.
metricas = [
    "exactitud",
    "precision",
    "recall",
    "f1_score"
]

# Configuramos el tamaño de la figura.
plt.figure(figsize=(12, 6))

# Cada algoritmo tendra una barra por metrica.
ancho = 0.22

# Posiciones de los algoritmos.
posiciones = np.arange(
    len(df_resultados)
)

# Dibujamos las barras de cada metrica.
for i, metrica in enumerate(metricas):

    desplazamiento = (
        i - 1.5
    ) * ancho

    plt.bar(

        posiciones + desplazamiento,

        df_resultados[metrica],

        width=ancho,

        label=metrica.replace("_", " ").title()

    )

# Configuramos el eje X.
plt.xticks(
    posiciones,
    df_resultados["algoritmo"]
)

# Configuramos el eje Y.
plt.ylim(0, 1.05)

plt.ylabel("Resultado")

plt.xlabel("Algoritmo")

plt.title(
    "Comparacion de algoritmos de clasificacion"
)

plt.legend()

plt.grid(
    axis="y",
    alpha=0.3
)

plt.tight_layout()

# Guardamos la grafica.
plt.savefig(
    "p05_comparacion_algoritmos.png",
    dpi=300
)

plt.show()


# ================================================================
# 17. GRAFICA DE LA MATRIZ DE CONFUSION
# ================================================================

# Creamos el objeto que representa la matriz.
visualizacion = ConfusionMatrixDisplay(

    confusion_matrix=matriz,

    display_labels=[
        "No aprueba",
        "Aprueba"
    ]

)

# Dibujamos la matriz.
visualizacion.plot(
    cmap="Blues",
    values_format="d"
)

plt.title(
    "Matriz de confusion - " + mejor_nombre
)

plt.tight_layout()

# Guardamos la imagen.
plt.savefig(
    "p05_matriz_confusion.png",
    dpi=300
)

plt.show()


# ================================================================
# 18. GUARDAR LOS RESULTADOS
# ================================================================

# Exportamos la tabla comparativa a CSV.
df_resultados.to_csv(

    "p05_resultados_comparacion.csv",

    index=False,

    encoding="utf-8"

)

print("\n==========================================")
print("10. ARCHIVOS GENERADOS")
print("==========================================")

print("p05_comparacion_algoritmos.png")

print("p05_matriz_confusion.png")

print("p05_resultados_comparacion.csv")


# ================================================================
# 19. CONCLUSION DEL SISTEMA
# ================================================================

print("\n==========================================")
print("CONCLUSION")
print("==========================================")

print(
    "El algoritmo seleccionado fue:",
    mejor_nombre
)

print(
    "Su F1-score final fue:",
    f"{f1_final:.2%}"
)

print(
    "\nSmartAcademy ha completado la comparacion"
    " de algoritmos de clasificacion."
)

print(
    "Recuerda: el mejor algoritmo depende de los datos,"
    " del problema y de la metrica que se desea optimizar."
)

print("\nPROCESO FINALIZADO.")


#Actividad de modificación
#realizar tres experimentos:

#- Experimento A: modificar n_neighbors de KNN a 3, 5, 7, 9 y 15.
#- Experimento B: modificar n_estimators de Random Forest a 50, 100, 200 y 500.
#- Experimento C: modificar max_depth de Decision Tree a 2, 3, 5, 8 y None.
#Deberán registrar los resultados y explicar cómo cambió el rendimiento.

#Importante: los resultados exactos dependerán de la configuración de los algoritmos. 
#No deben asumir que Random Forest o KNN siempre serán superiores.
#dar sus propias conclusiones con base en lo que arrojen los algoritmos.


# ================================================================
# 20. ACTIVIDAD DE MODIFICACION: EXPERIMENTOS
# ================================================================
#
# Para cada experimento se cambia UN solo hiperparametro y los
# demas algoritmos se dejan con sus valores originales:
#
#   Decision Tree -> max_depth = 15
#   Random Forest -> n_estimators = 200
#   KNN           -> n_neighbors = 7
#
# Todos los modelos se entrenan con el conjunto de entrenamiento
# y se evaluan con el conjunto de validacion (la prueba no se usa).

def crear_decision_tree(profundidad):
    return DecisionTreeClassifier(
        max_depth=profundidad,
        min_samples_leaf=4,
        random_state=SEMILLA
    )


def crear_random_forest(arboles):
    return RandomForestClassifier(
        n_estimators=arboles,
        max_depth=None,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=SEMILLA
    )


def crear_knn(vecinos):
    return Pipeline([
        ("escalador", StandardScaler()),
        ("clasificador", KNeighborsClassifier(
            n_neighbors=vecinos,
            weights="distance"
        ))
    ])


def evaluar(modelo):
    # Entrena el modelo y devuelve sus metricas de validacion.
    modelo.fit(X_entrenamiento, y_entrenamiento)
    pred = modelo.predict(X_validacion)
    return {
        "exactitud": accuracy_score(y_validacion, pred),
        "precision": precision_score(y_validacion, pred, zero_division=0),
        "recall": recall_score(y_validacion, pred, zero_division=0),
        "f1_score": f1_score(y_validacion, pred, zero_division=0)
    }


def mostrar_tabla(tabla):
    print(
        tabla.to_string(
            index=False,
            formatters={
                "exactitud": "{:.2%}".format,
                "precision": "{:.2%}".format,
                "recall": "{:.2%}".format,
                "f1_score": "{:.2%}".format
            }
        )
    )


# Aqui se registran todos los resultados de los experimentos.
registro = []

experimentos = [
    ("A", "KNN", "n_neighbors", [3, 5, 7, 9, 15], crear_knn),
    ("B", "Random Forest", "n_estimators", [50, 100, 200, 500], crear_random_forest),
    ("C", "Decision Tree", "max_depth", [2, 3, 5, 7, 8, 9, 15, None], crear_decision_tree),
]

for letra, algoritmo, parametro, valores, crear in experimentos:

    print("\n==========================================")
    print(f"EXPERIMENTO {letra}: {parametro} de {algoritmo}")
    print("==========================================")

    filas = []

    for valor in valores:
        metricas_exp = evaluar(crear(valor))
        fila = {"valor": str(valor), **metricas_exp}
        filas.append(fila)
        registro.append({
            "experimento": letra,
            "algoritmo": algoritmo,
            "parametro": parametro,
            **fila
        })

    tabla = pd.DataFrame(filas)
    mostrar_tabla(tabla)

    mejor_fila = tabla.loc[tabla["f1_score"].idxmax()]
    print(
        f"Mejor valor de {parametro}: {mejor_fila['valor']}"
        f" (F1 = {mejor_fila['f1_score']:.2%})"
    )

    # Grafica de como cambia el rendimiento.
    plt.figure(figsize=(8, 5))
    for metrica in ["exactitud", "precision", "recall", "f1_score"]:
        plt.plot(
            tabla["valor"],
            tabla[metrica],
            marker="o",
            label=metrica.replace("_", " ").title()
        )
    plt.ylim(0.5, 1.0)
    plt.xlabel(parametro)
    plt.ylabel("Resultado")
    plt.title(f"Experimento {letra}: {parametro} de {algoritmo}")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"p05_experimento_{letra}.png", dpi=300)
    plt.show()


# ================================================================
# 21. CONFIGURACION MAXIMA Y CONFIGURACION AUMENTADA
# ================================================================
#
# Maxima:     KNN = 15,  Random Forest = 500, Decision Tree = None
# Aumentada:  KNN = 25,  Random Forest = 600, Decision Tree = None
#
# En cada configuracion se selecciona el mejor modelo por F1,
# se reentrena con entrenamiento + validacion y se evalua
# con el conjunto de prueba.

configuraciones = {
    "Maxima": {"KNN": 15, "Random Forest": 500, "Decision Tree": None},
    "Aumentada": {"KNN": 25, "Random Forest": 600, "Decision Tree": None},
}

constructores = {
    "KNN": crear_knn,
    "Random Forest": crear_random_forest,
    "Decision Tree": crear_decision_tree,
}

parametros = {
    "KNN": "n_neighbors",
    "Random Forest": "n_estimators",
    "Decision Tree": "max_depth",
}

for nombre_config, valores_config in configuraciones.items():

    print("\n==========================================")
    print(f"CONFIGURACION {nombre_config.upper()}")
    print("==========================================")

    filas = []

    for algoritmo, valor in valores_config.items():
        metricas_cfg = evaluar(constructores[algoritmo](valor))
        filas.append({"algoritmo": algoritmo, **metricas_cfg})
        registro.append({
            "experimento": nombre_config,
            "algoritmo": algoritmo,
            "parametro": parametros[algoritmo],
            "valor": str(valor),
            **metricas_cfg
        })

    tabla = pd.DataFrame(filas).sort_values(
        by="f1_score",
        ascending=False,
        kind="stable"
    ).reset_index(drop=True)

    mostrar_tabla(tabla)

    seleccionado = tabla.iloc[0]["algoritmo"]

    modelo_cfg = constructores[seleccionado](valores_config[seleccionado])
    modelo_cfg.fit(X_entrenamiento_final, y_entrenamiento_final)
    pred_cfg = modelo_cfg.predict(X_prueba)

    print("\nModelo seleccionado:", seleccionado)
    print("Evaluacion con datos de prueba:")
    print("Exactitud:", f"{accuracy_score(y_prueba, pred_cfg):.2%}")
    print("Precision:", f"{precision_score(y_prueba, pred_cfg, zero_division=0):.2%}")
    print("Recall:", f"{recall_score(y_prueba, pred_cfg, zero_division=0):.2%}")
    print("F1-score:", f"{f1_score(y_prueba, pred_cfg, zero_division=0):.2%}")


# Guardamos el registro completo de los experimentos.
pd.DataFrame(registro).to_csv(
    "p05_registro_experimentos.csv",
    index=False,
    encoding="utf-8"
)

print("\nRegistro guardado en: p05_registro_experimentos.csv")


# ================================================================
# 22. RESULTADOS Y CONCLUSIONES DE LOS EXPERIMENTOS
# ================================================================
#
# (Metricas sobre el conjunto de validacion, 100 estudiantes)
#
# EXPERIMENTO A - KNN (n_neighbors)
#   k=3  -> Exactitud 73% | F1 70.33%
#   k=5  -> Exactitud 77% | F1 74.73%
#   k=7  -> Exactitud 77% | F1 74.73%
#   k=9  -> Exactitud 78% | F1 76.09%   <- mejor
#   k=15 -> Exactitud 74% | F1 72.34%
#   Con pocos vecinos el modelo es sensible al ruido; con muchos
#   promedia demasiado y pierde detalle. El mejor punto fue k=9.
#
# EXPERIMENTO B - RANDOM FOREST (n_estimators)
#   50  -> Exactitud 80% | F1 76.74%   <- mejor
#   100 -> Exactitud 78% | F1 74.42%
#   200 -> Exactitud 77% | F1 74.16%
#   500 -> Exactitud 77% | F1 73.56%
#   Mas arboles hacen al bosque mas estable pero no mas preciso;
#   desde 50 arboles ya no se gana rendimiento y si tiempo de computo.
#
# EXPERIMENTO C - DECISION TREE (max_depth)
#   2    -> Exactitud 74% | F1 69.05%
#   3    -> Exactitud 72% | F1 70.21%   <- mejor
#   5    -> Exactitud 74% | F1 69.05%
#   7, 8, 9, 15, None -> Exactitud 73% | F1 68.24%
#   Con min_samples_leaf=4 el arbol deja de crecer solo en
#   profundidad 7, por eso los valores mayores dan lo mismo.
#   Mas profundidad = mas memorizacion, no mejor generalizacion.
#
# CONFIGURACION MAXIMA (KNN 15, RF 500, DT None)
#   Seleccionado: Random Forest (F1 validacion 73.56%)
#   Prueba: Exactitud 76% | F1 72.09%
#
# CONFIGURACION AUMENTADA (KNN 25, RF 600, DT None)
#   KNN 25 -> F1 76.29% (recall 84.09%) | RF 600 -> F1 75.00% | DT -> 68.24%
#   Seleccionado: KNN (F1 validacion 76.29%)
#   Prueba: Exactitud 75% | F1 70.59%
#
# CONCLUSIONES
# 1. Ningun algoritmo fue siempre el mejor: el seleccionado cambio
#    entre KNN y Random Forest segun los hiperparametros.
# 2. Aumentar un hiperparametro no garantiza mejor rendimiento.
# 3. Decision Tree fue el mas debil en todos los casos.
# 4. El modelo que gano en validacion (KNN 25) no fue el que mejor
#    generalizo en prueba (Random Forest 500), por eso conviene
#    confirmar con validacion cruzada.
# 5. Random Forest fue el algoritmo mas estable para predecir datos
#    que el modelo nunca ha visto.