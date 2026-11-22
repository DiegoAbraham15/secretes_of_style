"""ETAPA 2 · ETL de los looks simulados con pandas (extracción, validación, transformación y carga a Parquet).

pandas lee el CSV de generacion_de_datos.py con tipos fijos, valida cada regla de los catálogos de la app,
calcula columnas nuevas, resume los corazones por perfil y guarda el resultado en Parquet particionado por el
tipo de ropa del cuestionario.

50 000 filas (unos 7 MB) caben de sobra en la memoria de una sola computadora: todo el ETL tarda segundos con
operaciones vectorizadas de pandas, sin clúster ni JVM.
"""

import pandas as pd

from comun import (ARCHIVO_CSV, ARCHIVO_RESUMEN, CARPETA_PARQUET, LOOKS_POR_PERSONA, TOTAL_REGISTROS, titulo)
from servidor.aprendizaje import PESOS_DE_RESPUESTA
from servidor.logica import COLORES, COLORES_NEUTROS, ESTAMPADOS, ESTILOS
from servidor.red_convolucional import ORDEN

OBLIGATORIAS = ["parte_superior", "parte_inferior", "calzado"]
ABRIGO = {"abrigo": (3, 5), "parte_superior": (1, 4), "parte_inferior": (1, 3), "calzado": (1, 3), "accesorio": (1, 2)}

# Esquema fijo: si el CSV trae otra columna o le falta una, la carga se detiene.
COLUMNAS = (["id_registro", "id_persona", *PESOS_DE_RESPUESTA]
            + [f"{p}_{c}" for p in ORDEN for c in ("color", "abrigo", "estampado", "estilo")]
            + ["me_gusta"])
TIPOS = {"id_registro": "int64", "id_persona": "string", "me_gusta": "int64",
         **{pregunta: "string" for pregunta in PESOS_DE_RESPUESTA},
         **{f"{p}_{c}": "string" for p in ORDEN for c in ("color", "estampado", "estilo")},
         **{f"{p}_abrigo": "Float64" for p in ORDEN}}


def cargar():
    titulo("1. LEYENDO EL CSV CON ESQUEMA")
    if not ARCHIVO_CSV.exists():
        raise FileNotFoundError(f"No existe {ARCHIVO_CSV}: corre primero generacion_de_datos.py")
    df = pd.read_csv(ARCHIVO_CSV, dtype=TIPOS)
    if list(df.columns) != COLUMNAS:
        raise ValueError(f"Columnas inesperadas en el CSV: {sorted(set(df.columns) ^ set(COLUMNAS))}")
    # El CSV trae el abrigo como "5.0" en las columnas con huecos: se pasa a entero que admite vacíos.
    for posicion in ORDEN:
        df[f"{posicion}_abrigo"] = df[f"{posicion}_abrigo"].astype("Int64")
    print(df.dtypes.to_string())
    print(f"\nFilas: {len(df):,} · columnas: {df.shape[1]} · memoria: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")
    return df


def validar(df):
    """Cada regla debe dar 0 registros; si no, se detiene."""
    titulo("2. VALIDANDO CON LOS CATÁLOGOS DE LA APP")
    total = len(df)
    revisiones = {
        "registros esperados": int(total != TOTAL_REGISTROS),
        "identificadores repetidos": int(df["id_registro"].duplicated().sum()),
        "sin parte de arriba, de abajo o calzado": int(df[[f"{p}_color" for p in OBLIGATORIAS]].isna().any(axis=1).sum()),
        "respuesta del cuestionario fuera del catálogo": int(pd.concat(
            [~df[p].isin(list(op)) for p, op in PESOS_DE_RESPUESTA.items()], axis=1).any(axis=1).sum()),
        "corazón distinto de 0/1": int((~df["me_gusta"].isin([0, 1])).sum()),
    }
    for posicion in ORDEN:
        presente = df[f"{posicion}_color"].notna()
        minimo, maximo = ABRIGO[posicion]
        fuera = (~df[f"{posicion}_color"].isin(sorted(COLORES))
                 | ~df[f"{posicion}_estampado"].isin(ESTAMPADOS)
                 | ~df[f"{posicion}_estilo"].isin(ESTILOS)
                 | ~df[f"{posicion}_abrigo"].between(minimo, maximo).fillna(False))
        revisiones[f"{posicion}: valores fuera de catálogo"] = int((presente & fuera).sum())
    looks = df.groupby("id_persona").size()
    revisiones[f"personas sin {LOOKS_POR_PERSONA} looks"] = int((looks != LOOKS_POR_PERSONA).sum())
    for regla, cuantos in revisiones.items():
        print(f"  {regla:48} {cuantos}")
    if any(revisiones.values()):
        raise ValueError("La validación encontró registros inválidos")
    print(f"\nVALIDACIÓN COMPLETA: {total:,} registros correctos")


def transformar(df):
    titulo("3. COLUMNAS NUEVAS")
    def contar(condicion):  # cuántas posiciones cumplen la condición; una posición vacía cuenta 0
        return sum(condicion(p).fillna(False).astype(int) for p in ORDEN)

    df = df.assign(
        prendas=contar(lambda p: df[f"{p}_color"].notna()),
        estampadas=contar(lambda p: df[f"{p}_estampado"].notna() & (df[f"{p}_estampado"] != "liso")),
        neutras=contar(lambda p: df[f"{p}_color"].isin(sorted(COLORES_NEUTROS))),
        mismo_estilo_arriba_abajo=(df["parte_superior_estilo"] == df["parte_inferior_estilo"]).astype(int),
    )
    print("prendas, estampadas, neutras y mismo_estilo_arriba_abajo calculadas")
    print(df[["id_registro", "prendas", "estampadas", "neutras", "mismo_estilo_arriba_abajo", "me_gusta"]].head(5).to_string(index=False))
    return df


def analizar(df):
    titulo("4. ANÁLISIS EXPLORATORIO")
    def resumen(columna):
        tabla = df.groupby(columna).agg(looks=("me_gusta", "size"), pct_corazon=("me_gusta", "mean"))
        tabla["pct_corazon"] = (tabla["pct_corazon"] * 100).round(1)
        return tabla.to_string()

    print("Corazones por tipo de ropa del cuestionario:\n" + resumen("ropa"))
    print("\nCorazones según cuántas prendas estampadas lleva el look:\n" + resumen("estampadas"))
    print("\nCorazones si arriba y abajo son del mismo estilo:\n" + resumen("mismo_estilo_arriba_abajo"))


def guardar(df):
    titulo("5. GUARDANDO EN PARQUET")
    import shutil

    shutil.rmtree(CARPETA_PARQUET, ignore_errors=True)
    df.to_parquet(CARPETA_PARQUET, partition_cols=["ropa"], index=False)
    print(f"Parquet particionado por ropa en {CARPETA_PARQUET}")
    resumen = df.groupby(["ropa", "paleta"]).agg(looks=("me_gusta", "size"), tasa_corazon=("me_gusta", "mean")).reset_index()
    resumen.to_csv(ARCHIVO_RESUMEN, index=False)
    print(f"Resumen por perfil en {ARCHIVO_RESUMEN}")


def main():
    titulo("SECRETS OF STYLE · ETAPA 2 · ETL DE LOOKS SIMULADOS (pandas)")
    print("Versión de pandas:", pd.__version__)
    df = cargar()
    validar(df)
    df = transformar(df)
    analizar(df)
    guardar(df)
    titulo("ETAPA 2 FINALIZADA")


if __name__ == "__main__":
    main()
