"""ETAPA 4 · Preparación de los tensores para la CNN 1D.

  1. pandas lee el Parquet de etl_atuendos.py y revisa columnas y cantidad.
  2. Cada look se vuelve la secuencia [canales, 5 posiciones] con secuencia_de() de servidor/red_convolucional.py:
     la MISMA función que usa la app al predecir, así no hay diferencias entre lo entrenado y lo que llega.
  3. División 70 / 15 / 15 POR PERSONA (GroupShuffleSplit): los 5 looks de una persona
     quedan todos del mismo lado, para que la prueba mida personas que la red nunca vio.
  4. Normalización con la media y la desviación SOLO del entrenamiento (por canal); se guardan para la app.
"""

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from comun import ARCHIVO_TENSORES, SEMILLA, TOTAL_REGISTROS, leer_parquet, titulo
from servidor.aprendizaje import PESOS_DE_RESPUESTA, caracteristicas_de, pesos_iniciales, puntuar
from servidor.red_convolucional import CANALES, ORDEN, secuencia_de

CAMPOS = ["color_principal", "nivel_abrigo", "estampado", "estilo"]
COLUMNAS = (["id_registro", "id_persona", *PESOS_DE_RESPUESTA, "me_gusta"]
            + [f"{p}_{c}" for p in ORDEN for c in ("color", "abrigo", "estampado", "estilo")])


def cargar():
    titulo("1. LEYENDO EL PARQUET")
    df = leer_parquet()  # ya viene ordenado por id_registro: todo es reproducible
    faltantes = set(COLUMNAS) - set(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas: {faltantes}")
    if len(df) != TOTAL_REGISTROS:
        raise ValueError(f"Se esperaban {TOTAL_REGISTROS:,} registros y hay {len(df):,}")
    datos = df[COLUMNAS]
    print(f"Registros: {len(datos):,} · personas: {datos['id_persona'].nunique():,}")
    return datos


def look_de(fila) -> list[dict]:
    look = []
    for posicion in ORDEN:
        if isinstance(fila[f"{posicion}_color"], str):
            look.append({"categoria": posicion, "color_principal": fila[f"{posicion}_color"],
                         "nivel_abrigo": int(fila[f"{posicion}_abrigo"]), "estampado": fila[f"{posicion}_estampado"],
                         "estilo": fila[f"{posicion}_estilo"]})
    return look


def construir_tensores(datos):
    titulo("2. DE CADA LOOK A SU SECUENCIA")
    secuencias, reglas = [], []
    for fila in datos.to_dict("records"):
        look, cuestionario = look_de(fila), {p: fila[p] for p in PESOS_DE_RESPUESTA}
        secuencias.append(secuencia_de(look, cuestionario))
        # Lo que hace hoy la app con una persona sin votos: el perceptrón con los pesos del cuestionario.
        reglas.append(puntuar(pesos_iniciales(cuestionario), caracteristicas_de(look)))
    X = np.stack(secuencias)
    y = datos["me_gusta"].to_numpy(dtype=np.float32)
    grupos = datos["id_persona"].to_numpy()
    print(f"X: {X.shape} = [looks, {len(CANALES)} canales, {len(ORDEN)} posiciones] · y: {y.shape}")
    print("Posiciones:", " → ".join(ORDEN))
    return X, y, grupos, np.array(reglas, dtype=np.float32)


def dividir(X, y, grupos):
    titulo("3. DIVISIÓN POR PERSONA 70 / 15 / 15")
    resto, prueba = next(GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=SEMILLA).split(X, y, grupos))
    entrenamiento_rel, validacion_rel = next(GroupShuffleSplit(n_splits=1, test_size=0.15 / 0.85, random_state=SEMILLA)
                                             .split(X[resto], y[resto], grupos[resto]))
    indices = {"entrenamiento": resto[entrenamiento_rel], "validacion": resto[validacion_rel], "prueba": prueba}
    personas = {nombre: set(grupos[i]) for nombre, i in indices.items()}
    assert not personas["entrenamiento"] & personas["validacion"], "Personas repetidas entre entrenamiento y validación"
    assert not personas["entrenamiento"] & personas["prueba"], "Personas repetidas entre entrenamiento y prueba"
    assert not personas["validacion"] & personas["prueba"], "Personas repetidas entre validación y prueba"
    for nombre, i in indices.items():
        print(f"{nombre:14} {len(i):6,} looks · {len(personas[nombre]):5,} personas · {y[i].mean():.1%} corazones")
    return indices


def main():
    titulo("SECRETS OF STYLE · ETAPA 4 · PREPARACIÓN DE TENSORES PARA LA CNN 1D")
    datos = cargar()
    X, y, grupos, reglas = construir_tensores(datos)
    indices = dividir(X, y, grupos)

    titulo("4. NORMALIZACIÓN CON EL ENTRENAMIENTO")
    entrenamiento = X[indices["entrenamiento"]]
    media = entrenamiento.mean(axis=(0, 2), keepdims=True)[0]  # una por canal: [canales, 1]
    desviacion = entrenamiento.std(axis=(0, 2), keepdims=True)[0]
    desviacion = np.where(desviacion == 0, 1.0, desviacion).astype(np.float32)
    print("Media y desviación por canal calculadas solo con entrenamiento (se aplican en entrenamiento_cnn.py y en la app)")

    np.savez_compressed(
        ARCHIVO_TENSORES,
        **{f"X_{n}": X[i] for n, i in indices.items()},
        **{f"y_{n}": y[i] for n, i in indices.items()},
        **{f"grupos_{n}": grupos[i].astype(str) for n, i in indices.items()},
        **{f"regla_{n}": reglas[i] for n, i in indices.items()},
        media=media.astype(np.float32), desviacion=desviacion, canales=np.array(CANALES),
    )
    print(f"\nGuardado: {ARCHIVO_TENSORES} ({ARCHIVO_TENSORES.stat().st_size / 1e6:.1f} MB)")
    titulo("ETAPA 4 FINALIZADA")


if __name__ == "__main__":
    main()
