"""Comprueba la limpieza de datos de los votos antes de entrenar al perceptrón.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python limpieza_de_datos\\prueba_limpieza_de_datos.py"""
import os
import sys

# La carpeta de este archivo se cambia por backend: si no, "limpieza_de_datos" sería el archivo .py de al lado
# y no la carpeta, y fallaría el import de principal.py.
sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi.testclient import TestClient  # noqa: E402
from servidor import base_datos, principal  # noqa: E402
from servidor.aprendizaje import caracteristicas_de, puntuar  # noqa: E402
from limpieza_de_datos import limpieza_de_datos as limpieza  # noqa: E402
from limpieza_de_datos.limpieza_de_datos import CARACTERISTICAS, limpiar_votos  # noqa: E402

limpieza.CARPETA_CSV = temporal / "datos"  # los CSV de la prueba no van a la carpeta real

def prenda(id, categoria, color, estilo="casual"):
    return {"id": id, "categoria": categoria, "color_principal": color, "nivel_abrigo": 2, "impermeable": False,
            "estado": "disponible", "subcategoria": None, "estampado": "liso", "estilo": estilo}


def voto(firma, me_gusta, prendas):
    return {"firma": firma, "me_gusta": me_gusta, "caracteristicas": caracteristicas_de(prendas)}


def guardar_voto(usuario_id, firma, me_gusta, prendas):
    """Escribe un voto directo en la colección votos_atuendo, como lo deja la API."""
    base_datos.bd().votos_atuendo.insert_one({"usuario_id": usuario_id, **voto(firma, me_gusta, prendas),
                                              "fecha_creacion": base_datos.ahora()})


formal = [prenda(1, "parte_superior", "blanco", "formal"), prenda(2, "parte_inferior", "negro", "formal"),
          prenda(3, "calzado", "cafe", "formal")]
gemelo = [prenda(1, "parte_superior", "blanco", "formal"), prenda(2, "parte_inferior", "negro", "formal"),
          prenda(4, "calzado", "cafe", "formal")]  # otros zapatos café formales: mismas características
casual = [prenda(5, "parte_superior", "rojo"), prenda(6, "parte_inferior", "mezclilla"), prenda(7, "calzado", "blanco")]

# --- Las características que revisa la limpieza son las que arma el perceptrón ---
ok(set(CARACTERISTICAS) == set(caracteristicas_de(formal)), "la limpieza espera las mismas características que caracteristicas_de")

# --- Datos limpios: no se aparta nada ---
limpios = [voto("1-2-3", 1, formal), voto("5-6-7", -1, casual)]
resultado = limpiar_votos(limpios)
ok(len(resultado["validos"]) == 2 and not resultado["revision"], "sin errores, todos los votos entrenan")

# --- Fila duplicada: drop_duplicates la elimina ---
resultado = limpiar_votos([voto("1-2-3", 1, formal), voto("1-2-3", 1, formal)])
ok(len(resultado["validos"]) == 1 and not resultado["revision"], "la fila duplicada se elimina")

# --- Sin votos ---
ok(limpiar_votos([]) == {"validos": [], "revision": []}, "sin votos no truena")

# --- Incompleto, fuera de rango y voto inválido ---
incompleto = voto("1-2-3", 1, formal)
del incompleto["caracteristicas"]["tono"]
fuera = voto("5-6-7", -1, casual)
fuera["caracteristicas"]["abrigo"] = 1.5
raro = voto("9-8", 0, casual)
sin_texto = {"firma": "9-9", "me_gusta": 1, "caracteristicas": None}
resultado = limpiar_votos([incompleto, fuera, raro, sin_texto])
motivos = [v["motivo"] for v in resultado["revision"]]
ok(not resultado["validos"], "ningún voto con errores entrena")
ok("tono" in motivos[0] and "incompleto" in motivos[0], "anota la característica que falta")
ok("abrigo" in motivos[1] and "fuera de 0 a 1" in motivos[1], "anota la característica fuera de rango")
ok("+1 o -1" in motivos[2], "anota el voto inválido")
ok("incompleto" in motivos[3], "un voto sin características no truena la limpieza")

# --- Contradicción: dos atuendos gemelos, uno con corazón y otro sin ---
resultado = limpiar_votos([voto("1-2-4", -1, gemelo), voto("1-2-3", 1, formal), voto("5-6-7", -1, casual)])
ok([v["firma"] for v in resultado["validos"]] == ["1-2-3", "5-6-7"], "gana el corazón y se conserva el orden")
ok(resultado["revision"][0]["firma"] == "1-2-4" and "corazón" in resultado["revision"][0]["motivo"],
   "el gemelo sin corazón va a revisión con su motivo")

