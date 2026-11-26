"""Deja todas las fotos de ejemplo con el mismo fondo: quita el fondo (U2-Net, como el motor del probador) y centra la
prenda sobre un lienzo cuadrado blanco, con el mismo margen, para que se vean parejas como las que ya están cargadas.

Se corre con el Python del motor (tiene rembg y el modelo u2net):
    backend\\motor\\.venv\\Scripts\\python backend\\ejemplos\\preparar_fotos.py originales fotos

  originales   carpeta con las fotos tal como se bajaron (jpg o png)
  fotos        carpeta de salida: una .jpg de 900 x 900 por foto
"""

import sys
from pathlib import Path

from PIL import Image, ImageOps
from rembg import new_session, remove

LADO = 900  # lienzo cuadrado
MARGEN = 0.08  # espacio blanco alrededor de la prenda, como proporción del lado
FONDO = (255, 255, 255)


def preparar(origen: Path, destino: Path, sesion) -> None:
    foto = ImageOps.exif_transpose(Image.open(origen)).convert("RGB")
    recortada = remove(foto, session=sesion)  # RGBA: la prenda sin fondo
    caja = recortada.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox()
    if caja is None:
        raise ValueError("no se encontró la prenda")
    prenda = recortada.crop(caja)
    maximo = int(LADO * (1 - 2 * MARGEN))
    prenda.thumbnail((maximo, maximo), Image.LANCZOS)
    lienzo = Image.new("RGB", (LADO, LADO), FONDO)
    lienzo.paste(prenda, ((LADO - prenda.width) // 2, (LADO - prenda.height) // 2), prenda.getchannel("A"))
    lienzo.save(destino, "JPEG", quality=90)


if __name__ == "__main__":
    entrada, salida = Path(sys.argv[1]), Path(sys.argv[2])
    salida.mkdir(parents=True, exist_ok=True)
    sesion = new_session("u2net")
    for archivo in sorted(entrada.iterdir()):
        if archivo.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        if (salida / f"{archivo.stem}.jpg").exists():
            continue  # ya está lista
        try:
            preparar(archivo, salida / f"{archivo.stem}.jpg", sesion)
            print("listo", archivo.name)
        except Exception as error:  # una foto mala no detiene las demás
            print("omitida", archivo.name, error)
