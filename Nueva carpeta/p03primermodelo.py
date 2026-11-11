
# ============================================================
# FUNDAMENTOS DE INTELIGENCIA ARTIFICIAL
# PRACTICA 03: PRIMER MODELO DE MACHINE LEARNING
# COMPARACION: REGLAS FIJAS VS APRENDIZAJE AUTOMATICO
# ============================================================

# OBJETIVO:
# Comprender como se entrena un modelo de clasificacion y
# comparar sus predicciones con un sistema de reglas manuales.
#
# IMPORTANTE:
# Los datos son ficticios y sirven exclusivamente para aprender.
# Este ejemplo NO debe utilizarse para tomar decisiones reales
# sobre estudiantes.

# Etapas del aprendizaje automático
# 1. Datos históricos
# Horas de estudio, asistencia y actividades
# 2. Separación de datos
# Entrenamiento y prueba
# 3. Entrenamiento
# El árbol identifica patrones en los ejemplos
# 4. Predicción
# El modelo clasifica casos que no usó para entrenar
# 5. Evaluación
# Comparamos predicciones con resultados reales


# ------------------------------------------------------------
# 1. IMPORTAR LAS BIBLIOTECAS
# ------------------------------------------------------------

# pandas permite organizar y analizar datos en tablas.
import pandas as pd

# train_test_split divide los datos en entrenamiento y prueba.
from sklearn.model_selection import train_test_split

# DecisionTreeClassifier crea un modelo de clasificacion
# basado en un arbol de decisiones que aprende de los datos.
from sklearn.tree import DecisionTreeClassifier

# accuracy_score calcula la proporcion de predicciones correctas.
from sklearn.metrics import accuracy_score

# classification_report muestra precision, recall y F1-score.
from sklearn.metrics import classification_report

# confusion_matrix permite observar aciertos y errores.
from sklearn.metrics import confusion_matrix


# ------------------------------------------------------------
# 2. CREAR LOS DATOS DE EJEMPLO
# ------------------------------------------------------------

# Cada diccionario representa un estudiante ficticio.
#
# horas_estudio:
# Horas dedicadas al estudio durante una semana.
#
# asistencia:
# Porcentaje de asistencia del estudiante.
#
# actividades_entregadas:
# Porcentaje de actividades que entrego.
#
# aprueba:
# 1 significa que aprobo.
# 0 significa que no aprobo.

datos = {
    "horas_estudio": [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
        2, 4, 6, 8, 10, 3, 5, 7, 9, 6
    ],

    "asistencia": [
        40, 50, 55, 60, 65, 70, 75, 80, 85, 90,
        45, 55, 60, 65, 70, 75, 80, 85, 90, 95,
        50, 60, 70, 80, 95, 55, 75, 85, 90, 68
    ],

    "actividades_entregadas": [
        30, 40, 45, 55, 60, 65, 70, 80, 90, 95,
        20, 35, 50, 60, 65, 70, 75, 85, 95, 100,
        40, 55, 75, 85, 100, 45, 70, 80, 90, 60
    ],

    "aprueba": [
        0, 0, 0, 0, 1, 1, 1, 1, 1, 1,
        0, 0, 0, 1, 1, 1, 1, 1, 1, 1,
        0, 0, 1, 1, 1, 0, 1, 1, 1, 0
    ]
}

# Convertimos el diccionario en una tabla de pandas.
df = pd.DataFrame(datos)

# Mostramos los datos para verificar que se crearon.
print("\n========================================")
print("1. DATOS DE LOS ESTUDIANTES")
print("========================================")

print(df.to_string(index=False))


# ------------------------------------------------------------
# 3. ANALIZAR LOS DATOS
# ------------------------------------------------------------

# shape devuelve la cantidad de filas y columnas.
print("\nCantidad de filas y columnas:")
print(df.shape)

# isnull().sum() cuenta los valores faltantes por columna.
print("\nValores faltantes:")
print(df.isnull().sum())

# value_counts() cuenta cuantos casos hay de cada clase.
print("\nDistribucion de la variable objetivo:")
print(df["aprueba"].value_counts().sort_index())

# En este ejemplo los datos ya estan preparados.
# En proyectos reales debemos revisar tambien duplicados,
# tipos de datos, rangos validos y posibles errores.


# ------------------------------------------------------------
# 4. DEFINIR LAS VARIABLES DE ENTRADA Y LA VARIABLE OBJETIVO
# ------------------------------------------------------------

# X contiene las caracteristicas que el modelo utilizara
# para aprender patrones.
#
# En este caso:
# - horas_estudio
# - asistencia
# - actividades_entregadas