# --- Con la API: el perceptrón entrena solo con los válidos y la ruta lo reporta ---
cliente = TestClient(principal.aplicacion)
token = cliente.post("/api/auth/registro", json={"correo": "limpieza@prueba.com", "contraseña": "12345678"}).json()["token_acceso"]
encabezado = {"Authorization": f"Bearer {token}"}
usuario_id = cliente.get("/api/auth/yo", headers=encabezado).json()["id"]
for firma, me_gusta, prendas in [("1-2-4", -1, gemelo), ("1-2-3", 1, formal)]:
    guardar_voto(usuario_id, firma, me_gusta, prendas)

ok(principal.reentrenar(usuario_id) == 2, "reentrenar sigue contando todos los votos")
pesos = principal.leer_pesos(usuario_id)
ok(puntuar(pesos, caracteristicas_de(formal)) > 0, "el perceptrón aprende el corazón sin que el gemelo lo cancele")

reporte = cliente.get("/api/votos/limpieza", headers=encabezado).json()
ok(reporte["total"] == 2 and reporte["validos"] == 1 and reporte["validos_con_corazon"] == 1, "la ruta reporta cuántos entrenan")
ok(reporte["revision"][0]["firma"] == "1-2-4", "la ruta muestra qué se apartó")
limpios_csv = limpieza.pd.read_csv(limpieza.CARPETA_CSV / f"votos_limpios_usuario_{usuario_id}.csv")
revision_csv = limpieza.pd.read_csv(limpieza.CARPETA_CSV / f"votos_revision_usuario_{usuario_id}.csv")
ok(list(limpios_csv["firma"]) == ["1-2-3"] and list(revision_csv["firma"]) == ["1-2-4"], "exporta los dos CSV")
ok("motivo" in revision_csv.columns, "el CSV de revisión trae el motivo")
ok(cliente.get("/api/votos/limpieza").status_code == 401, "la ruta pide sesión")

# ============================================================
# LIMPIEZA DE LAS PRENDAS (fotos y datos del armario)
# ============================================================
from PIL import Image  # noqa: E402

from limpieza_de_datos import evaluacion_del_modelo as evaluacion  # noqa: E402
from limpieza_de_datos import limpieza_de_prendas  # noqa: E402
from limpieza_de_datos import modelos  # noqa: E402
from limpieza_de_datos import seleccion_del_modelo as seleccion  # noqa: E402

limpieza_de_prendas.CARPETA_CSV = temporal / "datos"
evaluacion.CARPETA_CSV = temporal / "datos"
seleccion.CARPETA_CSV = temporal / "datos"
carpeta_prendas = base_datos.CARPETA_ARCHIVOS / "prendas"
carpeta_prendas.mkdir(parents=True, exist_ok=True)
fotos = {"roja": ((600, 800), (200, 20, 30)), "chica": ((200, 200), (30, 40, 200)),
         "gris": ((600, 800), (128, 128, 128)), "roja_intensa": ((600, 800), (230, 0, 20))}
for nombre, (tamaño, color) in fotos.items():
    Image.new("RGB", tamaño, color).save(carpeta_prendas / f"{nombre}.jpg")
(carpeta_prendas / "copia.jpg").write_bytes((carpeta_prendas / "roja.jpg").read_bytes())  # la misma foto


def nueva_prenda(foto, color, subcategoria=None, categoria="parte_superior"):
    prenda_id = base_datos.siguiente_id("prendas")
    base_datos.bd().prendas.insert_one({
        "_id": prenda_id, "usuario_id": usuario_id, "url_imagen": f"/archivos/prendas/{foto}.jpg", "categoria": categoria,
        "subcategoria": subcategoria, "color_principal": color, "nivel_abrigo": 2, "impermeable": False,
        "estampado": "liso", "estilo": "casual", "estado": "disponible", "fecha_creacion": base_datos.ahora(),
    })
    return prenda_id


bien = nueva_prenda("roja", "rojo", "Playera")
chica = nueva_prenda("chica", "azul", "Playera")
gris_como_rojo = nueva_prenda("gris", "rojo", "Suéter")  # color vivo guardado, pero la foto es gris
blanca_intensa = nueva_prenda("roja_intensa", "blanco", "Blusa")  # blanco guardado, pero la foto es roja
repetida = nueva_prenda("copia", "rojo")  # misma foto que "bien" y sin tipo de prenda
sin_foto = nueva_prenda("no_existe", "negro", "Jeans", "parte_inferior")

