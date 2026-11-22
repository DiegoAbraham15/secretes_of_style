"""Comprueba la CNN 1D: la secuencia del look, la cuenta con numpy y su lugar en reordenar.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_cnn.py"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from servidor import red_convolucional as red  # noqa: E402
from servidor.aprendizaje import AJUSTE_MAXIMO, PESO_CNN, escalar, reordenar  # noqa: E402


def prenda(id, categoria, color, estilo="casual", abrigo=2, estampado="liso"):
    return {"id": id, "categoria": categoria, "color_principal": color, "nivel_abrigo": abrigo, "estampado": estampado,
            "estilo": estilo}


def sugerencia(costo, *prendas):
    return {"costo": costo, "elementos": [{"rol": p["categoria"], "prenda": p} for p in prendas]}


arriba = prenda(1, "parte_superior", "rojo", "urbano", 3, "rayas")
abajo = prenda(2, "parte_inferior", "negro", "formal", 1)
zapatos = prenda(3, "calzado", "blanco", "deportivo", 1)
abrigo = prenda(4, "abrigo", "azul_marino", "formal", 5)
cuestionario = {"paleta": "oscuros", "ropa": "urbano", "estampados": "liso"}

# --- 1. La secuencia del look ---
x = red.secuencia_de([arriba, abajo, zapatos], cuestionario)
ok(x.shape == (len(red.CANALES), 5), f"la secuencia es [canales, 5 posiciones]: {x.shape}")
ok(red.ORDEN == ["abrigo", "parte_superior", "parte_inferior", "calzado", "accesorio"], "orden del cuerpo, de afuera hacia adentro")
ok(list(x[0]) == [0, 1, 1, 1, 0], "'presente' marca solo las posiciones que trae el look")
ok(x[red.CANALES.index("abrigo"), 1] == 0.5 and x[red.CANALES.index("tono"), 2] == 1.0,
   "abrigo y tono van de 0 a 1 (abrigo 3 → 0.5; negro, el más oscuro → 1)")
ok(x[red.CANALES.index("estampado"), 1] == 1 and x[red.CANALES.index("neutro"), 2] == 1, "estampado y neutro por prenda")
ok(x[red.CANALES.index("estilo_urbano"), 1] == 1 and x[red.CANALES.index("estilo_formal"), 2] == 1, "estilo en una columna por estilo")
ok(all(x[red.CANALES.index("ropa_urbano")] == 1) and all(x[red.CANALES.index("ropa_casual")] == 0),
   "el cuestionario va igual en las 5 posiciones")
ok(np.array_equal(x, red.secuencia_de([zapatos, abajo, arriba], cuestionario)), "el orden de las prendas no importa")
sin_respuestas = red.secuencia_de([arriba, abajo, zapatos], None)
ok(sin_respuestas[red.CANALES.index("paleta_sin_preferencia")].all() and sin_respuestas[red.CANALES.index("estampados_uno")].all(),
   "sin cuestionario se usan las respuestas por defecto")
ok(x.min() >= 0 and x.max() <= 1, "todos los valores quedan entre 0 y 1")

# --- 2. Sin modelo entrenado: todo como antes ---
red._cargado["pesos"] = None
ok(red.probabilidades([[arriba, abajo, zapatos]], cuestionario) is None, "sin modelo, probabilidades() devuelve None")
lista = [sugerencia(10, arriba, abajo, zapatos), sugerencia(10.5, abajo, zapatos), sugerencia(11, arriba, abajo, zapatos, abrigo)]
ok(all(s["costo_final"] == s["costo"] for s in reordenar([dict(s) for s in lista], {}, {}, (), None)),
   "con cnn=None, sin pesos ni votos, el orden es exactamente el de A* (como antes de la CNN)")

# --- 3. La cuenta con numpy (una red pequeña con pesos inventados, comparada a mano) ---
rng = np.random.default_rng(0)
canales = len(red.CANALES)
p = {"media": np.zeros((canales, 1), np.float32), "desviacion": np.ones((canales, 1), np.float32), "eps": np.float32(1e-5),
     "conv1.weight": rng.normal(size=(4, canales, 2)).astype(np.float32), "conv1.bias": rng.normal(size=4).astype(np.float32),
     "conv2.weight": rng.normal(size=(3, 4, 2)).astype(np.float32), "conv2.bias": rng.normal(size=3).astype(np.float32),
     "clasificador.weight": rng.normal(size=(1, 3)).astype(np.float32), "clasificador.bias": np.zeros(1, np.float32)}
for capa, n in (("bn1", 4), ("bn2", 3)):
    p.update({f"{capa}.running_mean": np.zeros(n, np.float32), f"{capa}.running_var": np.ones(n, np.float32),
              f"{capa}.weight": np.ones(n, np.float32), f"{capa}.bias": np.zeros(n, np.float32)})


def a_mano(x):
    """La misma red con ciclos, sin einsum: relleno de 1 → conv → ReLU → conv → ReLU → promedio → lineal."""
    def conv(entrada, w, b):
        salida = np.zeros((w.shape[0], entrada.shape[1] - 1))
        for o in range(w.shape[0]):
            for t in range(salida.shape[1]):
                salida[o, t] = b[o] + sum(w[o, i, k] * entrada[i, t + k] for i in range(w.shape[1]) for k in range(2))
        return salida
    escala = 1 / np.sqrt(1 + 1e-5)  # BatchNorm con media 0 y varianza 1
    h = np.maximum(conv(np.pad(x, ((0, 0), (1, 1))), p["conv1.weight"], p["conv1.bias"]) * escala, 0)
    h = np.maximum(conv(h, p["conv2.weight"], p["conv2.bias"]) * escala, 0)
    return 1 / (1 + np.exp(-(h.mean(axis=1) @ p["clasificador.weight"][0])))


calculado = red.probabilidad_de_lote(x[None], p)[0]
ok(abs(calculado - a_mano(x)) < 1e-5, f"Conv1d + BatchNorm + promedio con numpy = cuenta a mano ({calculado:.6f})")
ok(red.convolucion(np.ones((1, 1, 5)), np.ones((1, 1, 2)), np.zeros(1), 1).shape == (1, 1, 6),
   "con relleno 1 y kernel 2, 5 posiciones dan 6 (como PyTorch)")

# --- 4. Con el modelo entrenado de verdad (si ya se corrió entrenamiento_cnn/entrenamiento_cnn.py) ---
red._cargado.clear()
modelo = red.modelo()
if modelo is None:
    print("(sin modelos_entrenados/cnn_atuendos.npz: se saltan las pruebas con el modelo real)")
else:
    probabilidades = red.probabilidades([[arriba, abajo, zapatos], [abajo, zapatos], [abrigo, arriba, abajo, zapatos]], cuestionario)
    ok(len(probabilidades) == 3 and all(0 < v < 1 for v in probabilidades), f"una probabilidad entre 0 y 1 por look: {probabilidades}")
    ok(red.probabilidades([], cuestionario) is None, "sin looks no hay nada que predecir")
    lote = np.stack([red.secuencia_de([arriba, abajo, zapatos], cuestionario)] * 2)
    ok(np.allclose(red.probabilidad_de_lote(lote, modelo), probabilidades[0]), "la misma entrada da la misma salida")

    # --- 5. Su lugar en reordenar ---
    cnn = [0.9, 0.1, 0.5]
    resultado = reordenar([dict(s) for s in lista], {}, {}, (), cnn)
    esperado = {10: -AJUSTE_MAXIMO * PESO_CNN * 1, 10.5: AJUSTE_MAXIMO * PESO_CNN * 1, 11: 0.0}
    ok(all(abs(s["costo_final"] - (s["costo"] + esperado[s["costo"]])) < 1e-9 for s in resultado),
       "sin votos ni pesos, la CNN mueve el costo PESO_CNN × AJUSTE_MAXIMO como máximo")
    ok(escalar(cnn) == [1.0, -1.0, 0.0], "la CNN se escala de -1 a +1 dentro de la lista, como el perceptrón")
    votado = reordenar([dict(s) for s in lista], {}, {"1-2-3": -1}, (), cnn)
    ok(next(s for s in votado if s["costo"] == 10)["costo_final"] == 10 + AJUSTE_MAXIMO,
       "lo ya votado sigue valiendo ±1: la CNN no lo adivina")

    # --- 6. Lo que ve la app en "Cómo aprende tus gustos" ---
    from limpieza_de_datos.evaluacion_del_modelo import cnn_entrenada
    resumen = cnn_entrenada()
    ok(resumen is not None and 0.5 < resumen["auc"] <= 1 and {"CNN 1D", "Random Forest"} <= {f["modelo"] for f in resumen["comparacion"]},
       f"la evaluación incluye cómo le fue a la CNN al entrenarse (AUC {resumen and resumen['auc']})")

terminar()
