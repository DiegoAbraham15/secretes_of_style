"""Lo que comparten las etapas del entrenamiento de la CNN: rutas, semilla, tamaños y el formato de los títulos.

Se corre con el Python de esta carpeta (entrenamiento_cnn\\.venv, Python 3.11 con pandas y PyTorch), no con el
del servidor. Importa los módulos de servidor/ (catálogos, reglas de color, la secuencia de la CNN) para que los
datos simulados y el entrenamiento usen exactamente lo mismo que la app.
"""

import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
CARPETA_BACKEND = CARPETA.parent
DATOS = CARPETA / "datos"
DATOS.mkdir(exist_ok=True)
MODELOS_ENTRENADOS = CARPETA_BACKEND / "modelos_entrenados"
MODELOS_ENTRENADOS.mkdir(exist_ok=True)

ARCHIVO_CSV = DATOS / "atuendos_50000.csv"
CARPETA_PARQUET = DATOS / "atuendos_procesados"
ARCHIVO_RESUMEN = DATOS / "resumen_etl.csv"
ARCHIVO_TENSORES = DATOS / "atuendos_cnn.npz"
ARCHIVO_CHECKPOINT = DATOS / "cnn_atuendos.pth"
ARCHIVO_METRICAS = MODELOS_ENTRENADOS / "metricas_cnn.json"

SEMILLA = 42
PERSONAS = 10_000
LOOKS_POR_PERSONA = 5
TOTAL_REGISTROS = PERSONAS * LOOKS_POR_PERSONA

sys.path.insert(0, str(CARPETA_BACKEND))  # para "from servidor.… import …"


def titulo(texto: str):
    print("\n" + "=" * 65 + f"\n{texto}\n" + "=" * 65)


def leer_parquet():
    """Lee el Parquet que deja etl_atuendos.py como DataFrame de pandas, en el orden de id_registro."""
    import pandas as pd

    if not CARPETA_PARQUET.exists():
        raise FileNotFoundError(f"No existe {CARPETA_PARQUET}: corre primero etl_atuendos.py")
    datos = pd.read_parquet(CARPETA_PARQUET)
    datos["ropa"] = datos["ropa"].astype(str)  # la columna de la partición llega como categoría
    return datos.sort_values("id_registro").reset_index(drop=True)
