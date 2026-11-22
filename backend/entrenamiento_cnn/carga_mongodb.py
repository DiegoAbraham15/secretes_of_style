"""ETAPA 3 · Carga masiva de los looks procesados en MongoDB (pymongo con bulk_write).

Lee el Parquet de etl_atuendos.py y escribe en lotes de 500 con bulk_write. Con ReplaceOne y upsert la carga se
puede repetir sin duplicar: el índice único (id_lote, id_registro) lo garantiza.

Va a la MongoDB local, en una base APARTE (secrets_of_style_bigdata): los 50 000 looks simulados no se mezclan
con los datos reales de la app.
"""

import os
from datetime import datetime, timezone

import pandas as pd
from pymongo import MongoClient, ReplaceOne

from comun import PERSONAS, TOTAL_REGISTROS, leer_parquet, titulo

URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
BASE = "secrets_of_style_bigdata"
COLECCION = "atuendos_simulados"
LOTE = "SECRETS-50000-V1"
TAMANO_LOTE = 500


def preparar_coleccion():
    titulo("1. CONECTANDO CON MONGODB")
    cliente = MongoClient(URI, serverSelectionTimeoutMS=10000)
    cliente.admin.command("ping")
    coleccion = cliente[BASE][COLECCION]
    coleccion.create_index([("id_lote", 1), ("id_registro", 1)], unique=True, name="un_registro_por_lote")
    coleccion.create_index("id_persona", name="looks_por_persona")
    print(f"Base {BASE} · colección {COLECCION} · índices listos")
    return cliente, coleccion


def escribir(coleccion, datos):
    """Un documento por look, sin los campos vacíos (posiciones sin abrigo o sin accesorio)."""
    fecha = datetime.now(timezone.utc)
    operaciones, lotes = [], 0
    for fila in datos.to_dict("records"):
        documento = {clave: valor for clave, valor in fila.items() if not pd.isna(valor)}
        documento.update(id_lote=LOTE, fecha_carga=fecha)
        operaciones.append(ReplaceOne({"id_lote": LOTE, "id_registro": documento["id_registro"]}, documento, upsert=True))
        if len(operaciones) >= TAMANO_LOTE:
            coleccion.bulk_write(operaciones, ordered=False)
            operaciones.clear()
            lotes += 1
    if operaciones:
        coleccion.bulk_write(operaciones, ordered=False)
        lotes += 1
    return lotes


def validar(coleccion):
    titulo("4. VALIDANDO LO GUARDADO")
    filtro = {"id_lote": LOTE}
    total = coleccion.count_documents(filtro)
    personas = len(coleccion.distinct("id_persona", filtro))
    corazones = coleccion.count_documents({**filtro, "me_gusta": 1})
    print(f"Documentos: {total:,} (esperados {TOTAL_REGISTROS:,}) · personas: {personas:,} · corazones: {corazones:,}")
    if total != TOTAL_REGISTROS or personas != PERSONAS:
        raise ValueError("Lo guardado en MongoDB no coincide con lo esperado")
    print("Ejemplo:", coleccion.find_one(filtro, {"_id": 0, "fecha_carga": 0}))


def main():
    titulo("SECRETS OF STYLE · ETAPA 3 · CARGA MASIVA EN MONGODB")
    cliente, coleccion = preparar_coleccion()
    try:
        titulo("2. LEYENDO EL PARQUET")
        datos = leer_parquet()
        print(f"Registros: {len(datos):,}")
        titulo("3. ESCRIBIENDO EN LOTES")
        lotes = escribir(coleccion, datos)
        print(f"{lotes} lotes de hasta {TAMANO_LOTE} documentos escritos con bulk_write (ReplaceOne + upsert)")
        validar(coleccion)
        titulo("ETAPA 3 FINALIZADA")
    finally:
        cliente.close()


if __name__ == "__main__":
    main()
