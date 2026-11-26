"""Modo viaje: un look por día con el pronóstico del destino y la lista de lo que hay que empacar.

Usa lo mismo que los atuendos de hoy:
  1. Clima: el pronóstico diario de Open-Meteo (gratis, sin clave) pasa a hechos con la lógica proposicional
     (hechos_del_clima y razonar_clima de logica.py), igual que el clima del momento en clima.py.
  2. Cada día, A* (busqueda.py) arma los 3 mejores looks con cada parte de arriba disponible como base.
  3. Esos candidatos se ordenan con los gustos de la persona (reordenar: perceptrón, parecido y CNN).
  4. Para que la maleta no sea el mismo look 5 veces, cada parte de arriba o de abajo que ya salió en un día
     anterior cuesta REPETIR de más. Zapatos, abrigo y accesorios al revés: repetirlos no cuesta, y lo que
     cuesta (EMPACAR_OTRA) es llevar otro par cuando ya va uno, como en una maleta real.
Nada se guarda en la base (salvo el pronóstico en la caché de climas) ni cuenta como voto.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from fastapi import HTTPException

from servidor import colorimetria
from servidor.aprendizaje import AJUSTE_MAXIMO, reordenar
from servidor.base_datos import bd
from servidor.busqueda import recomendar
from servidor.clima import URL_OPEN_METEO, describir_codigo
from servidor.logica import hechos_de_ocasion, hechos_del_clima, razonar_clima
from servidor.red_convolucional import probabilidades

URL_LUGARES = "https://geocoding-api.open-meteo.com/v1/search"
DIAS_DE_PRONOSTICO = 16  # hoy y los 15 días siguientes: lo que pide pronostico_diario a Open-Meteo
HORAS_DE_CACHE = 3  # el pronóstico de varios días cambia poco en unas horas
# Costo extra por cada parte de arriba o de abajo que ya salió en el viaje. Es la mayor diferencia que pueden hacer
# los gustos (±AJUSTE_MAXIMO): así repetir pierde contra cualquier preferencia, pero no contra el clima (+3) ni
# la ocasión (+20). Con 1.0, la CNN prefería repetir la misma playera dos días seguidos.
REPETIR = 2 * AJUSTE_MAXIMO
# Zapatos, abrigo y accesorios se pueden repetir; lo que cuesta es meter OTRO a la maleta cuando ya va uno de esa
# categoría (medio rango de los gustos: un par nuevo solo entra si gusta bastante más o va mejor con el clima).
SE_REPITE_SIN_COSTO = {"calzado", "abrigo", "accesorio"}
EMPACAR_OTRA = AJUSTE_MAXIMO
# Looks que A* propone con cada base: con uno solo no habría "el mismo look pero con los zapatos que ya van".
CANDIDATOS_POR_BASE = 3
ORDEN_MALETA = ["abrigo", "parte_superior", "parte_inferior", "calzado", "accesorio"]


def consultar(url: str, parametros: dict) -> dict:
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(parametros)}", timeout=10) as respuesta:
        return json.load(respuesta)


# ------------------------------------------------
# 1. EL DESTINO Y SU PRONÓSTICO
# ------------------------------------------------

def buscar_lugares(nombre: str) -> list[dict]:
    """Ciudades que se llaman así (geocodificación de Open-Meteo), para elegir el destino."""
    try:
        datos = consultar(URL_LUGARES, {"name": nombre, "count": 5, "language": "es", "format": "json"})
    except (urllib.error.URLError, TimeoutError):
        raise HTTPException(502, "No se pudo buscar el lugar")
    return [{"nombre": r["name"], "region": r.get("admin1"), "pais": r.get("country"),
             "latitud": r["latitude"], "longitud": r["longitude"]} for r in datos.get("results", [])]


def pronostico_diario(latitud: float, longitud: float) -> dict:
    """16 días de pronóstico. Se guarda en climas (como clima.py) y se reutiliza unas horas; sin red, el último."""
    clave = f"dias:{round(latitud, 2)},{round(longitud, 2)}"
    guardado = bd().climas.find_one({"_id": clave})
    if guardado and time.time() - guardado["consultado"] < HORAS_DE_CACHE * 3600:
        return guardado["reporte"]
    try:
        datos = consultar(URL_OPEN_METEO, {
            "latitude": latitud, "longitude": longitud, "forecast_days": DIAS_DE_PRONOSTICO, "timezone": "auto",
            "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,"
                     "precipitation_probability_max,weather_code",
        })
    except (urllib.error.URLError, TimeoutError):
        if guardado:
            return guardado["reporte"]
        raise HTTPException(502, "No se pudo consultar el pronóstico")
    reporte = datos["daily"]
    bd().climas.replace_one({"_id": clave}, {"consultado": time.time(), "reporte": reporte}, upsert=True)
    return reporte


def clima_del_dia(pronostico: dict, i: int) -> tuple[dict, set[str]]:
    """El clima de un día para la app y sus hechos. La sensación del día es el promedio de la máxima y la mínima."""
    sensacion = (pronostico["apparent_temperature_max"][i] + pronostico["apparent_temperature_min"][i]) / 2
    lluvia = pronostico["precipitation_probability_max"][i] or 0
    codigo = pronostico["weather_code"][i] or 0
    hechos, deducciones = razonar_clima(hechos_del_clima(sensacion, lluvia, codigo))
    clima = {
        "fecha": pronostico["time"][i],
        "maxima_c": pronostico["temperature_2m_max"][i],
        "minima_c": pronostico["temperature_2m_min"][i],
        "probabilidad_lluvia": lluvia,
        "descripcion": describir_codigo(codigo),
        "hechos": sorted(hechos),
        "deducciones": deducciones,
    }
    return clima, hechos


# ------------------------------------------------
# 2. UN LOOK POR DÍA Y LA MALETA
# ------------------------------------------------

def look_del_dia(armario: list[dict], hechos: set[str], usadas: dict[int, int], gustos: dict,
                 maleta: bool = True) -> tuple[dict | None, list[str]]:
    """El mejor look del día: A* con cada parte de arriba como base, ordenado por gustos y castigando repetir.

    usadas: prenda_id → cuántas veces ya salió (en el viaje, o en los últimos días para el look de hoy).
    maleta: False en el look de hoy, donde ponerse otros zapatos no cuesta nada (no hay que cargarlos).
    """
    candidatos, avisos = [], {}
    for base in [p for p in armario if p["categoria"] == "parte_superior" and p["estado"] == "disponible"]:
        resultado = recomendar(base, armario, hechos, cantidad=CANDIDATOS_POR_BASE, con_accesorio=gustos["con_accesorio"])
        candidatos += resultado["sugerencias"]
        avisos[base["id"]] = resultado["avisos"]  # p. ej. "no tienes un abrigo que combine"
    if not candidatos:
        return None, ["No hay un look completo con lo disponible: agrega o libera prendas"]

    cnn = probabilidades([[e["prenda"] for e in c["elementos"]] for c in candidatos], gustos["preferencias"])
    candidatos = reordenar(candidatos, gustos["pesos"], gustos["votos"], gustos["gustados"], cnn)
    candidatos = colorimetria.ajustar(candidatos, gustos.get("colorimetria"))  # colores que le favorecen
    por_id = {p["id"]: p for p in armario}
    en_maleta = {por_id[i]["categoria"] for i in usadas if i in por_id}  # categorías que ya llevan algo
    for c in candidatos:
        prendas = [e["prenda"] for e in c["elementos"]]
        repetidas = sum(usadas.get(p["id"], 0) for p in prendas if p["categoria"] not in SE_REPITE_SIN_COSTO)
        otras = maleta * sum(1 for p in prendas if p["categoria"] in SE_REPITE_SIN_COSTO & en_maleta and p["id"] not in usadas)
        c["costo_viaje"] = c["costo_final"] + REPETIR * repetidas + EMPACAR_OTRA * otras
    elegido = min(candidatos, key=lambda c: c["costo_viaje"])  # en empate gana el que reordenar puso primero
    # Aquí nadie eligió la base: A* la tomó de las partes de arriba.
    avisos_del_look = [a.replace("La prenda base", "La parte de arriba") for a in avisos[elegido["elementos"][0]["prenda"]["id"]]]
    return elegido, [a.replace("de hoy", "de ese día") for a in avisos_del_look] if maleta else avisos_del_look


def planear(armario: list[dict], latitud: float, longitud: float, lugar: str, salida: int, dias: int,
            ocasion: str, gustos: dict) -> dict:
    """gustos: pesos, votos (firma → ±1), gustados, preferencias y con_accesorio, como en las recomendaciones."""
    pronostico = pronostico_diario(latitud, longitud)
    usadas: dict[int, int] = {}
    maleta: dict[int, dict] = {}
    plan = []
    for numero, i in enumerate(range(salida, salida + dias), start=1):
        clima, hechos = clima_del_dia(pronostico, i)
        sugerencia, avisos = look_del_dia(armario, hechos | hechos_de_ocasion(ocasion), usadas, gustos)
        if sugerencia:
            for e in sugerencia["elementos"]:
                prenda = e["prenda"]
                usadas[prenda["id"]] = usadas.get(prenda["id"], 0) + 1
                maleta.setdefault(prenda["id"], {"prenda": prenda, "dias": []})["dias"].append(numero)
        plan.append({"dia": numero, "clima": clima, "sugerencia": sugerencia, "avisos": avisos})
    return {
        "lugar": lugar,
        "ocasion": ocasion,
        "dias": plan,
        "maleta": sorted(maleta.values(), key=lambda m: (ORDEN_MALETA.index(m["prenda"]["categoria"]), m["dias"][0])),
    }
