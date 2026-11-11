"""Limpieza de datos de las prendas con pandas (práctica 2, aplicada al armario).

Los votos no son los únicos datos que importan: si la foto o los datos de una prenda están mal, el probador
virtual y las recomendaciones salen mal. Por ejemplo, el pantalón #2 tenía una foto de 196x200 px y el
probador lo vestía gris en vez de azul.

Estrategia :
  PASO 1. Contar los valores faltantes por columna (como df.isnull().sum()). El tipo de prenda es opcional:
          se informa, pero no manda la prenda a revisión.
  PASO 2. Identificar los registros válidos:
          - que la foto exista y no sea demasiado chica (lado menor de al menos 256 px);
          - categoría, color, estampado y estilo dentro de los catálogos; nivel de abrigo de 1 a 5 (between);
          - que la foto no esté repetida en otra prenda (duplicated sobre la huella del archivo);
          - que el color guardado no contradiga la foto: un color vivo guardado cuando la prenda se ve gris, o
            un negro, blanco o gris guardado cuando se ve de un color intenso. Es una revisión conservadora:
            mira el centro de la foto, donde suele estar la prenda.
  PASO 3. Separar las válidas de las que requieren revisión, con el motivo.
  PASO 4. Exportar ambas a CSV en limpieza_de_datos/datos/ (desde la ruta /api/prendas/revision).

La app muestra el aviso en la pantalla de la prenda. Nada se borra ni se cambia solo: la persona decide.
"""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from PIL import Image, ImageOps

from servidor import base_datos
from servidor.base_datos import consultar
from servidor.logica import COLORES_NEUTROS, COLORES_VIVOS, ESTAMPADOS, ESTILOS
from servidor.seguridad import usuario_actual

CATEGORIAS = ["parte_superior", "parte_inferior", "calzado", "abrigo", "accesorio"]
COLORES = COLORES_NEUTROS | COLORES_VIVOS
LADO_MINIMO_PX = 256  # con menos, el probador no alcanza a copiar el color ni la textura
SATURACION_GRIS = 0.10  # por debajo, el centro de la foto se ve gris o neutro
SATURACION_INTENSA = 0.45  # por encima, se ve de un color intenso
NEUTROS_PUROS = {"negro", "blanco", "gris"}  # beige, café, azul marino y mezclilla sí tienen algo de color
CARPETA_CSV = Path(__file__).resolve().parent / "datos"

medidas_guardadas = {}  # (ruta, fecha de modificación) -> medidas de la foto; las fotos casi no cambian


# ------------------------------------------------------------
# DE LAS PRENDAS A UN DATAFRAME
# ------------------------------------------------------------

def medir_foto(url_imagen: str) -> dict:
    """Tamaño, huella del archivo y saturación del centro de la foto. Sin foto, todo queda vacío (NaN)."""
    ruta = base_datos.CARPETA_ARCHIVOS / (url_imagen or "").removeprefix("/archivos/")
    if not url_imagen or not ruta.is_file():
        return {"existe_foto": False, "ancho": None, "alto": None, "huella": None, "saturacion": None}
    clave = (str(ruta), ruta.stat().st_mtime)
    if clave not in medidas_guardadas:
        contenido = ruta.read_bytes()
        try:
            imagen = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
        except OSError:
            return {"existe_foto": False, "ancho": None, "alto": None, "huella": None, "saturacion": None}
        ancho, alto = imagen.size
        centro = imagen.crop((int(ancho * 0.3), int(alto * 0.3), int(ancho * 0.7), int(alto * 0.7)))
        saturacion = np.median(np.asarray(centro.convert("HSV"))[:, :, 1]) / 255
        medidas_guardadas[clave] = {"existe_foto": True, "ancho": ancho, "alto": alto,
                                    "huella": hashlib.md5(contenido).hexdigest(), "saturacion": float(saturacion)}
    return medidas_guardadas[clave]


def a_tabla(prendas: list[dict]) -> pd.DataFrame:
    filas = [{**{c: p.get(c) for c in ("id", "categoria", "subcategoria", "color_principal", "nivel_abrigo",
                                       "estampado", "estilo", "url_imagen")}, **medir_foto(p.get("url_imagen"))}
             for p in prendas]
    return pd.DataFrame(filas, columns=["id", "categoria", "subcategoria", "color_principal", "nivel_abrigo",
                                        "estampado", "estilo", "url_imagen", "existe_foto", "ancho", "alto",
                                        "huella", "saturacion"])


# ------------------------------------------------------------
# LA LIMPIEZA
# ------------------------------------------------------------

