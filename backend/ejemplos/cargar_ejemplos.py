"""Carga al armario de una cuenta las prendas de ejemplo (fotos de backend/ejemplos/fotos).

Usa la API del servidor, así que pasan por las mismas validaciones que una prenda subida desde la app.
Hace falta el servidor corriendo (python -m uvicorn servidor.principal:aplicacion --port 8000).

    .venv\\Scripts\\python ejemplos\\cargar_ejemplos.py CORREO CONTRASEÑA [URL]

Corre una sola vez por cuenta: cada ejecución agrega las prendas otra vez.
Los datos de cada foto (tipo, color, abrigo…) están en prendas_de_ejemplo.json y los créditos en creditos.md.
"""

import json
import sys
from pathlib import Path

import httpx

CARPETA = Path(__file__).resolve().parent


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    correo, contraseña = sys.argv[1], sys.argv[2]
    url = (sys.argv[3] if len(sys.argv) > 3 else "http://127.0.0.1:8000").rstrip("/")

    inicio = httpx.post(f"{url}/api/auth/login", json={"correo": correo, "contraseña": contraseña}, timeout=30)
    inicio.raise_for_status()
    cabeceras = {"Authorization": f"Bearer {inicio.json()['token_acceso']}"}

    manifiesto = json.loads((CARPETA / "prendas_de_ejemplo.json").read_text(encoding="utf-8"))
    cargadas = 0
    for prenda in manifiesto:
        foto = CARPETA / "fotos" / prenda["archivo"]
        datos = {k: v for k, v in prenda.items() if k != "archivo"}
        datos = {k: str(v).lower() if isinstance(v, bool) else v for k, v in datos.items()}
        with foto.open("rb") as archivo:
            respuesta = httpx.post(f"{url}/api/prendas", headers=cabeceras, data=datos,
                                      files={"imagen": (foto.name, archivo, "image/jpeg")}, timeout=60)
        respuesta.raise_for_status()
        cargadas += 1
        print("cargada", prenda["subcategoria"], prenda["color_principal"])
    print(f"{cargadas} prendas de ejemplo en el armario de {correo}")


if __name__ == "__main__":
    main()
