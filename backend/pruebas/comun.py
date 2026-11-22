"""Lo que comparten todas las pruebas del backend.

Uso, al principio de cada prueba y ANTES de importar servidor.principal:
    sys.path.insert(0, <carpeta backend>)
    from pruebas.comun import ok, preparar, terminar
    temporal = preparar()
    ...
    terminar()

preparar() deja todo en lugares temporales: una base de MongoDB que se borra al terminar y carpetas de
archivos aparte, así las pruebas nunca tocan la base secrets_of_style ni las fotos reales.
"""

import os
import struct
import sys
import tempfile
import zlib
from pathlib import Path

fallas = 0


def preparar() -> Path:
    """Clave de sesión fija, base de MongoDB temporal y carpetas temporales. Devuelve la carpeta temporal."""
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba"  # antes de importar seguridad.py, que la lee al cargarse
    temporal = Path(tempfile.mkdtemp())
    from servidor import base_datos

    base_datos.usar_base_de_prueba()
    os.environ.pop("GOOGLE_VISION_CLAVE", None)  # base_datos leyó el .env: las pruebas nunca mandan fotos a Google
    base_datos.CARPETA_ARCHIVOS = temporal / "archivos"
    base_datos.CARPETA_PRIVADA = temporal / "privado"
    return temporal


def ok(condicion, mensaje: str) -> None:
    """Anota un caso: OK o FALLA. Las fallas se cuentan para el código de salida."""
    global fallas
    fallas += not condicion
    print(("OK   " if condicion else "FALLA"), mensaje)


def terminar() -> None:
    """Imprime el total y sale con código 1 si algo falló (así un script o CI lo detecta)."""
    print(f"\nFALLAS: {fallas}")
    sys.exit(1 if fallas else 0)


def png_de_color(rojo: int = 200, verde: int = 50, azul: int = 50, lado: int = 64) -> bytes:
    """Un PNG de un solo color, armado a mano para no depender de Pillow."""
    def bloque(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))
    fila = b"\x00" + bytes([rojo, verde, azul]) * lado
    return (b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", lado, lado, 8, 2, 0, 0, 0))
            + bloque(b"IDAT", zlib.compress(fila * lado)) + bloque(b"IEND", b""))