X = df[
    [
        "horas_estudio",
        "asistencia",
        "actividades_entregadas"
    ]
]

# y contiene el resultado que queremos aprender a predecir.
#
# 1 = aprueba
# 0 = no aprueba

y = df["aprueba"]

print("\nCaracteristicas utilizadas:")
print(X.head())

print("\nResultados que queremos predecir:")
print(y.head())


# ------------------------------------------------------------
# 5. DIVIDIR LOS DATOS EN ENTRENAMIENTO Y PRUEBA
# ------------------------------------------------------------

# El modelo necesita ejemplos para aprender.
# Tambien necesitamos reservar ejemplos para evaluarlo.
#
# test_size=0.30 significa que reservamos el 30 % para prueba.
# El 70 % restante se utiliza para entrenamiento.
#
# random_state=42 permite reproducir la misma division.
#
# stratify=y procura conservar la proporcion de las clases
# en ambos conjuntos.

X_entrenamiento, X_prueba, y_entrenamiento, y_prueba = (
    train_test_split(
        X,
        y,
        test_size=0.30,
        random_state=42,
        stratify=y
    )
)

print("\n========================================")
print("2. DIVISION DE LOS DATOS")
print("========================================")

print("Registros para entrenar:", len(X_entrenamiento))
print("Registros para probar:", len(X_prueba))


# ------------------------------------------------------------
# 6. CREAR EL SISTEMA BASADO EN REGLAS FIJAS
# ------------------------------------------------------------

# Este sistema NO aprende de los datos.
# Una persona establece las condiciones manualmente.
#
# Regla de ejemplo:
# El estudiante aprueba si cumple simultaneamente:
# - al menos 5 horas de estudio;
# - al menos 70 % de asistencia;
# - al menos 65 % de actividades entregadas.
#
# Estas condiciones son inventadas para fines didacticos.
# No representan criterios institucionales reales.

def predecir_con_reglas(estudiante):

    # Leemos los valores del estudiante.
    horas = estudiante["horas_estudio"]
    asistencia = estudiante["asistencia"]
    actividades = estudiante["actividades_entregadas"]

    # Evaluamos todas las condiciones.
    if (
        horas >= 5
        and asistencia >= 70
        and actividades >= 65
    ):
        return 1

    # Si no cumple todas las condiciones, devolvemos 0.
    return 0


# ------------------------------------------------------------
# 7. CREAR Y ENTRENAR EL MODELO DE MACHINE LEARNING
# ------------------------------------------------------------

# Creamos un arbol de decisiones.
#
# max_depth=3 limita la profundidad del arbol para que el
# ejemplo sea mas sencillo de interpretar.
#
# random_state=42 permite reproducir el resultado.

modelo = DecisionTreeClassifier(
    max_depth=3,
    random_state=42
)

# fit() es el metodo que entrena el modelo.
#
# El algoritmo analiza las caracteristicas X_entrenamiento
# y sus resultados conocidos y_entrenamiento.
#
# A partir de estos ejemplos construye reglas internas
# que ayudan a clasificar nuevos casos.

modelo.fit(
    X_entrenamiento,
    y_entrenamiento
)

print("\n========================================")
print("3. MODELO ENTRENADO")
print("========================================")

print("El arbol de decisiones termino su entrenamiento.")


# ------------------------------------------------------------
# 8. GENERAR PREDICCIONES CON AMBOS SISTEMAS
# ------------------------------------------------------------

# El modelo predice los resultados del conjunto de prueba.
predicciones_ml = modelo.predict(X_prueba)

# Aplicamos las reglas manuales a los mismos estudiantes.
predicciones_reglas = X_prueba.apply(
    predecir_con_reglas,
    axis=1
)

# Guardamos los resultados reales y las dos predicciones
# en una sola tabla para compararlos facilmente.

comparacion = X_prueba.copy()

comparacion["resultado_real"] = y_prueba
comparacion["prediccion_reglas"] = predicciones_reglas
comparacion["prediccion_ml"] = predicciones_ml

# Ordenamos el indice para facilitar la lectura.
comparacion = comparacion.sort_index()

print("\n========================================")
print("4. COMPARACION DE PREDICCIONES")
print("========================================")

print(comparacion.to_string())


# ------------------------------------------------------------
# 9. EVALUAR EL MODELO DE MACHINE LEARNING
# ------------------------------------------------------------

# accuracy_score compara las predicciones con los resultados
# reales y calcula la proporcion de aciertos.

exactitud_ml = accuracy_score(
    y_prueba,
    predicciones_ml
)

