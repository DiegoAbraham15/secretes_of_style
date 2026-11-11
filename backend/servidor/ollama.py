"""Conexión con Ollama, el programa que corre los modelos de IA en la misma computadora que el servidor.

La usan vision.py (detectar la prenda en la foto) y explicacion.py (redactar por qué funciona un atuendo).
"""

import base64
import json
import os
import urllib.error
import urllib.request

from fastapi import HTTPException

from servidor import gpu

URL_OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELO = os.environ.get("MODELO_IA", "gemma3:4b")  # entiende imágenes y texto; un solo modelo en memoria
ESPERA_SEGUNDOS = 90  # la primera consulta tarda más: Ollama tiene que cargar el modelo
ESPERA_TURNO = 30  # si el probador tiene la GPU más tiempo, se avisa en vez de dejar esperando a la app
AVISO_OCUPADA = "La IA está ocupada vistiendo un look. Intenta en un minuto."


def preguntar(instrucciones: str, aviso: str, imagen: bytes | None = None, formato: dict | None = None,
              temperatura: float = 0) -> str:
    """Manda las instrucciones (y la foto, si hay) al modelo y devuelve su respuesta.

    formato: JSON schema para obligar al modelo a contestar con esa forma (salida estructurada).
    aviso: el mensaje del error 503 si Ollama no responde.
    """
    mensaje = {"role": "user", "content": instrucciones}
    if imagen:
        mensaje["images"] = [base64.b64encode(imagen).decode()]
    cuerpo = {"model": MODELO, "stream": False, "messages": [mensaje], "options": {"temperature": temperatura}}
    if formato:
        cuerpo["format"] = formato

    peticion = urllib.request.Request(
        f"{URL_OLLAMA}/api/chat", data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"}
    )
    # Gemma y CatVTON no caben juntos en la GPU: se espera el turno y se saca a CatVTON (ver gpu.py).
    if not gpu.turno.acquire(timeout=ESPERA_TURNO):
        raise HTTPException(503, AVISO_OCUPADA)
    try:
        gpu.liberar_motor()
        with urllib.request.urlopen(peticion, timeout=ESPERA_SEGUNDOS) as respuesta:
            return json.load(respuesta)["message"]["content"]
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError):
        # Ollama cerrado, modelo sin descargar, respuesta lenta o que no es JSON.
        raise HTTPException(503, aviso)
    finally:
        gpu.turno.release()


def descargar_modelo():
    """Saca a Gemma de la GPU (keep_alive 0) para dejarle espacio al probador. Si Ollama está cerrado, no pasa nada."""
    cuerpo = json.dumps({"model": MODELO, "keep_alive": 0}).encode()
    peticion = urllib.request.Request(f"{URL_OLLAMA}/api/generate", data=cuerpo, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(peticion, timeout=15).close()
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        pass
