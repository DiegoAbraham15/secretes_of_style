"""Comprueba la limpieza de datos de los votos antes de entrenar al perceptrón.
Ejecutar desde la carpeta backend: .venv\\Scripts\\python limpieza_de_datos\\prueba_limpieza_de_datos.py"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["CLAVE_SECRETA"] = "clave-de-prueba"
# La carpeta de este archivo se cambia por backend: si no, "limpieza_de_datos" sería el archivo .py de al lado
# y no la carpeta, y fallaría el import de principal.py.
sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
temporal = Path(tempfile.mkdtemp())

from servidor import base_datos  # noqa: E402

base_datos.RUTA_BD = temporal / "prueba.db"
base_datos.CARPETA_ARCHIVOS = temporal / "archivos"

from fastapi.testclient import TestClient  # noqa: E402
from servidor import principal  # noqa: E402
from servidor.aprendizaje import caracteristicas_de, puntuar  # noqa: E402
from limpieza_de_datos import limpieza_de_datos as limpieza  # noqa: E402
from limpieza_de_datos.limpieza_de_datos import CARACTERISTICAS, limpiar_votos  # noqa: E402

limpieza.CARPETA_CSV = temporal / "datos"  # los CSV de la prueba no van a la carpeta real

fallas = 0


def ok(cond, msg):
    global fallas
    fallas += not cond
    print(("OK   " if cond else "FALLA"), msg)


def prenda(id, categoria, color, estilo="casual"):
    return {"id": id, "categoria": categoria, "color_principal": color, "nivel_abrigo": 2, "impermeable": False,
            "estado": "disponible", "subcategoria": None, "estampado": "liso", "estilo": estilo}


def voto(firma, me_gusta, prendas):
    return {"firma": firma, "me_gusta": me_gusta, "caracteristicas": caracteristicas_de(prendas)}


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

# --- Fila duplicada: como en la práctica, drop_duplicates la elimina ---
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
    base_datos.ejecutar("INSERT INTO votos_atuendo (usuario_id, firma, me_gusta, caracteristicas) VALUES (?, ?, ?, ?)",
                        (usuario_id, firma, me_gusta, principal.json.dumps(caracteristicas_de(prendas))))

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

limpieza_de_prendas.CARPETA_CSV = temporal / "datos"
evaluacion.CARPETA_CSV = temporal / "datos"
carpeta_prendas = base_datos.CARPETA_ARCHIVOS / "prendas"
carpeta_prendas.mkdir(parents=True, exist_ok=True)
fotos = {"roja": ((600, 800), (200, 20, 30)), "chica": ((200, 200), (30, 40, 200)),
         "gris": ((600, 800), (128, 128, 128)), "roja_intensa": ((600, 800), (230, 0, 20))}
for nombre, (tamaño, color) in fotos.items():
    Image.new("RGB", tamaño, color).save(carpeta_prendas / f"{nombre}.jpg")
(carpeta_prendas / "copia.jpg").write_bytes((carpeta_prendas / "roja.jpg").read_bytes())  # la misma foto


def nueva_prenda(foto, color, subcategoria=None, categoria="parte_superior"):
    base_datos.ejecutar(
        "INSERT INTO prendas (usuario_id, url_imagen, categoria, subcategoria, color_principal, nivel_abrigo, impermeable, "
        "estado, fecha_creacion) VALUES (?, ?, ?, ?, ?, 2, 0, 'disponible', CURRENT_TIMESTAMP)",
        (usuario_id, f"/archivos/prendas/{foto}.jpg", categoria, subcategoria, color))
    return base_datos.consultar_uno("SELECT MAX(id) AS id FROM prendas")["id"]


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
# EVALUACION DEL MODELO (práctica 3)
# ============================================================
real = limpieza.pd.Series([1, 1, 0, 0, 0])
m = evaluacion.metricas(real, limpieza.pd.Series([1, 0, 1, 0, 0]), limpieza.pd.Series([0.9, 0.1, 0.5, 0.2, 0.0]))
ok(m["matriz"] == [[2, 1], [1, 1]] and m["exactitud"] == 0.6 and m["precision"] == 0.5 and m["recall"] == 0.5,
   "métricas calculadas a mano como en la práctica")
ok(m["orden"] == round(4 / 6, 3), "orden: 4 de 6 pares (corazón, sin corazón) quedan bien")
ok(evaluacion.orden(real, limpieza.pd.Series([1.0] * 5)) == 0.5, "si todo empata, el orden es 0.5 (azar)")
datos = limpieza.pd.DataFrame({"me_gusta": [1] * 10 + [0] * 30})
entrenamiento, prueba = evaluacion.dividir(datos, 42)
ok(len(prueba) == 12 and prueba["me_gusta"].sum() == 3 and len(entrenamiento) == 28, "la división conserva la proporción (stratify)")

ok(cliente.get("/api/votos/evaluacion", headers=encabezado).json()["listo"] is False, "con pocos votos avisa que falta")
casual2 = [prenda(8, "parte_superior", "rojo"), prenda(9, "parte_inferior", "verde"), prenda(10, "calzado", "rojo")]
looks = [("a", 1, formal), ("b", 1, formal), ("c", -1, casual), ("d", -1, casual), ("e", -1, casual2), ("f", -1, casual2),
         ("g", -1, casual), ("h", -1, casual2)]
base_datos.ejecutar("DELETE FROM votos_atuendo WHERE usuario_id = ?", (usuario_id,))
for firma, me_gusta, prendas in looks:
    base_datos.ejecutar("INSERT INTO votos_atuendo (usuario_id, firma, me_gusta, caracteristicas) VALUES (?, ?, ?, ?)",
                        (usuario_id, firma, me_gusta, principal.json.dumps(caracteristicas_de(prendas))))
resultado = cliente.get("/api/votos/evaluacion", headers=encabezado).json()
ok(resultado["listo"] and resultado["datos"]["votos_validos"] == 8, "evalúa con los votos limpios")
ok(set(resultado["una_division"]) == {"siempre_no", "regla_fija", "perceptron", "parecido", "sistema_actual"},
   "compara los cinco sistemas")
ok(resultado["promedio_20_divisiones"]["parecido"]["orden"] == 1.0, "el parecido reconoce un look idéntico al del corazón")
ok((evaluacion.CARPETA_CSV / f"evaluacion_usuario_{usuario_id}.csv").exists(), "exporta la comparación voto por voto")
ok(cliente.get("/api/votos/evaluacion").status_code == 401, "la evaluación pide sesión")

print(f"\nFALLAS: {fallas}")
sys.exit(1 if fallas else 0)