def limpiar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Devuelve (df_validas, df_revision, faltantes). df_revision trae la columna motivo."""
    # PASO 1. VALORES FALTANTES POR COLUMNA (solo se informan)
    faltantes = {columna: int(n) for columna, n in df.drop(columns=["huella", "saturacion"]).isnull().sum().items() if n}
    if df.empty:
        return df.copy(), df.assign(motivo=""), faltantes

    # PASO 2. IDENTIFICAR REGISTROS VALIDOS
    sin_foto = ~df["existe_foto"].astype(bool)
    lado_menor = df[["ancho", "alto"]].min(axis=1)
    foto_chica = ~sin_foto & (lado_menor < LADO_MINIMO_PX)
    fuera_de_catalogo = (~df["categoria"].isin(CATEGORIAS) | ~df["color_principal"].isin(COLORES)
                         | ~df["estampado"].isin(ESTAMPADOS) | ~df["estilo"].isin(ESTILOS))
    abrigo_fuera = ~pd.to_numeric(df["nivel_abrigo"], errors="coerce").between(1, 5)
    foto_repetida = df["huella"].notna() & df.duplicated(subset="huella", keep="first")
    se_ve_gris = df["color_principal"].isin(COLORES_VIVOS) & (df["saturacion"] < SATURACION_GRIS)
    se_ve_intenso = df["color_principal"].isin(NEUTROS_PUROS) & (df["saturacion"] > SATURACION_INTENSA)

    valido = ~(sin_foto | foto_chica | fuera_de_catalogo | abrigo_fuera | foto_repetida | se_ve_gris | se_ve_intenso)

    # Anotar por qué se aparta cada prenda.
    primera_con_huella = df.drop_duplicates(subset="huella").set_index("huella")["id"]
    motivo = pd.Series("", index=df.index)
    motivo[sin_foto] += "no se encontró la foto; "
    motivo[foto_chica] += ("la foto es muy chica (" + df["ancho"].astype("Int64").astype(str) + "x"
                           + df["alto"].astype("Int64").astype(str) + " px): el probador puede no copiar bien "
                           "el color. Sube una más grande; ")[foto_chica]
    motivo[fuera_de_catalogo] += "categoría, color, estampado o estilo fuera del catálogo; "
    motivo[abrigo_fuera] += "el nivel de abrigo debe ir de 1 a 5; "
    motivo[foto_repetida] += ("es la misma foto que la prenda #"
                              + df["huella"].map(primera_con_huella).astype("Int64").astype(str) + "; ")[foto_repetida]
    motivo[se_ve_gris] += ("guardada como " + df["color_principal"].str.replace("_", " ")
                           + ", pero en la foto se ve gris o neutra: revisa el color; ")[se_ve_gris]
    motivo[se_ve_intenso] += ("guardada como " + df["color_principal"]
                              + ", pero en la foto se ve de un color intenso: revisa el color; ")[se_ve_intenso]

    # PASO 3. SEPARAR LOS REGISTROS VALIDOS
    df_validas = df.loc[valido].copy()
    df_revision = df.loc[~valido].copy()
    df_revision["motivo"] = motivo[~valido].str.rstrip("; ")
    return df_validas, df_revision, faltantes


def prendas_de(usuario_id: int) -> list[dict]:
    return consultar("SELECT * FROM prendas WHERE usuario_id = ? ORDER BY id", (usuario_id,))


# ------------------------------------------------------------
# RUTAS (la de cada prenda la usa la app; la general se ve en /docs)
# ------------------------------------------------------------

rutas = APIRouter()


@rutas.get("/api/prendas/revision")
def revisar_armario(usuario: dict = Depends(usuario_actual)):
    """Limpia los datos del armario, exporta los CSV y dice qué prendas conviene revisar y por qué."""
    df = a_tabla(prendas_de(usuario["id"]))
    df_validas, df_revision, faltantes = limpiar(df)

    # PASO 4. EXPORTAR LOS RESULTADOS
    CARPETA_CSV.mkdir(exist_ok=True)
    columnas = [c for c in df.columns if c != "huella"]
    df_validas[columnas].to_csv(CARPETA_CSV / f"prendas_validas_usuario_{usuario['id']}.csv", index=False, encoding="utf-8")
    df_revision[columnas + ["motivo"]].to_csv(CARPETA_CSV / f"prendas_revision_usuario_{usuario['id']}.csv",
                                              index=False, encoding="utf-8")
    return {
        "total": len(df),
        "validas": len(df_validas),
        "faltantes": faltantes,
        "revision": [{"id": int(fila.id), "motivo": fila.motivo} for fila in df_revision.itertuples()],
    }


@rutas.get("/api/prendas/{prenda_id}/revision")
def revisar_prenda(prenda_id: int, usuario: dict = Depends(usuario_actual)):
    """Los motivos para revisar una prenda (lista vacía si está bien). Se compara con todo el armario por las fotos repetidas."""
    prendas = prendas_de(usuario["id"])
    if not any(p["id"] == prenda_id for p in prendas):
        raise HTTPException(404, "Prenda no encontrada")
    _, df_revision, _ = limpiar(a_tabla(prendas))
    fila = df_revision[df_revision["id"] == prenda_id]
    return {"motivos": fila["motivo"].iloc[0].split("; ") if len(fila) else []}
