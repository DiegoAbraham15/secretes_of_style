"""Base de datos SQLite (un solo archivo) con sqlite3, que ya viene con Python."""

import sqlite3
from contextlib import closing
from pathlib import Path

CARPETA_BACKEND = Path(__file__).resolve().parent.parent
RUTA_BD = CARPETA_BACKEND / "secrets_of_style.db"
CARPETA_ARCHIVOS = CARPETA_BACKEND / "archivos_subidos"

TABLAS = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    correo TEXT UNIQUE NOT NULL,
    contraseña_hash TEXT NOT NULL,
    version_sesion INTEGER DEFAULT 0,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS perfiles (
    usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    altura_cm REAL,
    peso_kg REAL,
    url_imagen_rostro TEXT,
    url_avatar TEXT,
    parametros_corporales TEXT
);
CREATE TABLE IF NOT EXISTS prendas (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    url_imagen TEXT NOT NULL,
    categoria TEXT NOT NULL,
    subcategoria TEXT,
    color_principal TEXT NOT NULL,
    nivel_abrigo INTEGER NOT NULL,
    impermeable INTEGER DEFAULT 0,
    estampado TEXT DEFAULT 'liso',
    estilo TEXT DEFAULT 'casual',
    estado TEXT DEFAULT 'disponible',
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS atuendos (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    puntuacion REAL NOT NULL,
    reporte_clima TEXT,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS atuendo_elementos (
    atuendo_id INTEGER NOT NULL REFERENCES atuendos(id) ON DELETE CASCADE,
    prenda_id INTEGER NOT NULL REFERENCES prendas(id) ON DELETE CASCADE,
    rol TEXT NOT NULL,
    PRIMARY KEY (atuendo_id, prenda_id)
);
CREATE TABLE IF NOT EXISTS preferencias_usuario (
    usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    paleta TEXT NOT NULL,
    ropa TEXT NOT NULL,
    estampados TEXT NOT NULL,
    accesorios TEXT NOT NULL,
    fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pesos_usuario (
    usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    pesos TEXT NOT NULL,
    fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS votos_atuendo (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    firma TEXT NOT NULL,
    me_gusta INTEGER NOT NULL,
    caracteristicas TEXT NOT NULL,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (usuario_id, firma)
);
CREATE TABLE IF NOT EXISTS climas (
    clave TEXT PRIMARY KEY,
    consultado REAL NOT NULL,
    reporte TEXT NOT NULL
);
"""

# Columnas que se agregaron después: las bases viejas las reciben al arrancar el servidor.
COLUMNAS_NUEVAS = [
    ("usuarios", "version_sesion", "INTEGER DEFAULT 0"),
    ("prendas", "estampado", "TEXT DEFAULT 'liso'"),
    ("prendas", "estilo", "TEXT DEFAULT 'casual'"),
]


def conectar() -> sqlite3.Connection:
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row  # permite leer las columnas por nombre
    conexion.execute("PRAGMA foreign_keys = ON")  # activa el borrado en cascada
    return conexion


def crear_tablas():
    with closing(conectar()) as conexion:
        conexion.executescript(TABLAS)
        for tabla, columna, definicion in COLUMNAS_NUEVAS:
            columnas = {fila["name"] for fila in conexion.execute(f"PRAGMA table_info({tabla})")}
            if columna not in columnas:
                conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
        conexion.commit()


def consultar(sql: str, parametros: tuple = ()) -> list[dict]:
    """Ejecuta un SELECT y devuelve las filas como diccionarios."""
    with closing(conectar()) as conexion:
        return [dict(fila) for fila in conexion.execute(sql, parametros)]


def consultar_uno(sql: str, parametros: tuple = ()) -> dict | None:
    filas = consultar(sql, parametros)
    return filas[0] if filas else None


def ejecutar(sql: str, parametros: tuple = ()) -> int:
    """Ejecuta INSERT, UPDATE o DELETE y devuelve el id de la fila insertada."""
    with closing(conectar()) as conexion, conexion:
        return conexion.execute(sql, parametros).lastrowid
