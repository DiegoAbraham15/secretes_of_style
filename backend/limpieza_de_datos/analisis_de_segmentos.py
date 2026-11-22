"""Módulo de validación de segmentos: confiabilidad de los grupos de K-means del armario.

No basta con formar grupos: hay que saber si son confiables. Con las mismas prendas y variables de
segmentacion_kmeans.py:
  1. Inicializaciones: k-means++ contra random (inercia, silhouette, iteraciones y si coinciden).
  2. Escaladores: StandardScaler contra MinMaxScaler (silhouette de cada uno y ARI entre sus grupos).
  3. Estabilidad: K-means con las semillas 10, 20, 30, 40, 50 y 42; ARI entre cada par de ejecuciones.
     ARI 1 = mismos grupos aunque cambien sus números; cerca de 0 = coincidencia como al azar.
  4. Centroides y distancias: el centro de cada grupo en unidades originales y la distancia de cada prenda a él.
  5. Posibles atípicos: prendas cuya distancia a su centroide supera el percentil 95 de todas las distancias.
     Es una regla exploratoria: una prenda lejos de su grupo es "rara" dentro del armario (difícil de
     combinar o mal registrada), no necesariamente un error.
  6. Exportar el reporte a CSV.
Esta ruta NO cambia lo que hace la app.
"""

import itertools

import numpy as np
from fastapi import APIRouter, Depends

from limpieza_de_datos.evaluacion_del_modelo import CARPETA_CSV
from limpieza_de_datos.segmentacion_kmeans import (MINIMO_PRENDAS, PERCENTIL_ATIPICOS, SEMILLA, VARIABLES, ari,
                                                   distancia_al_centro, estandarizar, kmeans,
                                                   min_max, segmentar, silhouette, silhouette_por_registro,
                                                   tabla_de_prendas)
from servidor.seguridad import usuario_actual

SEMILLAS = [10, 20, 30, 40, 50, 42]


def comparar_inicializaciones(X: np.ndarray, k: int) -> dict:
    """Con una sola inicialización por corrida se nota más la diferencia; se promedian las seis semillas."""
    resultado = {}
    for inicio in ("k-means++", "random"):
        corridas = [kmeans(X, k, semilla, inicio, inicializaciones=1) for semilla in SEMILLAS]
        resultado[inicio] = {
            "inercia_promedio": round(float(np.mean([c["inercia"] for c in corridas])), 3),
            "inercia_peor": round(float(max(c["inercia"] for c in corridas)), 3),
            "iteraciones_promedio": round(float(np.mean([c["iteraciones"] for c in corridas])), 1),
            "silhouette_promedio": round(float(np.mean([silhouette(X, c["etiquetas"]) for c in corridas])), 4),
        }
    final_pp, final_random = kmeans(X, k, inicio="k-means++"), kmeans(X, k, inicio="random")
    resultado["ari_entre_las_dos"] = ari(final_pp["etiquetas"], final_random["etiquetas"])  # con 20 inicializaciones
    return resultado


def comparar_escaladores(datos: np.ndarray, k: int) -> dict:
    estandar, minmax = estandarizar(datos), min_max(datos)
    grupos_estandar, grupos_minmax = kmeans(estandar, k)["etiquetas"], kmeans(minmax, k)["etiquetas"]
    return {"StandardScaler": {"silhouette": silhouette(estandar, grupos_estandar)},
            "MinMaxScaler": {"silhouette": silhouette(minmax, grupos_minmax)},
            "ari_entre_los_dos": ari(grupos_estandar, grupos_minmax)}


def estabilidad(X: np.ndarray, k: int) -> dict:
    particiones = {s: kmeans(X, k, semilla=s)["etiquetas"] for s in SEMILLAS}
    pares = [{"semilla_a": a, "semilla_b": b, "ari": ari(particiones[a], particiones[b])}
             for a, b in itertools.combinations(SEMILLAS, 2)]
    return {"comparaciones": pares, "ari_promedio": round(float(np.mean([p["ari"] for p in pares])), 4),
            "ari_minimo": min(p["ari"] for p in pares)}