revision = cliente.get("/api/prendas/revision", headers=encabezado).json()
apartadas = {r["id"]: r["motivo"] for r in revision["revision"]}
ok(revision["total"] == 6 and revision["validas"] == 1 and bien not in apartadas, "la prenda bien hecha no se aparta")
ok("muy chica (200x200 px)" in apartadas.get(chica, ""), "foto muy chica, con su tamaño")
ok("se ve gris" in apartadas.get(gris_como_rojo, ""), "color vivo guardado con foto gris")
ok("color intenso" in apartadas.get(blanca_intensa, ""), "blanco guardado con foto de color intenso")
ok(f"prenda #{bien}" in apartadas.get(repetida, ""), "foto repetida dice de qué prenda")
ok("no se encontró la foto" in apartadas.get(sin_foto, ""), "foto que no existe")
ok(revision["faltantes"].get("subcategoria") == 1, "cuenta los faltantes por columna, como isnull().sum()")
ok((limpieza_de_prendas.CARPETA_CSV / f"prendas_revision_usuario_{usuario_id}.csv").exists(), "exporta el CSV de prendas")
ok(cliente.get(f"/api/prendas/{chica}/revision", headers=encabezado).json()["motivos"][0].startswith("la foto es muy chica"),
   "la ruta de una prenda da sus motivos")
ok(cliente.get(f"/api/prendas/{bien}/revision", headers=encabezado).json() == {"motivos": []}, "sin motivos si está bien")
ok(cliente.get("/api/prendas/99999/revision", headers=encabezado).status_code == 404, "prenda ajena o inexistente -> 404")
ok(cliente.get("/api/prendas/revision").status_code == 401, "la revisión del armario pide sesión")
ok(cliente.get(f"/api/prendas/{bien}", headers=encabezado).status_code == 200, "la ruta normal de la prenda sigue funcionando")

# ============================================================
# EVALUACION DEL MODELO
# ============================================================
real = limpieza.pd.Series([1, 1, 0, 0, 0])
m = evaluacion.metricas(real, limpieza.pd.Series([1, 0, 1, 0, 0]), limpieza.pd.Series([0.9, 0.1, 0.5, 0.2, 0.0]))
ok(m["matriz"] == [[2, 1], [1, 1]] and m["exactitud"] == 0.6 and m["precision"] == 0.5 and m["recall"] == 0.5,
   "métricas calculadas a mano")
ok(m["orden"] == round(4 / 6, 3), "orden: 4 de 6 pares (corazón, sin corazón) quedan bien")
ok(evaluacion.orden(real, limpieza.pd.Series([1.0] * 5)) == 0.5, "si todo empata, el orden es 0.5 (azar)")
datos = limpieza.pd.DataFrame({"me_gusta": [1] * 10 + [0] * 30})
entrenamiento, prueba = evaluacion.dividir(datos, 42)
ok(len(prueba) == 12 and prueba["me_gusta"].sum() == 3 and len(entrenamiento) == 28, "la división conserva la proporción (stratify)")

ok(cliente.get("/api/votos/evaluacion", headers=encabezado).json()["listo"] is False, "con pocos votos avisa que falta")
casual2 = [prenda(8, "parte_superior", "rojo"), prenda(9, "parte_inferior", "verde"), prenda(10, "calzado", "rojo")]
looks = [("a", 1, formal), ("b", 1, formal), ("c", -1, casual), ("d", -1, casual), ("e", -1, casual2), ("f", -1, casual2),
         ("g", -1, casual), ("h", -1, casual2)]
base_datos.bd().votos_atuendo.delete_many({"usuario_id": usuario_id})
for firma, me_gusta, prendas in looks:
    guardar_voto(usuario_id, firma, me_gusta, prendas)
resultado = cliente.get("/api/votos/evaluacion", headers=encabezado).json()
ok(resultado["listo"] and resultado["datos"]["votos_validos"] == 8, "evalúa con los votos limpios")
ok(set(resultado["una_division"]) == {"siempre_no", "regla_fija", "perceptron", "parecido", "sistema_actual"},
   "compara los cinco sistemas")
