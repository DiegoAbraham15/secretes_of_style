"""Comprueba la colorimetría personal (colorimetria.py): reglas de estación, cuestionario, selfie (motor simulado),
la insignia en los looks, priorizar la paleta y la línea en "¿Vale la pena?".
Ejecutar desde la carpeta backend: .venv\\Scripts\\python pruebas\\prueba_colorimetria.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pruebas.comun import ok, preparar, terminar  # noqa: E402

temporal = preparar()

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pruebas.comun import png_de_color  # noqa: E402
from servidor import base_datos, colorimetria as co, gpu, principal  # noqa: E402

# --- 1. Reglas ---
ok(co.estacion_de("calido", "claro", "medio") == "primavera" and co.estacion_de("calido", "profundo", "alto") == "otono",
   "cálido: claro → Primavera, profundo → Otoño")
ok(co.estacion_de("frio", "claro", "bajo") == "verano" and co.estacion_de("frio", "medio", "alto") == "invierno",
   "frío: suave → Verano, contraste alto → Invierno")
ok(co.estacion_de("neutro", "medio", "alto") == "invierno" and co.estacion_de("neutro", "profundo", "medio") == "otono"
   and co.estacion_de("neutro", "claro", "bajo") == "verano" and co.estacion_de("neutro", "medio", "medio") == "primavera",
   "neutro: lo decide el contraste y la profundidad")

calida_clara = {"venas": "verde", "sol": "se_quema", "metales": "oro", "cabello": "claro", "contraste": "bajo"}
fria_alta = {"venas": "azul", "sol": "se_quema", "metales": "plata", "cabello": "oscuro", "contraste": "alto"}
calida_profunda = {"venas": "verde", "sol": "se_broncea", "metales": "oro", "cabello": "oscuro", "contraste": "medio"}
fria_suave = {"venas": "azul", "sol": "ambas", "metales": "plata", "cabello": "castano", "contraste": "bajo"}
for respuestas, esperada in ((calida_clara, "primavera"), (fria_alta, "invierno"), (calida_profunda, "otono"), (fria_suave, "verano")):
    d = co.diagnosticar(respuestas, None)
    ok(d["estacion"] == esperada and d["metodo"] == "cuestionario", f"cuestionario → {esperada} ({d['estacion']}, {d['subtono']})")
d = co.diagnosticar(calida_clara, None)
ok("amarillo" in d["paleta"] and "negro" in d["evitar"] and len(d["paleta_hex"]) == 12, "la paleta y los colores a evitar")

piel_dorada = {"piel": {"lab": [72, 12, 24], "hex": "#E0B48C"}, "cabello": {"lab": [60, 8, 20], "hex": "#B08050"}}
piel_rosada_oscuro = {"piel": {"lab": [68, 18, 12], "hex": "#E0A898"}, "cabello": {"lab": [12, 2, 2], "hex": "#1E1A1A"}}
m = co.medidas_de_selfie(piel_dorada)
ok(m["subtono"] == "calido" and m["profundidad"] == "claro" and m["contraste"] == "bajo", f"selfie dorada y clara: {m}")
m = co.medidas_de_selfie(piel_rosada_oscuro)
ok(m["subtono"] == "frio" and m["contraste"] == "alto", f"selfie rosada con cabello negro: {m}")
ok(co.diagnosticar(None, piel_rosada_oscuro)["estacion"] == "invierno", "solo con selfie también hay estación")
d = co.diagnosticar(calida_profunda, piel_rosada_oscuro)
ok(d["metodo"] == "ambos" and d["subtono"] == "neutro", "la selfie pesa el doble: cálido (+6) y frío (−4·2) → casi neutro")
ok(co.medidas_de_selfie({"piel": {"lab": [60, 15, 20]}, "cabello": None})["contraste"] == "medio", "sin cabello visible: contraste medio")

# --- 2. La insignia y priorizar ---
perfil = {**co.diagnosticar(fria_alta, None), "priorizar": True}  # Invierno: negro sí, beige no
arriba = lambda color: {"categoria": "parte_superior", "color_principal": color}  # noqa: E731
abajo = {"categoria": "parte_inferior", "color_principal": "beige"}
look_beige = {"elementos": [{"prenda": arriba("beige")}, {"prenda": abajo}], "costo": 5, "costo_final": 4.0}
look_negro = {"elementos": [{"prenda": arriba("negro")}, {"prenda": abajo}], "costo": 5, "costo_final": 4.5}
ordenados = co.ajustar([look_beige, look_negro], perfil)
ok(ordenados[0] is look_negro and look_negro["colorimetria"]["nivel"] == "favorece"
   and look_beige["colorimetria"]["nivel"] == "evitar", "con priorizar, el look con su paleta cerca del rostro sube")
ok("abajo" not in str(look_beige["colorimetria"]) and co.marca_de([abajo], perfil)[1] == 0,
   "la parte de abajo no cuenta: el color se ve cerca del rostro")
look_a = {"elementos": [{"prenda": arriba("beige")}], "costo": 5, "costo_final": 4.0}
look_b = {"elementos": [{"prenda": arriba("negro")}], "costo": 5, "costo_final": 4.5}
ok(co.ajustar([look_a, look_b], {**perfil, "priorizar": False})[0] is look_a and "colorimetria" in look_a,
   "sin priorizar solo se marca, no se reordena")
ok(co.ajustar([look_a], None) == [look_a], "sin diagnóstico no cambia nada")

# --- 3. La API ---
medidas_motor = {"valida": True, **piel_rosada_oscuro}
pedidas = []


def motor_falso(ruta, datos=None, espera=0):
    pedidas.append((ruta, datos))
    return medidas_motor


gpu.pedir_al_motor = motor_falso
principal.obtener_clima = lambda lat, lon: {"temperatura_c": 20, "sensacion_termica_c": 20, "probabilidad_lluvia": 0,
                                            "descripcion": "Despejado", "hechos": [], "deducciones": []}

with TestClient(principal.aplicacion) as cliente:
    def cuenta(correo):
        r = cliente.post("/api/auth/registro", json={"correo": correo, "contraseña": "contraseña-larga"})
        return {"Authorization": f"Bearer {r.json()['token_acceso']}"}

    h, otra = cuenta("color@prueba.com"), cuenta("otra-color@prueba.com")
    preguntas = cliente.get("/api/colorimetria/preguntas", headers=h).json()
    ok(len(preguntas) == 5 and all("hex" in o and "puntos" not in o for p in preguntas for o in p["opciones"]),
       "5 preguntas con muestras de color (sin los puntos)")
    ok(cliente.get("/api/colorimetria", headers=h).json() is None, "sin diagnóstico: null")
    ok(cliente.post("/api/colorimetria/cuestionario", headers=h, json={"respuestas": {"venas": "verde"}}).status_code == 422,
       "faltan respuestas: 422")
    ok(cliente.post("/api/colorimetria/cuestionario", headers=h, json={"respuestas": {**fria_alta, "venas": "rojas"}})
       .status_code == 422, "una opción que no existe: 422")
    r = cliente.post("/api/colorimetria/cuestionario", headers=h, json={"respuestas": fria_alta})
    ok(r.status_code == 200 and r.json()["estacion"] == "invierno" and r.json()["priorizar"], "el cuestionario da Invierno")
    guardado = base_datos.bd().usuarios.find_one({"correo": "color@prueba.com"})["colorimetria"]
    ok(guardado["respuestas"] == fria_alta and guardado["selfie"] is None, "se guardan las respuestas, no los puntos")

    r = cliente.post("/api/colorimetria/selfie", headers=h, files={"imagen": ("s.png", png_de_color(220, 180, 160), "image/png")})
    ok(r.status_code == 200 and r.json()["metodo"] == "ambos" and pedidas[-1][0] == "/colorimetria",
       "la selfie se combina con el cuestionario")
    selfies = base_datos.CARPETA_PRIVADA / "selfies"
    ok(not selfies.exists() or not any(selfies.iterdir()), "la selfie se borra en cuanto se mide")
    ok("hex" in base_datos.bd().usuarios.find_one({"correo": "color@prueba.com"})["colorimetria"]["selfie"]["piel"],
       "solo se guardan los colores medidos")
    medidas_motor = {"valida": False, "motivo": "No se ve bien tu rostro."}
    r = cliente.post("/api/colorimetria/selfie", headers=h, files={"imagen": ("s.png", png_de_color(), "image/png")})
    ok(r.status_code == 422 and "rostro" in r.json()["detail"], "sin rostro: 422 con qué hacer")
    gpu.pedir_al_motor = lambda *a, **k: (_ for _ in ()).throw(HTTPException(503, "El probador está apagado"))
    ok(cliente.post("/api/colorimetria/selfie", headers=h, files={"imagen": ("s.png", png_de_color(), "image/png")})
       .status_code == 503, "motor apagado: 503 (queda el cuestionario)")
    ok(cliente.post("/api/colorimetria/selfie", headers=h, data={"usar_foto_probador": "true"}).status_code == 409,
       "usar la foto del probador sin haberla subido: 409")
    ok(cliente.post("/api/colorimetria/selfie", headers=h).status_code == 422, "sin foto: 422")

    ok(cliente.patch("/api/colorimetria", headers=h, json={"priorizar": False}).json()["priorizar"] is False, "apagar priorizar")
    ok(cliente.patch("/api/colorimetria", headers=otra, json={"priorizar": True}).status_code == 404,
       "priorizar sin diagnóstico: 404")
    ok(cliente.get("/api/colorimetria", headers=otra).json() is None, "cada quien su diagnóstico")

    # La insignia en las recomendaciones y en "¿Vale la pena?"
    def subir(categoria, color):
        return cliente.post("/api/prendas", headers=h, data={"categoria": categoria, "color_principal": color, "nivel_abrigo": "2"},
                            files={"imagen": ("p.png", png_de_color(), "image/png")}).json()["id"]

    base = subir("parte_superior", "negro")
    subir("parte_inferior", "gris"), subir("calzado", "negro")
    r = cliente.post("/api/recomendaciones", headers=h, json={"prenda_base_id": base, "latitud": 19.4, "longitud": -99.1})
    ok(r.json()["sugerencias"][0]["colorimetria"]["nivel"] == "favorece", "los looks traen su insignia de color")
    r = cliente.post("/api/recomendaciones/dia", headers=h, json={"latitud": 19.4, "longitud": -99.1})
    ok("colorimetria" in r.json()["sugerencias"][0], "también el look del día")
    principal.detectar_para_tienda = lambda contenido: {"categoria": "parte_superior", "subcategoria": "Blusa",
                                                        "color_principal": "beige", "estampado": "liso", "estilo": "casual"}
    deseo = cliente.post("/api/deseos", headers=h, files={"imagen": ("t.png", png_de_color(), "image/png")}).json()
    a = cliente.get(f"/api/deseos/{deseo['id']}/vale-la-pena", headers=h).json()
    ok(a["colorimetria"]["nivel"] == "evitar" and "Invierno" in a["colorimetria"]["texto"],
       "¿Vale la pena? dice si el color te favorece")

    ok(cliente.delete("/api/colorimetria", headers=h).status_code == 204 and cliente.get("/api/colorimetria", headers=h).json() is None,
       "borrar el diagnóstico")
    r = cliente.post("/api/recomendaciones", headers=h, json={"prenda_base_id": base, "latitud": 19.4, "longitud": -99.1})
    ok("colorimetria" not in r.json()["sugerencias"][0], "sin diagnóstico, los looks no llevan insignia")
    ok(cliente.get("/api/colorimetria").status_code == 401, "pide sesión")

terminar()
