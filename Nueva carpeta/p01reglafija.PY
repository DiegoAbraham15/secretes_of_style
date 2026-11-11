
# ============================================================
# PARTE B: TOMAR UNA DECISION MEDIANTE UNA REGLA FIJA
# ============================================================

# La siguiente informacion es ficticia.
# Las horas corresponden al tiempo de estudio semanal.

#Ahora resolveremos un problema diferente: 
#clasificar el resultado académico de un estudiante a partir de sus horas de estudio.

#Para comprender primero la diferencia conceptual, 
#utilizaremos una regla fija. Posteriormente, en la práctica de KNN,
#sustituiremos esa regla por un modelo que aprende de ejemplos.

estudiantes = [
    {"nombre": "Ana", "horas_estudio": 8},
    {"nombre": "Luis", "horas_estudio": 3},
    {"nombre": "Maria", "horas_estudio": 10},
    {"nombre": "Carlos", "horas_estudio": 5}
]


# ------------------------------------------------------------
# DEFINIR UNA REGLA MANUAL
# ------------------------------------------------------------
# Esta regla es solamente un ejemplo didactico.
# No representa una relacion cientifica entre horas y aprobacion.

def predecir_con_regla(horas):

    if horas >= 6:
        return "Probablemente aprueba"

    return "Necesita apoyo"


# ------------------------------------------------------------
# APLICAR LA REGLA A CADA ESTUDIANTE
# ------------------------------------------------------------
print("\n=== RESULTADO DE LA REGLA FIJA ===")

for estudiante in estudiantes:

    horas = estudiante["horas_estudio"]

    resultado = predecir_con_regla(horas)

    print(
        estudiante["nombre"],
        "| Horas:", horas,
        "| Resultado:", resultado
    )


# ------------------------------------------------------------
# PROBAR CON UN CASO NUEVO
# ------------------------------------------------------------
horas_nuevo_estudiante = 7

resultado = predecir_con_regla(horas_nuevo_estudiante)

print("\n=== NUEVO CASO ===")
print("Horas de estudio:", horas_nuevo_estudiante)
print("Resultado:", resultado)