ok(resultado["promedio_20_divisiones"]["parecido"]["orden"] == 1.0, "el parecido reconoce un look idéntico al del corazón")
ok((evaluacion.CARPETA_CSV / f"evaluacion_usuario_{usuario_id}.csv").exists(), "exporta la comparación voto por voto")
ok(cliente.get("/api/votos/evaluacion").status_code == 401, "la evaluación pide sesión")

# ============================================================
# SELECCION DEL MODELO (entrenamiento, validación y prueba)
# ============================================================
datos = limpieza.pd.DataFrame({"me_gusta": [1] * 10 + [0] * 40})
resto, prueba = seleccion.apartar(datos, seleccion.PROPORCION_PRUEBA, 42)
entrenamiento, validacion = seleccion.apartar(resto, seleccion.PROPORCION_VALIDACION, 0)
ok((len(entrenamiento), len(validacion), len(prueba)) == (30, 10, 10), "división 60 / 20 / 20")
ok([p["me_gusta"].sum() for p in (entrenamiento, validacion, prueba)] == [6, 2, 2], "las tres partes conservan la proporción")
ok(not set(prueba.index) & set(resto.index), "la prueba queda fuera de entrenamiento y validación")

conocidos = limpieza.pd.DataFrame([{**caracteristicas_de(formal), "me_gusta": 1}, {**caracteristicas_de(casual), "me_gusta": 0},
                                   {**caracteristicas_de(casual2), "me_gusta": 0}])
nuevos = limpieza.pd.DataFrame([caracteristicas_de(gemelo), caracteristicas_de(casual)])
ok(list(modelos.knn(conocidos, nuevos, 1)) == [1.0, 0.0], "KNN con k = 1 copia el voto del vecino más cercano")
ok(list(modelos.knn(conocidos, nuevos, 3)) == [1 / 3, 1 / 3], "KNN con k = 3 da la fracción de corazones de los 3 vecinos")
ok([seleccion.diagnostico(e, v) for e, v in ((0.4, 0.4), (1.0, 0.6), (0.9, 0.85))] == ["subajuste", "sobreajuste", "buen ajuste"],
   "diagnóstico de sobreajuste y subajuste")

ok(cliente.get("/api/votos/seleccion", headers=encabezado).json()["listo"] is False, "con 2 corazones avisa que faltan")
guardar_voto(usuario_id, "i", 1, formal)
resultado = cliente.get("/api/votos/seleccion", headers=encabezado).json()
ok(resultado["listo"] and len(resultado["comparacion"]) == len(seleccion.MODELOS), "compara los diez modelos")
ok(resultado["elegido"]["modelo"] in [m["modelo"] for m in resultado["comparacion"]], "elige uno de los comparados")
ok(resultado["modelo_de_la_app"]["modelo"].startswith("Parecido 90 %"), "mide también el modelo de la app en la prueba")
ok((seleccion.CARPETA_CSV / f"seleccion_usuario_{usuario_id}.csv").exists(), "exporta la tabla de la comparación")
ok(cliente.get("/api/votos/seleccion").status_code == 401, "la selección pide sesión")

# ============================================================
# OPTIMIZACION DE HIPERPARAMETROS
# ============================================================
import numpy as np  # noqa: E402

from limpieza_de_datos import analisis_de_segmentos as analisis  # noqa: E402
from limpieza_de_datos import optimizacion_hiperparametros as optimizacion  # noqa: E402
from limpieza_de_datos import pca_prendas  # noqa: E402
from limpieza_de_datos import segmentacion_kmeans as segmentacion  # noqa: E402

for modulo in (optimizacion, segmentacion, analisis, pca_prendas):
    modulo.CARPETA_CSV = temporal / "datos"
pd = limpieza.pd

datos = pd.DataFrame({"me_gusta": [1] * 10 + [0] * 40})
pliegues = optimizacion.pliegues_estratificados(datos, 5)
ok(sorted(i for _, v in pliegues for i in v) == list(datos.index), "los 5 pliegues reparten todos los votos sin repetir")
ok(all(len(v) == 10 and datos.loc[v, "me_gusta"].sum() == 2 for _, v in pliegues),
   "StratifiedKFold: cada pliegue conserva la proporción (2 corazones de 10)")
ok(all(not set(e) & set(v) for e, v in pliegues), "en cada pliegue, entrenamiento y validación no se mezclan")
ok(len(optimizacion.busqueda_en_rejilla()) == 46, "GridSearchCV prueba las 20 + 20 + 6 combinaciones")
al_azar = optimizacion.busqueda_al_azar(15)
ok(len(al_azar) == 30 and al_azar == optimizacion.busqueda_al_azar(15), "RandomizedSearchCV: 10 por modelo y reproducible")

