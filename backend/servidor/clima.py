"""Consulta real del clima en Open-Meteo (gratis, sin clave) y su traducción a hechos."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from fastapi import HTTPException

from servidor.base_datos import consultar_uno, ejecutar
from servidor.logica import hechos_del_clima, razonar_clima

URL_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
MINUTOS_DE_CACHE = 30


def describir_codigo(codigo: int) -> str:
    """Descripción en español de los códigos WMO que usa Open-Meteo."""
    for maximo, descripcion in [(0, "Despejado"), (3, "Nublado"), (48, "Niebla"), (67, "Lluvia"),
                                (77, "Nieve"), (86, "Chubascos")]:
        if codigo <= maximo:
            return descripcion
    return "Tormenta"


def obtener_clima(latitud: float, longitud: float) -> dict:
    # Cada consulta se guarda en la base por coordenadas redondeadas (~1 km): se reutiliza 30 min
    # y, si Open-Meteo no responde, se usa la última aunque sea más vieja.
    clave = f"{round(latitud, 2)},{round(longitud, 2)}"
    guardado = consultar_uno("SELECT consultado, reporte FROM climas WHERE clave = ?", (clave,))
    if guardado and time.time() - guardado["consultado"] < MINUTOS_DE_CACHE * 60:
        return json.loads(guardado["reporte"])

    parametros = urllib.parse.urlencode({
        "latitude": latitud,
        "longitude": longitud,
        "current": "temperature_2m,apparent_temperature,weather_code",
        "hourly": "precipitation_probability",
        "forecast_hours": 6,
        "timezone": "auto",
    })
    try:
        with urllib.request.urlopen(f"{URL_OPEN_METEO}?{parametros}", timeout=10) as respuesta:
            datos = json.load(respuesta)
    except (urllib.error.URLError, TimeoutError):
        if guardado:
            minutos = round((time.time() - guardado["consultado"]) / 60)
            return {**json.loads(guardado["reporte"]), "minutos_desactualizado": minutos}
        raise HTTPException(502, "No se pudo consultar el clima")

    actual = datos["current"]
    # Mayor probabilidad de lluvia de las próximas 6 horas.
    probabilidad_lluvia = max(p or 0 for p in datos["hourly"]["precipitation_probability"])

    # Mediciones → proposiciones → deducciones con las reglas.
    hechos = hechos_del_clima(actual["apparent_temperature"], probabilidad_lluvia, actual["weather_code"])
    hechos, deducciones = razonar_clima(hechos)

    reporte = {
        "temperatura_c": actual["temperature_2m"],
        "sensacion_termica_c": actual["apparent_temperature"],
        "probabilidad_lluvia": probabilidad_lluvia,
        "descripcion": describir_codigo(actual["weather_code"]),
        "hechos": sorted(hechos),
        "deducciones": deducciones,
    }
    ejecutar(
        "INSERT OR REPLACE INTO climas (clave, consultado, reporte) VALUES (?, ?, ?)",
        (clave, time.time(), json.dumps(reporte)),
    )
    return reporte
