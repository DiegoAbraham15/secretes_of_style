"""Las fotos que sube la app: revisar que sean imágenes de verdad, guardarlas y borrarlas.

Viven aquí (y no en principal.py) porque también las usa digitalizar.py, que principal importa.
La carpeta se lee de base_datos en cada llamada: las pruebas la cambian por una temporal.
"""

import uuid

from fastapi import HTTPException

from servidor import base_datos

MARCAS_HEIC = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}
MAXIMO_IMAGEN_MB = 8


def extension_de_imagen(contenido: bytes) -> str | None:
    """Extensión según los primeros bytes del archivo (su firma), sin confiar en el nombre que manda la app."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return ".webp"
    if contenido[4:8] == b"ftyp" and contenido[8:12] in MARCAS_HEIC:
        return ".heic"
    return None


def revisar_imagen(contenido: bytes) -> str:
    """Rechaza archivos muy pesados o que no son imagen; devuelve la extensión."""
    if len(contenido) > MAXIMO_IMAGEN_MB * 1024 * 1024:
        raise HTTPException(413, f"La imagen supera {MAXIMO_IMAGEN_MB} MB")
    extension = extension_de_imagen(contenido)
    if extension is None:
        raise HTTPException(415, "El archivo no es una imagen JPG, PNG, WEBP o HEIC.")
    return extension


def ruta_de(ruta_publica: str):
    """/archivos/prendas/abc.jpg → la ruta en disco."""
    return base_datos.CARPETA_ARCHIVOS / ruta_publica.removeprefix("/archivos/")


def guardar_imagen(contenido: bytes, extension: str, carpeta: str) -> str:
    """Guarda la imagen en disco y devuelve su ruta pública, p. ej. /archivos/prendas/abc.jpg."""
    nombre = f"{uuid.uuid4().hex}{extension}"
    (base_datos.CARPETA_ARCHIVOS / carpeta).mkdir(parents=True, exist_ok=True)
    (base_datos.CARPETA_ARCHIVOS / carpeta / nombre).write_bytes(contenido)
    return f"/archivos/{carpeta}/{nombre}"


def borrar_imagen(ruta_publica: str | None):
    if ruta_publica:
        ruta_de(ruta_publica).unlink(missing_ok=True)