ceros, unos = {c: 0.0 for c in CARACTERISTICAS}, {c: 1.0 for c in CARACTERISTICAS}
conocidos = pd.DataFrame([{**ceros, "me_gusta": 1}, {**unos, "me_gusta": 0}])
nuevo = pd.DataFrame([{c: 0.25 for c in CARACTERISTICAS}])
ok(modelos.knn(conocidos, nuevo, 2, "uniform", "manhattan").iloc[0] == 0.5, "KNN uniform: cada vecino vale igual")
ok(abs(modelos.knn(conocidos, nuevo, 2, "distance", "euclidean").iloc[0] - 0.75) < 1e-9,
   "KNN distance: el vecino 3 veces más cerca pesa 3 veces más")

resultado = cliente.get("/api/votos/optimizacion", headers=encabezado).json()
ok(resultado["listo"] and resultado["configuraciones_probadas"] == {"GridSearchCV": 46, "RandomizedSearchCV": 30},
   "la ruta prueba la rejilla completa y 30 configuraciones al azar")
ok(resultado["mejor"]["orden_promedio"] >= max(m["orden_promedio"] for m in resultado["mejores_por_modelo"]),
   "elige la configuración con mejor validación cruzada")
ok({"mejor", "app"} == set(resultado["prueba_final"]), "mide una vez en prueba la mejor y la de la app")
ok((optimizacion.CARPETA_CSV / f"optimizacion_usuario_{usuario_id}.csv").exists(), "exporta todas las configuraciones")
ok(cliente.get("/api/votos/optimizacion").status_code == 401, "la optimización pide sesión")

# ============================================================
# SEGMENTACION CON K-MEANS
# ============================================================
manchas = np.array([[0, 0], [0, 1], [1, 0], [10, 10], [10, 11], [11, 10]], dtype=float)
ok(segmentacion.ari(segmentacion.kmeans(manchas, 2)["etiquetas"], [0, 0, 0, 1, 1, 1]) == 1.0,
   "K-means encuentra dos grupos evidentes")
ok(abs(segmentacion.kmeans(manchas, 2)["inercia"] - 8 / 3) < 1e-9,
   "la inercia es la suma de distancias² a su centroide (WCSS): 4/3 por grupo")
ok(abs(segmentacion.silhouette(np.array([[0.0], [1.0], [10.0], [11.0]]), np.array([0, 0, 1, 1])) - 0.8997) < 1e-4,
   "silhouette calculado a mano como en scikit-learn")
ok(segmentacion.ari([0, 0, 1, 1], [1, 1, 0, 0]) == 1.0, "ARI ignora los números de grupo")
ok(segmentacion.ari([0, 0, 1, 1], [0, 0, 1, 2]) == 0.5714 and segmentacion.ari([0, 0, 0, 0], [0, 1, 2, 3]) == 0.0,
   "ARI con los valores de la documentación de scikit-learn")
escalado = segmentacion.estandarizar(np.array([[1.0, 10], [2, 20], [3, 30]]))
ok(np.allclose(escalado.mean(axis=0), 0) and np.allclose(escalado.std(axis=0), 1), "StandardScaler: media 0, desviación 1")
ok(np.allclose(segmentacion.min_max(np.array([[1.0], [3], [5]])).ravel(), [0, 0.5, 1]), "MinMaxScaler: de 0 a 1")

resultado = cliente.get("/api/prendas/segmentos", headers=encabezado).json()
ok(resultado["listo"] and sum(s["prendas"] for s in resultado["segmentos"]) == resultado["prendas"] == 6,
   "cada prenda queda en un segmento")
ok(resultado["k_elegido"] in [f["k"] for f in resultado["silhouette_por_k"]] and resultado["metodo_del_codo"][0]["k"] == 1,
   "reporta el codo y el silhouette de cada K")
ok((segmentacion.CARPETA_CSV / f"segmentos_prendas_usuario_{usuario_id}.csv").exists(), "exporta el segmento de cada prenda")
ok(cliente.get("/api/prendas/segmentos").status_code == 401, "la segmentación pide sesión")
vacia = {"Authorization": "Bearer " + cliente.post("/api/auth/registro", json={"correo": "vacia@prueba.com",
                                                                                "contraseña": "12345678"}).json()["token_acceso"]}
