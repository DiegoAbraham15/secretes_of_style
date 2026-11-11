"""
La pregunta: ¿el perceptrón (servidor/aprendizaje.py) adivina qué atuendos le gustan a la persona mejor que una
regla fija? Se comparan tres sistemas sobre los mismos votos de prueba:
  - Siempre "no le gusta": la referencia. Como casi todos los votos son "no", ya saca una exactitud alta;
    por eso importan más la precisión y el recall de "le gusta".
  - Regla fija: los pesos que salen del cuestionario de estilo (pesos_iniciales), sin aprender de los votos.
  - Perceptrón: parte de esos mismos pesos y aprende de los votos de entrenamiento (entrenar).

Pasos:
  1. Datos: los votos que pasan la limpieza (limpieza_de_datos.py). X = las 13 características, y = me_gusta.
  2. División: 70 % para entrenar y 30 % para probar, conservando la proporción de corazones en ambos
     (como stratify=y). Con random_state=42 sale siempre la misma división.
  3. Entrenar el perceptrón solo con la parte de entrenamiento.
  4. Predecir los votos de prueba. La app no usa el signo del puntaje: ORDENA los candidatos y muestra los de
     arriba (y como casi todos los votos son "no", casi todos los puntajes salen negativos). Por eso aquí
     "le gusta" son los atuendos que el sistema pone arriba, tantos como la proporción de corazones del
     entrenamiento (al menos uno).
  5. Evaluar: exactitud, precisión, recall, F1 y matriz de confusión [[VN, FP], [FN, VP]]. Además, "orden":
     la probabilidad de que un atuendo con corazón quede por encima de uno sin corazón (0.5 = al azar,
     1 = perfecto; los empates cuentan 0.5). Es la medida que más se parece a lo que hace la app.

Con pocos votos, una sola división depende mucho de qué votos cayeron en la prueba. Por eso también se da el
promedio de 20 divisiones distintas. No se usa scikit-learn: la división se hace con pandas y las métricas se
calculan a mano, para que se vea de dónde sale cada número.
"""

import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends

from limpieza_de_datos.limpieza_de_datos import CARACTERISTICAS, limpiar_votos
from servidor.aprendizaje import PESO_PARECIDO, distancia, entrenar, escalar, pesos_iniciales, puntuar
from servidor.base_datos import consultar, consultar_uno
from servidor.seguridad import usuario_actual

PROPORCION_PRUEBA = 0.30
SEMILLA = 42
REPETICIONES = 20
CARPETA_CSV = Path(__file__).resolve().parent / "datos"


# ------------------------------------------------------------
# 1. DIVIDIR EN ENTRENAMIENTO Y PRUEBA (estratificado)
# ------------------------------------------------------------