def estabilidad_en_palabras(ari_promedio: float) -> str:
    if ari_promedio >= 0.9:
        return "muy estables"
    return "bastante estables" if ari_promedio >= 0.75 else "poco estables"


rutas = APIRouter()


@rutas.get("/api/prendas/segmentos/analisis")
def analizar_segmentos(usuario: dict = Depends(usuario_actual)):
    """Confiabilidad de los segmentos del armario y prendas atípicas dentro de su grupo."""
    df = tabla_de_prendas(usuario["id"])
    if len(df) < MINIMO_PRENDAS:
        return {"listo": False, "mensaje": f"Hacen falta al menos {MINIMO_PRENDAS} prendas para formar grupos."}
    datos = df[VARIABLES].to_numpy(dtype=float)
    segmentos = segmentar(df)  # el modelo final de segmentacion_kmeans.py: StandardScaler, k-means++, semilla 42
    X, k, modelo = segmentos["X"], segmentos["k"], segmentos["modelo"]
    etiquetas = modelo["etiquetas"]

    # Centroides y distancias (en el espacio escalado, que es donde K-means mide).
    distancia, umbral = distancia_al_centro(X, modelo)
    reporte = df.assign(segmento=etiquetas + 1, nombre_segmento=[segmentos["nombres"][j] for j in etiquetas],
                        distancia_centroide=distancia.round(4),
                        silhouette_individual=silhouette_por_registro(X, etiquetas).round(4),
                        posible_atipico=distancia > umbral)
    atipicos = reporte[reporte["posible_atipico"]].sort_values("distancia_centroide", ascending=False)

    CARPETA_CSV.mkdir(exist_ok=True)
    reporte.to_csv(CARPETA_CSV / f"analisis_segmentos_usuario_{usuario['id']}.csv", index=False, encoding="utf-8")

    inicios, escaladores, estable = comparar_inicializaciones(X, k), comparar_escaladores(datos, k), estabilidad(X, k)
    centroides = [{"segmento": j + 1, "nombre": nombre,
                   "centroide": {v: round(float(df.loc[etiquetas == j, v].mean()), 2) for v in VARIABLES},
                   "distancia_promedio": round(float(distancia[etiquetas == j].mean()), 4)}
                  for j, nombre in segmentos["nombres"].items()]
    return {
        "listo": True,
        "k": k,
        "semilla": SEMILLA,
        "inicializaciones": inicios,
        "escaladores": escaladores,
        "estabilidad": estable,
        "centroides": centroides,
        "atipicos": {"percentil": PERCENTIL_ATIPICOS, "umbral_distancia": round(umbral, 4),
                     "prendas": [{"id": int(f.id), "prenda": f.prenda, "color": f.color, "segmento": f.nombre_segmento,
                                  "distancia": float(f.distancia_centroide), "silhouette": float(f.silhouette_individual)}
                                 for f in atipicos.itertuples()]},
        "conclusion": (f"Los {k} grupos son {estabilidad_en_palabras(estable['ari_promedio'])} entre "
                       f"semillas (ARI promedio {estable['ari_promedio']}). k-means++ deja una inercia promedio de "
                       f"{inicios['k-means++']['inercia_promedio']} contra {inicios['random']['inercia_promedio']} de random "
                       f"con una sola inicialización. StandardScaler y MinMaxScaler coinciden con ARI "
                       f"{escaladores['ari_entre_los_dos']}. Posibles atípicos: "
                       + (", ".join(f"{a.prenda} {a.color} (#{a.id})" for a in atipicos.itertuples()) or "ninguno") + "."),
        "archivo": f"limpieza_de_datos/datos/analisis_segmentos_usuario_{usuario['id']}.csv",
    }