ok(cliente.get("/api/prendas/segmentos", headers=vacia).json()["listo"] is False, "sin prendas suficientes avisa")

# ============================================================
# VALIDACION DE SEGMENTOS Y ATIPICOS
# ============================================================
resultado = cliente.get("/api/prendas/segmentos/analisis", headers=encabezado).json()
ok(resultado["listo"] and len(resultado["estabilidad"]["comparaciones"]) == 15, "compara las 6 semillas de dos en dos (ARI)")
ok({"k-means++", "random", "ari_entre_las_dos"} <= set(resultado["inicializaciones"]), "compara k-means++ contra random")
ok({"StandardScaler", "MinMaxScaler", "ari_entre_los_dos"} == set(resultado["escaladores"]), "compara los dos escaladores")
ok(resultado["atipicos"]["percentil"] == 95, "los atípicos usan el percentil 95 de la distancia al centroide")
ok((analisis.CARPETA_CSV / f"analisis_segmentos_usuario_{usuario_id}.csv").exists(), "exporta el reporte integral")
ok(cliente.get("/api/prendas/segmentos/analisis").status_code == 401, "el análisis pide sesión")

# ============================================================
# PCA
# ============================================================
correlacionadas = segmentacion.estandarizar(np.array([[1.0, 2], [2, 4], [3, 6], [4, 8]]))
ok(abs(pca_prendas.pca(correlacionadas)["proporcion"][0] - 1) < 1e-9, "dos variables iguales: PC1 explica el 100 %")
aleatorio = segmentacion.estandarizar(np.random.default_rng(0).normal(size=(20, 4)))
componentes = pca_prendas.pca(aleatorio)["componentes"]
ok(np.allclose(pca_prendas.reconstruir(aleatorio, componentes, 4), aleatorio), "con todas las componentes no se pierde nada")
ok(np.allclose(componentes.T @ componentes, np.eye(4)), "las componentes no se correlacionan (son ortogonales)")
resultado = cliente.get("/api/prendas/pca", headers=encabezado).json()
ok(resultado["listo"] and resultado["varianza"][-1]["acumulada"] == 1.0 and len(resultado["coordenadas"]) == 6,
   "varianza acumulada hasta 100 % y coordenadas de cada prenda")
ok(resultado["error_de_reconstruccion"][-1]["mse"] == 0.0, "el error de reconstrucción con 4 componentes es 0")
ok((pca_prendas.CARPETA_CSV / f"pca_prendas_usuario_{usuario_id}.csv").exists(), "exporta coordenadas y reconstrucción")
ok(cliente.get("/api/prendas/pca").status_code == 401, "el PCA pide sesión")

# ============================================================
# LO QUE MUESTRA LA APP (pantalla Estadísticas: grupos, mapa y atípicos)
# ============================================================
resultado = cliente.get("/api/prendas/grupos", headers=encabezado).json()
ids = sorted(i for g in resultado["grupos"] for i in g["prendas"])
ok(resultado["listo"] and ids == sorted(p["id"] for p in resultado["mapa"]["puntos"]) == sorted(map(int, resultado["prendas"])),
   "cada prenda está en un grupo y en el mapa, con sus datos para la app")
tamaños = [len(g["prendas"]) for g in resultado["grupos"]]
ok([g["numero"] for g in resultado["grupos"]] == list(range(1, len(tamaños) + 1)) and tamaños == sorted(tamaños, reverse=True),
   "los grupos se numeran del más grande al más chico (cada número tiene su color en la app)")
ok(len(resultado["grupos"]) <= 4, "máximo 4 grupos: los que se distinguen por color en el mapa")
ok(all(item["id"] in ids for item in resultado["no_encajan"]), "las prendas que no encajan son del armario")
from limpieza_de_datos.grupos_del_armario import describir_eje  # noqa: E402
ok(describir_eje({"abrigo": 0.1, "tono": 0.7, "formalidad": -0.6, "neutro": 0.2})
   == {"positivo": "más oscuras y más casuales", "negativo": "más claras y más formales"},
   "cada eje del mapa se describe con las variables que más pesan")
ok(cliente.get("/api/prendas/grupos", headers=vacia).json() == {"listo": False, "minimo": 6, "prendas": 0},
   "sin prendas suficientes, la app avisa cuántas hacen falta")
ok(cliente.get("/api/prendas/grupos").status_code == 401, "los grupos piden sesión")

terminar()
