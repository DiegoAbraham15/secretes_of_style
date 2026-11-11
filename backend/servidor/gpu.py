"""Turno de la GPU y conexión con el motor del probador.

La laptop tiene una RTX 4050 de 6 GB: Gemma (Ollama, ~3.3 GB) y CatVTON (el motor, ~5.4 GB) no caben a la
vez. Quien va a usar la GPU toma el turno y antes saca al otro modelo:
  - ollama.preguntar toma el turno y le pide al motor que suelte CatVTON;
  - el probador toma el turno y le pide a Ollama que descargue a Gemma.
"""

import json
import os
import threading
import urllib.error
import urllib.request

from fastapi import HTTPException

URL_MOTOR = os.environ.get("MOTOR_URL", "http://127.0.0.1:8001")
AVISO_APAGADO = "El probador está apagado. Abre el motor (backend\\motor) e intenta de nuevo."

turno = threading.Lock()


def pedir_al_motor(ruta: str, datos: dict | None = None, espera: float = 300) -> dict:
    """Llama al motor por HTTP local. Si no responde, 503 con un aviso claro."""
    peticion = urllib.request.Request(
        f"{URL_MOTOR}{ruta}", data=json.dumps(datos or {}).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(peticion, timeout=espera) as respuesta:
            return json.load(respuesta)
    except urllib.error.HTTPError as error:  # el motor contestó con un error
        try:
            detalle = json.load(error).get("detail")
        except ValueError:
            detalle = None
        raise HTTPException(503, detalle or "El probador no pudo generar la imagen")
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        raise HTTPException(503, AVISO_APAGADO)


def liberar_motor():
    """Saca a CatVTON de la GPU. Si el motor está apagado no hay nada que liberar."""
    try:
        pedir_al_motor("/liberar", espera=15)
    except HTTPException:
        pass
