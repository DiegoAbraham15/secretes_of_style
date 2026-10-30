"""Conexión con Ollama, el programa que corre los modelos de IA en la misma computadora que el servidor.

La usan vision.py (detectar la prenda en la foto) y explicacion.py (redactar por qué funciona un atuendo).
"""

import base64
import json
import os
import urllib.error
import urllib.request

from fastapi import HTTPException

URL_OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELO = os.environ.get("MODELO_IA", "gemma3:4b")  # entiende imágenes y texto; un solo modelo en memoria
ESPERA_SEGUNDOS = 90  # la primera consulta tarda más: Ollama tiene que cargar el modelo


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
    try:
        with urllib.request.urlopen(peticion, timeout=ESPERA_SEGUNDOS) as respuesta:
            return json.load(respuesta)["message"]["content"]
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError):
        # Ollama cerrado, modelo sin descargar, respuesta lenta o que no es JSON.
        raise HTTPException(503, aviso)
