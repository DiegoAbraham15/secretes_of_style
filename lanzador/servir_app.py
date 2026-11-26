"""Sirve la version web de la app (movil/dist) en http://localhost:8090, solo para esta computadora.

Cualquier ruta que no sea un archivo (por ejemplo /estadisticas) devuelve index.html: la app decide que pantalla mostrar.
"""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent / "movil" / "dist"


class AppWeb(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}

    def send_head(self):
        if not Path(self.translate_path(self.path)).is_file():
            self.path = "/index.html"
        return super().send_head()

    def log_message(self, *args):  # sin consola: no hay donde escribir los registros
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8090), partial(AppWeb, directory=str(CARPETA))).serve_forever()