def dividir(df: pd.DataFrame, semilla: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """El 30 % de los corazones y el 30 % de los "no" van a prueba; el resto a entrenamiento."""
    prueba = df.groupby("me_gusta", group_keys=False).sample(frac=PROPORCION_PRUEBA, random_state=semilla)
    return df.drop(prueba.index), prueba


# ------------------------------------------------------------
# 2. LOS TRES SISTEMAS
# ------------------------------------------------------------

def votos_para_entrenar(df: pd.DataFrame) -> list[dict]:
    """El formato que espera entrenar(): me_gusta en +1/-1 y las características en un diccionario."""
    return [{"me_gusta": 1 if fila["me_gusta"] == 1 else -1,
             "caracteristicas": {c: float(fila[c]) for c in CARACTERISTICAS}} for _, fila in df.iterrows()]


def puntajes(pesos: dict, df: pd.DataFrame) -> pd.Series:
    return df.apply(lambda fila: puntuar(pesos, {c: float(fila[c]) for c in CARACTERISTICAS}), axis=1)


def arriba(puntaje: pd.Series, cuantos: int) -> pd.Series:
    """1 para los `cuantos` atuendos con mayor puntaje (lo que la app mostraría primero), 0 para los demás."""
    prediccion = pd.Series(0, index=puntaje.index)
    prediccion[puntaje.sort_values(ascending=False, kind="stable").index[:cuantos]] = 1
    return prediccion


def predicciones(entrenamiento: pd.DataFrame, prueba: pd.DataFrame, iniciales: dict) -> dict[str, tuple]:
    """Para cada sistema: (predicción 0/1, puntaje). Siempre "no" no ordena: todos valen igual.

    Además del perceptrón solo, se evalúa lo que de verdad usa la app (reordenar en aprendizaje.py): el
    parecido con los looks con corazón (distancia manhattan al más cercano) y la mezcla de los dos con
    PESO_PARECIDO, cada uno escalado de -1 a +1 dentro de la lista.
    """
    cuantos = max(1, round(len(prueba) * entrenamiento["me_gusta"].mean()))
    regla = puntajes(iniciales, prueba)
    perceptron = puntajes(entrenar(votos_para_entrenar(entrenamiento), iniciales), prueba)
    gustados = [{c: float(fila[c]) for c in CARACTERISTICAS} for _, fila in entrenamiento[entrenamiento["me_gusta"] == 1].iterrows()]
    parecido = prueba.apply(lambda fila: -min(distancia({c: float(fila[c]) for c in CARACTERISTICAS}, g) for g in gustados), axis=1)
    sistema = pd.Series([(1 - PESO_PARECIDO) * a + PESO_PARECIDO * b
                         for a, b in zip(escalar(list(perceptron)), escalar(list(parecido)))], index=prueba.index)
    return {
        "siempre_no": (pd.Series(0, index=prueba.index), pd.Series(0.0, index=prueba.index)),
        "regla_fija": (arriba(regla, cuantos), regla),
        "perceptron": (arriba(perceptron, cuantos), perceptron),
        "parecido": (arriba(parecido, cuantos), parecido),
        "sistema_actual": (arriba(sistema, cuantos), sistema),
    }


# ------------------------------------------------------------
# 3. METRICAS 
# ------------------------------------------------------------

def orden(real: pd.Series, puntaje: pd.Series) -> float:
    """De cada par (con corazón, sin corazón), en cuántos el de corazón quedó arriba. Empate = medio punto."""
    con, sin = puntaje[real == 1], puntaje[real == 0]
    if con.empty or sin.empty:
        return 0.5
    pares = [(a > b) + 0.5 * (a == b) for a in con for b in sin]
    return round(sum(pares) / len(pares), 3)


def metricas(real: pd.Series, prediccion: pd.Series, puntaje: pd.Series) -> dict:
    vp = int(((real == 1) & (prediccion == 1)).sum())  # dijo "le gusta" y sí le gustó
    vn = int(((real == 0) & (prediccion == 0)).sum())
    fp = int(((real == 0) & (prediccion == 1)).sum())  # dijo "le gusta" y no
    fn = int(((real == 1) & (prediccion == 0)).sum())  # no detectó uno que sí le gustó
    precision = vp / (vp + fp) if vp + fp else 0.0  # de los que dijo "le gusta", cuántos sí
    recall = vp / (vp + fn) if vp + fn else 0.0  # de los que sí gustaron, cuántos detectó
    return {
        "exactitud": round((vp + vn) / len(real), 3) if len(real) else 0.0,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(2 * precision * recall / (precision + recall), 3) if precision + recall else 0.0,
        "orden": orden(real, puntaje),
        "matriz": [[vn, fp], [fn, vp]],  # filas: real (no, sí); columnas: predicho (no, sí)
    }


NOMBRES = {"regla_fija": "la regla del cuestionario", "perceptron": "el perceptrón",
           "parecido": "el parecido con tus looks con corazón", "sistema_actual": "el sistema actual (90 % parecido)"}


def conclusion(promedio: dict, corazones: int) -> str:
    """Quién ordena mejor tus gustos (el orden es la medida que más se parece a lo que hace la app)."""
    ranking = sorted(NOMBRES, key=lambda nombre: promedio[nombre]["orden"], reverse=True)
    frase = "Orden promedio (0.5 es al azar): " + ", ".join(
        f"{NOMBRES[nombre]} {promedio[nombre]['orden']}" for nombre in ranking) + "."
    mejor = ranking[0]
    if promedio[mejor]["orden"] <= 0.55:
        frase += " Ninguno ordena mejor que el azar todavía."
    else:
        frase += f" Lo que mejor predice tus gustos es {NOMBRES[mejor]}."
    if corazones < 10:
        frase += f" Ojo: solo hay {corazones} atuendos con corazón; con más votos la evaluación será más confiable."
    return frase


# ------------------------------------------------------------
# RUTA 
# ------------------------------------------------------------

rutas = APIRouter()


@rutas.get("/api/votos/evaluacion")
def evaluar_modelo(usuario: dict = Depends(usuario_actual)):
    """Evalúa el perceptrón de la persona contra la regla fija y contra decir siempre "no"."""
    filas = consultar("SELECT firma, me_gusta, caracteristicas FROM votos_atuendo WHERE usuario_id = ? ORDER BY id",
                      (usuario["id"],))
    votos = [{**f, "caracteristicas": json.loads(f["caracteristicas"])} for f in filas]
    validos = limpiar_votos(votos)["validos"]  # 1. solo los datos limpios
    df = pd.DataFrame([{"firma": v["firma"], **{c: v["caracteristicas"][c] for c in CARACTERISTICAS},
                        "me_gusta": 1 if v["me_gusta"] == 1 else 0} for v in validos])
    corazones = int(df["me_gusta"].sum()) if len(df) else 0
    if corazones < 2 or len(df) - corazones < 2:
        return {"listo": False, "mensaje": "Hacen falta al menos 2 atuendos con corazón y 2 sin corazón para evaluar."}

    iniciales = pesos_iniciales(consultar_uno("SELECT * FROM preferencias_usuario WHERE usuario_id = ?",
                                              (usuario["id"],)) or {})

    # 2 a 5 con una sola división, como la práctica.
    entrenamiento, prueba = dividir(df, SEMILLA)
    pred = predicciones(entrenamiento, prueba, iniciales)
    una = {nombre: metricas(prueba["me_gusta"], p, s) for nombre, (p, s) in pred.items()}

    # Lo mismo con 20 divisiones distintas, para no depender de la suerte de una sola.
    acumulado = {nombre: {m: 0.0 for m in ("exactitud", "precision", "recall", "f1", "orden")} for nombre in pred}
    for semilla in range(REPETICIONES):
        entrenamiento_r, prueba_r = dividir(df, semilla)
        for nombre, (p, s) in predicciones(entrenamiento_r, prueba_r, iniciales).items():
            for m, valor in metricas(prueba_r["me_gusta"], p, s).items():
                if m != "matriz":
                    acumulado[nombre][m] += valor / REPETICIONES
    promedio = {nombre: {m: round(v, 3) for m, v in ms.items()} for nombre, ms in acumulado.items()}

    # Comparación voto por voto de la división principal, para revisarla en Excel.
    CARPETA_CSV.mkdir(exist_ok=True)
    comparacion = prueba[["firma", "me_gusta"]].rename(columns={"me_gusta": "real"})
    for nombre, (p, s) in pred.items():
        comparacion[nombre] = p
        comparacion[f"puntaje_{nombre}"] = s.round(3)
    comparacion.to_csv(CARPETA_CSV / f"evaluacion_usuario_{usuario['id']}.csv", index=False, encoding="utf-8")

    return {
        "listo": True,
        "datos": {"votos_validos": len(df), "con_corazon": corazones,
                  "entrenamiento": len(entrenamiento), "prueba": len(prueba)},
        "una_division": una,
        f"promedio_{REPETICIONES}_divisiones": promedio,
        "conclusion": conclusion(promedio, corazones),
        "archivo": f"limpieza_de_datos/datos/evaluacion_usuario_{usuario['id']}.csv",
    }