# Evaluamos tambien el sistema de reglas.
exactitud_reglas = accuracy_score(
    y_prueba,
    predicciones_reglas
)

print("\n========================================")
print("5. EXACTITUD DE LOS SISTEMAS")
print("========================================")

print(f"Exactitud de reglas fijas: {exactitud_reglas:.2%}")
print(f"Exactitud de Machine Learning: {exactitud_ml:.2%}")


# ------------------------------------------------------------
# 10. ANALIZAR PRECISION, RECALL Y F1-SCORE
# ------------------------------------------------------------

# Precision:
# De los casos que el sistema predijo como positivos,
# cuantos realmente eran positivos.
#
# Recall:
# De todos los casos positivos reales, cuantos detecto.
#
# F1-score:
# Combina precision y recall en una sola medida.
#
# support:
# Cantidad de ejemplos reales de cada clase evaluada.

print("\n========================================")
print("6. REPORTE DE CLASIFICACION")
print("========================================")

print(
    classification_report(
        y_prueba,
        predicciones_ml,
        labels=[0, 1],
        target_names=["No aprueba", "Aprueba"],
        zero_division=0
    )
)


# ------------------------------------------------------------
# 11. MOSTRAR LA MATRIZ DE CONFUSION
# ------------------------------------------------------------

# La matriz permite contar aciertos y errores.
#
# Filas: resultados reales.
# Columnas: resultados predichos.
#
# Orden de las clases: 0 y 1.
#
# [[verdaderos negativos, falsos positivos],
#  [falsos negativos, verdaderos positivos]]

matriz = confusion_matrix(
    y_prueba,
    predicciones_ml,
    labels=[0, 1]
)

print("\n========================================")
print("7. MATRIZ DE CONFUSION")
print("========================================")

print(matriz)


# ------------------------------------------------------------
# 12. PROBAR UN ESTUDIANTE NUEVO
# ------------------------------------------------------------

# Creamos un registro ficticio que no pertenece a la tabla.
# Asi observamos como se realiza una prediccion individual.

nuevo_estudiante = pd.DataFrame({
    "horas_estudio": [6],
    "asistencia": [80],
    "actividades_entregadas": [75]
})

# Prediccion del modelo entrenado.
resultado_ml = modelo.predict(nuevo_estudiante)[0]

# Prediccion de las reglas fijas.
resultado_reglas = predecir_con_reglas(
    nuevo_estudiante.iloc[0]
)

# Convertimos el numero en un mensaje comprensible.
def interpretar_resultado(resultado):

    if resultado == 1:
        return "Aprueba"

    return "No aprueba"


print("\n========================================")
print("8. PREDICCION PARA UN NUEVO ESTUDIANTE")
print("========================================")

print("Horas de estudio:", nuevo_estudiante.iloc[0]["horas_estudio"])
print("Asistencia:", nuevo_estudiante.iloc[0]["asistencia"])
print(
    "Actividades entregadas:",
    nuevo_estudiante.iloc[0]["actividades_entregadas"]
)

print(
    "Resultado con reglas:",
    interpretar_resultado(resultado_reglas)
)

print(
    "Resultado con Machine Learning:",
    interpretar_resultado(resultado_ml)
)


# ------------------------------------------------------------
# 13. CONCLUSIONES AUTOMATICAS
# ------------------------------------------------------------

print("\n========================================")
print("9. CONCLUSIONES")
print("========================================")

print(
    "El sistema de reglas utiliza condiciones definidas "
    "manualmente."
)

print(
    "El modelo de Machine Learning utiliza patrones "
    "aprendidos durante el entrenamiento."
)

print(
    "Una mayor exactitud en esta prueba no garantiza que "
    "un sistema funcione mejor con datos futuros."
)

print(
    "Para obtener conclusiones confiables necesitamos "
    "mas datos representativos y una evaluacion rigurosa."
)

print("\nPractica terminada correctamente.")


# Instrucción	            Función
# X = df[[...]]	            Selecciona las variables de entrada.
# y = df["aprueba"]	        Selecciona la respuesta que queremos aprender.
# train_test_split()	    Separa los datos para entrenamiento y evaluación.
# DecisionTreeClassifier()	Crea el clasificador.
# modelo.fit(X, y)	        Entrena el modelo con ejemplos conocidos.
# modelo.predict(X)	        Genera predicciones para nuevos ejemplos.
# accuracy_score()	        Calcula la proporción de predicciones correctas.
# confusion_matrix()	    Cuenta los tipos de aciertos y errores.

# Punto fundamental: fit() entrena; predict() predice. Son operaciones diferentes.


