"""Limpieza de datos con pandas : revisa los votos antes de que entrenen al perceptrón.

Los datos son los votos de la tabla votos_atuendo. Cada voto es una fila con:
  X  las 13 características del atuendo (caracteristicas_de en aprendizaje.py), todas de 0 a 1
  y  me_gusta: +1 si le dio corazón, -1 si se le mostró y no le dio corazón

Estrategia (la de la práctica, parte D, más un paso propio del proyecto):
  PASO 1. Eliminar filas completamente duplicadas.
  PASO 2. Identificar los registros válidos: completos, en rango y sin contradicciones.
          Contradicción: atuendos distintos con características idénticas y votos distintos (por ejemplo,
          dos zapatos café formales). El perceptrón nunca podría acertar los dos. Gana el corazón, porque es un
          voto que la persona dio a propósito; el -1 solo significa que lo vio.
  PASO 3. Separar los válidos (entrenan) de los que requieren revisión, anotando el motivo.
  PASO 4. Exportar ambos a CSV en limpieza_de_datos/datos/ (solo desde la ruta /api/votos/limpieza, no en cada
          entrenamiento).

Lo que se aparta solo deja de entrenar al perceptrón: no se borra de la base y sigue contando en reordenar.

"""

import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends

from servidor.base_datos import consultar
from servidor.logica import ESTILOS
from servidor.seguridad import usuario_actual

# Las características que espera el perceptrón (las mismas que arma caracteristicas_de).
CARACTERISTICAS = ["neutros", "contraste", "tono", "complementarios", "monocromo", "abrigo", "estampado",
                   "accesorio"] + [f"estilo_{estilo}" for estilo in ESTILOS]
CARPETA_CSV = Path(__file__).resolve().parent / "datos"  # limpieza_de_datos/datos/


# ------------------------------------------------------------
# DE LOS VOTOS A UN DATAFRAME
# ------------------------------------------------------------

def a_tabla(votos: list[dict]) -> pd.DataFrame:
    """Una fila por voto: firma, una columna por característica y me_gusta.

    Si a un voto le falta una característica, queda NaN; si trae texto u otra cosa, to_numeric la vuelve NaN.
    Así el paso 2 la detecta como faltante.
    """
    filas = [{"firma": v.get("firma"), **(v.get("caracteristicas") or {}), "me_gusta": v.get("me_gusta")} for v in votos]
    df = pd.DataFrame(filas, columns=["firma"] + CARACTERISTICAS + ["me_gusta"])
    df[CARACTERISTICAS + ["me_gusta"]] = df[CARACTERISTICAS + ["me_gusta"]].apply(pd.to_numeric, errors="coerce")
    return df


# ------------------------------------------------------------
# LA LIMPIEZA
# ------------------------------------------------------------

