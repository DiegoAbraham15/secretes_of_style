"""ETAPA 6 · La CNN contra otros modelos.

Con los mismos looks de prueba (personas que ningún modelo vio):
  - CNN 1D                 la de entrenamiento_cnn.py (probabilidades calculadas con numpy, como en la app).
  - Random Forest          300 árboles sobre la secuencia aplanada (23 × 5 = 115 valores).
  - Regresión logística    modelo lineal sobre lo mismo: si la CNN no le gana, la convolución no aporta.
  - Regla del cuestionario lo que hace hoy la app con una persona sin votos (pesos_iniciales · características).
  - Siempre "no"           la referencia.

Se compara con AUC (qué tan bien ordena: la app usa la red para ORDENAR looks) y con F1 (umbral elegido en
validación). Los resultados se agregan a modelos_entrenados/metricas_cnn.json.
"""

import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

from comun import ARCHIVO_METRICAS, ARCHIVO_TENSORES, SEMILLA, titulo
from servidor import red_convolucional


def medir(nombre, y_val, p_val, y, p):
    """F1 y exactitud con el umbral que mejor funciona en validación; AUC no necesita umbral."""
    if np.ptp(p_val) == 0:  # un modelo que da siempre lo mismo no tiene umbral: siempre dice "no"
        prediccion = np.zeros(len(y), dtype=bool)
    else:
        umbral = max(np.unique(np.quantile(p_val, np.linspace(0.01, 0.99, 99))),
                     key=lambda u: f1_score(y_val, p_val >= u))
        prediccion = p >= umbral
    fila = {"modelo": nombre, "auc": float(roc_auc_score(y, p)) if np.ptp(p) else 0.5,
            "f1": float(f1_score(y, prediccion, zero_division=0)), "exactitud": float(accuracy_score(y, prediccion))}
    print(f"{nombre:24} AUC {fila['auc']:.3f} · F1 {fila['f1']:.3f} · exactitud {fila['exactitud']:.3f}")
    return fila


def main():
    titulo("SECRETS OF STYLE · ETAPA 6 · COMPARACIÓN DE MODELOS")
    with np.load(ARCHIVO_TENSORES) as d:
        datos = {nombre: d[nombre] for nombre in d.files}
    plano = {n: ((datos[f"X_{n}"] - datos["media"]) / datos["desviacion"]).reshape(len(datos[f"X_{n}"]), -1)
             for n in ("entrenamiento", "validacion", "prueba")}
    y_ent, y_val, y = datos["y_entrenamiento"], datos["y_validacion"], datos["y_prueba"]

    pesos = red_convolucional.modelo()
    if pesos is None:
        raise FileNotFoundError("No hay modelo entrenado: corre primero entrenamiento_cnn.py")
    cnn = {n: red_convolucional.probabilidad_de_lote(datos[f"X_{n}"], pesos) for n in ("validacion", "prueba")}

    print("Entrenando Random Forest (300 árboles) y regresión logística…")
    bosque = RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=SEMILLA, n_jobs=-1)
    bosque.fit(plano["entrenamiento"], y_ent)
    logistica = LogisticRegression(max_iter=2000).fit(plano["entrenamiento"], y_ent)

    titulo("RESULTADOS EN PRUEBA (1 500 personas nuevas, 7 500 looks)")
    filas = [
        medir("CNN 1D", y_val, cnn["validacion"], y, cnn["prueba"]),
        medir("Random Forest", y_val, bosque.predict_proba(plano["validacion"])[:, 1], y, bosque.predict_proba(plano["prueba"])[:, 1]),
        medir("Regresión logística", y_val, logistica.predict_proba(plano["validacion"])[:, 1], y, logistica.predict_proba(plano["prueba"])[:, 1]),
        medir("Regla del cuestionario", y_val, datos["regla_validacion"], y, datos["regla_prueba"]),
        medir("Siempre no", y_val, np.zeros(len(y_val)), y, np.zeros(len(y))),
    ]
    mejor = max(filas, key=lambda f: f["auc"])
    print(f"\nOrdena mejor (AUC): {mejor['modelo']}")

    metricas = json.loads(ARCHIVO_METRICAS.read_text(encoding="utf-8"))
    metricas["comparacion"] = filas
    ARCHIVO_METRICAS.write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Comparación agregada a {ARCHIVO_METRICAS}")
    titulo("ETAPA 6 FINALIZADA")


if __name__ == "__main__":
    main()