def limpiar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (df_validos, df_revision). df_revision trae la columna motivo."""

    if df.empty:  # sin votos no hay nada que limpiar
        return df.copy(), df.assign(motivo="")

    # PASO 1. ELIMINAR FILAS COMPLETAMENTE DUPLICADAS
    df_limpio = df.drop_duplicates().copy()

    # PASO 2. IDENTIFICAR REGISTROS VALIDOS
    # Que no falte ninguna característica ni el voto.
    completo = df_limpio[CARACTERISTICAS + ["me_gusta"]].notna().all(axis=1)

    # Que todas las características estén entre 0 y 1 (NaN cuenta como fuera; ya lo marcó "completo").
    en_rango = df_limpio[CARACTERISTICAS].apply(lambda columna: columna.between(0, 1)).all(axis=1)

    # Que el voto sea +1 o -1.
    voto_valido = df_limpio["me_gusta"].isin([1, -1])

    # Que no haya un atuendo con las mismas características y corazón (solo entre los que ya están bien).
    bien = completo & en_rango & voto_valido
    huella = df_limpio[CARACTERISTICAS].round(6).apply(tuple, axis=1)  # lo que el modelo ve del atuendo
    huellas_con_corazon = set(huella[bien & (df_limpio["me_gusta"] == 1)])
    contradictorio = bien & (df_limpio["me_gusta"] == -1) & huella.isin(huellas_con_corazon)

    # Combinar las condiciones.
    valido = bien & ~contradictorio

    # Anotar por qué se aparta cada registro.
    faltantes = df_limpio[CARACTERISTICAS].isna().apply(lambda fila: ", ".join(fila.index[fila]), axis=1)
    fuera = df_limpio[CARACTERISTICAS].apply(lambda columna: columna.notna() & ~columna.between(0, 1))
    fuera = fuera.apply(lambda fila: ", ".join(fila.index[fila]), axis=1)
    motivo = pd.Series("", index=df_limpio.index)
    motivo[faltantes != ""] += "incompleto: falta " + faltantes[faltantes != ""] + "; "
    motivo[df_limpio["me_gusta"].isna()] += "incompleto: falta el voto; "
    motivo[fuera != ""] += "fuera de 0 a 1: " + fuera[fuera != ""] + "; "
    motivo[df_limpio["me_gusta"].notna() & ~voto_valido] += "voto distinto de +1 o -1; "
    motivo[contradictorio] += "otro atuendo con las mismas características tiene corazón; "

    # PASO 3. SEPARAR LOS REGISTROS VALIDOS
    df_validos = df_limpio.loc[valido].copy()
    # Los registros descartados se conservan para poder auditarlos.
    df_revision = df_limpio.loc[~valido].copy()
    df_revision["motivo"] = motivo[~valido].str.rstrip("; ")
    return df_validos, df_revision


def limpiar_votos(votos: list[dict]) -> dict:
    """Lo que usa reentrenar: los votos originales que pasaron la limpieza, en su orden, y los apartados."""
    df_validos, df_revision = limpiar(a_tabla(votos))
    return {
        "validos": [votos[i] for i in df_validos.index],  # el índice del DataFrame es la posición en la lista
        "revision": [{**votos[i], "motivo": df_revision.at[i, "motivo"]} for i in df_revision.index],
    }


# ------------------------------------------------------------
# RUTA PARA VER LA LIMPIEZA 
# ------------------------------------------------------------

rutas = APIRouter()


@rutas.get("/api/votos/limpieza")
def ver_limpieza(usuario: dict = Depends(usuario_actual)):
    """Limpia los votos de la persona, exporta los CSV y dice cuántos entrenan y qué se apartó."""
    filas = consultar("SELECT firma, me_gusta, caracteristicas FROM votos_atuendo WHERE usuario_id = ? ORDER BY id",
                      (usuario["id"],))
    votos = []
    for fila in filas:
        try:
            caracteristicas = json.loads(fila["caracteristicas"])
        except (TypeError, ValueError):
            caracteristicas = None  # texto dañado: cae en "incompleto"
        votos.append({**fila, "caracteristicas": caracteristicas})

    df = a_tabla(votos)
    df_validos, df_revision = limpiar(df)

    # PASO 4. EXPORTAR LOS RESULTADOS
    CARPETA_CSV.mkdir(exist_ok=True)
    df_validos.to_csv(CARPETA_CSV / f"votos_limpios_usuario_{usuario['id']}.csv", index=False, encoding="utf-8")
    df_revision.to_csv(CARPETA_CSV / f"votos_revision_usuario_{usuario['id']}.csv", index=False, encoding="utf-8")

    return {
        "total": len(df),
        "duplicados": int(df.duplicated().sum()),
        "validos": len(df_validos),
        "validos_con_corazon": int((df_validos["me_gusta"] == 1).sum()),
        # NaN no existe en JSON: un voto faltante sale como null.
        "revision": df_revision[["firma", "me_gusta", "motivo"]].astype(object)
                    .where(df_revision[["firma", "me_gusta", "motivo"]].notna(), None).to_dict(orient="records"),
        "archivos": [f"limpieza_de_datos/datos/votos_limpios_usuario_{usuario['id']}.csv",
                     f"limpieza_de_datos/datos/votos_revision_usuario_{usuario['id']}.csv"],
    }
