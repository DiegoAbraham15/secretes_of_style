"""API de Secrets of Style.

Ejecutar desde la carpeta backend:
    uvicorn servidor.principal:aplicacion --reload --host 0.0.0.0 --port 8000
"""

import json
import uuid
from collections import Counter

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from servidor.base_datos import CARPETA_ARCHIVOS, consultar, consultar_uno, crear_tablas, ejecutar
from servidor.busqueda import recomendar
from servidor.clima import obtener_clima
from servidor.logica import COLORES_NEUTROS, COLORES_VIVOS
from servidor.seguridad import crear_token, generar_hash, usuario_actual, verificar_contraseña

CATEGORIAS = ["parte_superior", "parte_inferior", "calzado", "abrigo", "accesorio"]
ESTADOS = ["disponible", "en_lavado", "archivada"]
COLORES = COLORES_NEUTROS | COLORES_VIVOS
MARCAS_HEIC = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}
MAXIMO_IMAGEN_MB = 8
# CORS solo aplica a la versión web (la app del teléfono no lo usa): se permite la computadora
# y las IP de la red local, que es desde donde Expo sirve la app.
ORIGENES_PERMITIDOS = (
    r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+"
    r"|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?"
)

crear_tablas()
CARPETA_ARCHIVOS.mkdir(exist_ok=True)

aplicacion = FastAPI(title="Secrets of Style")
aplicacion.add_middleware(
    CORSMiddleware,
    allow_origin_regex=ORIGENES_PERMITIDOS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
aplicacion.mount("/archivos", StaticFiles(directory=CARPETA_ARCHIVOS), name="archivos")


# ============================================================
# AUTENTICACIÓN
# ============================================================

class Cuenta(BaseModel):
    correo: str
    contraseña: str


def respuesta_token(usuario: dict) -> dict:
    return {"token_acceso": crear_token(usuario), "usuario": {"id": usuario["id"], "correo": usuario["correo"]}}


@aplicacion.post("/api/auth/registro", status_code=201)
def registrar(datos: Cuenta):
    correo = datos.correo.strip().lower()
    if "@" not in correo:
        raise HTTPException(422, "Escribe un correo válido")
    if len(datos.contraseña) < 8:
        raise HTTPException(422, "La contraseña debe tener al menos 8 caracteres")
    if consultar_uno("SELECT id FROM usuarios WHERE correo = ?", (correo,)):
        raise HTTPException(409, "Ese correo ya está registrado")

    usuario_id = ejecutar(
        "INSERT INTO usuarios (correo, contraseña_hash, fecha_creacion) VALUES (?, ?, datetime('now'))", (correo, generar_hash(datos.contraseña))
    )
    ejecutar("INSERT INTO perfiles (usuario_id) VALUES (?)", (usuario_id,))
    return respuesta_token({"id": usuario_id, "correo": correo})


@aplicacion.post("/api/auth/login")
def iniciar_sesion(datos: Cuenta):
    usuario = consultar_uno("SELECT * FROM usuarios WHERE correo = ?", (datos.correo.strip().lower(),))
    if not usuario or not verificar_contraseña(datos.contraseña, usuario["contraseña_hash"]):
        raise HTTPException(401, "Correo o contraseña incorrectos")
    return respuesta_token(usuario)


@aplicacion.get("/api/auth/yo")
def usuario_de_la_sesion(usuario: dict = Depends(usuario_actual)):
    return usuario


@aplicacion.post("/api/auth/cerrar-sesion", status_code=204)
def cerrar_sesion(usuario: dict = Depends(usuario_actual)):
    """Sube la versión de sesión: todos los tokens emitidos hasta ahora dejan de ser válidos."""
    ejecutar("UPDATE usuarios SET version_sesion = version_sesion + 1 WHERE id = ?", (usuario["id"],))


# ============================================================
# PERFIL
# ============================================================

class DatosPerfil(BaseModel):
    altura_cm: float | None = None
    peso_kg: float | None = None


def calcular_parametros_corporales(altura_cm: float | None, peso_kg: float | None) -> dict | None:
    """Datos simples para dibujar la silueta del avatar más adelante."""
    if not altura_cm or not peso_kg:
        return None
    imc = peso_kg / (altura_cm / 100) ** 2
    complexion = "delgada" if imc < 18.5 else "media" if imc < 25 else "robusta" if imc < 30 else "amplia"
    return {"imc": round(imc, 1), "complexion": complexion, "escala_altura": round(altura_cm / 170, 3)}


def leer_perfil(usuario_id: int) -> dict:
    perfil = consultar_uno("SELECT * FROM perfiles WHERE usuario_id = ?", (usuario_id,))
    if perfil is None:
        ejecutar("INSERT INTO perfiles (usuario_id) VALUES (?)", (usuario_id,))
        return leer_perfil(usuario_id)
    perfil["parametros_corporales"] = json.loads(perfil["parametros_corporales"] or "null")
    return perfil


@aplicacion.get("/api/perfil")
def ver_perfil(usuario: dict = Depends(usuario_actual)):
    return leer_perfil(usuario["id"])


@aplicacion.put("/api/perfil")
def actualizar_perfil(datos: DatosPerfil, usuario: dict = Depends(usuario_actual)):
    leer_perfil(usuario["id"])  # crea el perfil si no existe
    parametros = calcular_parametros_corporales(datos.altura_cm, datos.peso_kg)
    ejecutar(
        "UPDATE perfiles SET altura_cm = ?, peso_kg = ?, parametros_corporales = ? WHERE usuario_id = ?",
        (datos.altura_cm, datos.peso_kg, json.dumps(parametros), usuario["id"]),
    )
    return leer_perfil(usuario["id"])


@aplicacion.post("/api/perfil/rostro")
async def subir_rostro(imagen: UploadFile = File(...), usuario: dict = Depends(usuario_actual)):
    borrar_imagen(leer_perfil(usuario["id"])["url_imagen_rostro"])
    ruta = await guardar_imagen(imagen, "rostros")
    ejecutar("UPDATE perfiles SET url_imagen_rostro = ? WHERE usuario_id = ?", (ruta, usuario["id"]))
    return leer_perfil(usuario["id"])


# ============================================================
# ARMARIO
# ============================================================

def extension_de_imagen(contenido: bytes) -> str | None:
    """Extensión según los primeros bytes del archivo (su firma), sin confiar en el nombre que manda la app."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return ".webp"
    if contenido[4:8] == b"ftyp" and contenido[8:12] in MARCAS_HEIC:
        return ".heic"
    return None


async def guardar_imagen(archivo: UploadFile, carpeta: str) -> str:
    """Guarda la imagen en disco y devuelve su ruta pública, p. ej. /archivos/prendas/abc.jpg."""
    maximo_bytes = MAXIMO_IMAGEN_MB * 1024 * 1024
    contenido = await archivo.read(maximo_bytes + 1)  # un byte de más basta para saber si se pasa
    if len(contenido) > maximo_bytes:
        raise HTTPException(413, f"La imagen supera {MAXIMO_IMAGEN_MB} MB")
    extension = extension_de_imagen(contenido)
    if extension is None:
        raise HTTPException(415, "El archivo no es una imagen JPG, PNG, WEBP o HEIC.")

    nombre = f"{uuid.uuid4().hex}{extension}"
    (CARPETA_ARCHIVOS / carpeta).mkdir(parents=True, exist_ok=True)
    (CARPETA_ARCHIVOS / carpeta / nombre).write_bytes(contenido)
    return f"/archivos/{carpeta}/{nombre}"


def borrar_imagen(ruta_publica: str | None):
    if ruta_publica:
        (CARPETA_ARCHIVOS / ruta_publica.removeprefix("/archivos/")).unlink(missing_ok=True)


def preparar_prenda(prenda: dict) -> dict:
    prenda["impermeable"] = bool(prenda["impermeable"])  # SQLite guarda 0 o 1
    return prenda


def buscar_prenda(prenda_id: int, usuario: dict) -> dict:
    prenda = consultar_uno("SELECT * FROM prendas WHERE id = ? AND usuario_id = ?", (prenda_id, usuario["id"]))
    if prenda is None:
        raise HTTPException(404, "Prenda no encontrada")
    return preparar_prenda(prenda)


@aplicacion.post("/api/prendas", status_code=201)
async def subir_prenda(
    imagen: UploadFile = File(...),
    categoria: str = Form(...),
    color_principal: str = Form(...),
    nivel_abrigo: int = Form(...),
    impermeable: bool = Form(False),
    subcategoria: str = Form(""),
    usuario: dict = Depends(usuario_actual),
):
    if categoria not in CATEGORIAS or color_principal not in COLORES or not 1 <= nivel_abrigo <= 5:
        raise HTTPException(422, "Revisa la categoría, el color y el nivel de abrigo (1 a 5)")

    prenda_id = ejecutar(
        "INSERT INTO prendas (usuario_id, url_imagen, categoria, subcategoria, color_principal, nivel_abrigo,"
        " impermeable, estado, fecha_creacion) VALUES (?, ?, ?, ?, ?, ?, ?, 'disponible', datetime('now'))",
        (usuario["id"], await guardar_imagen(imagen, "prendas"), categoria, subcategoria.strip()[:60] or None,
         color_principal, nivel_abrigo, impermeable),
    )
    return buscar_prenda(prenda_id, usuario)


@aplicacion.get("/api/prendas")
def listar_prendas(
    categoria: str | None = None,
    color_principal: str | None = None,
    estado: str | None = None,
    impermeable: bool | None = None,
    nivel_abrigo_minimo: int = 1,
    nivel_abrigo_maximo: int = 5,
    usuario: dict = Depends(usuario_actual),
):
    sql = "SELECT * FROM prendas WHERE usuario_id = ? AND nivel_abrigo BETWEEN ? AND ?"
    parametros = [usuario["id"], nivel_abrigo_minimo, nivel_abrigo_maximo]
    # Cada filtro opcional agrega una condición a la consulta.
    for columna, valor in [("categoria", categoria), ("color_principal", color_principal),
                           ("estado", estado), ("impermeable", impermeable)]:
        if valor is not None:
            sql += f" AND {columna} = ?"
            parametros.append(valor)
    return [preparar_prenda(p) for p in consultar(sql + " ORDER BY id DESC", tuple(parametros))]


@aplicacion.get("/api/prendas/{prenda_id}")
def ver_prenda(prenda_id: int, usuario: dict = Depends(usuario_actual)):
    return buscar_prenda(prenda_id, usuario)


class CambioEstado(BaseModel):
    estado: str


@aplicacion.patch("/api/prendas/{prenda_id}/estado")
def cambiar_estado(prenda_id: int, datos: CambioEstado, usuario: dict = Depends(usuario_actual)):
    buscar_prenda(prenda_id, usuario)
    if datos.estado not in ESTADOS:
        raise HTTPException(422, "El estado debe ser disponible, en_lavado o archivada")
    ejecutar("UPDATE prendas SET estado = ? WHERE id = ?", (datos.estado, prenda_id))
    return buscar_prenda(prenda_id, usuario)


@aplicacion.delete("/api/prendas/{prenda_id}", status_code=204)
def eliminar_prenda(prenda_id: int, usuario: dict = Depends(usuario_actual)):
    prenda = buscar_prenda(prenda_id, usuario)
    ejecutar("DELETE FROM prendas WHERE id = ?", (prenda_id,))  # también la quita de los atuendos (cascada)
    borrar_imagen(prenda["url_imagen"])


# ============================================================
# CLIMA
# ============================================================

@aplicacion.get("/api/clima")
def consultar_clima(latitud: float, longitud: float, _usuario: dict = Depends(usuario_actual)):
    return obtener_clima(latitud, longitud)


# ============================================================
# RECOMENDACIONES Y ATUENDOS
# ============================================================

class SolicitudRecomendacion(BaseModel):
    prenda_base_id: int
    latitud: float
    longitud: float
    cantidad: int = Field(default=3, ge=1, le=10)


@aplicacion.post("/api/recomendaciones")
def generar_recomendaciones(datos: SolicitudRecomendacion, usuario: dict = Depends(usuario_actual)):
    """Los mejores atuendos con la prenda base según A* y el clima real."""
    base = buscar_prenda(datos.prenda_base_id, usuario)
    clima = obtener_clima(datos.latitud, datos.longitud)
    armario = [preparar_prenda(p) for p in consultar("SELECT * FROM prendas WHERE usuario_id = ?", (usuario["id"],))]
    return {"clima": clima, "prenda_base": base, **recomendar(base, armario, set(clima["hechos"]), datos.cantidad)}


class ElementoNuevo(BaseModel):
    prenda_id: int
    rol: str


class AtuendoNuevo(BaseModel):
    puntuacion: float
    reporte_clima: dict | None = None
    elementos: list[ElementoNuevo]


def leer_atuendo(atuendo: dict) -> dict:
    atuendo["reporte_clima"] = json.loads(atuendo["reporte_clima"] or "null")
    prendas = consultar(
        # En el orden en que se guardaron: la prenda base primero.
        "SELECT e.rol, p.* FROM atuendo_elementos e JOIN prendas p ON p.id = e.prenda_id "
        "WHERE e.atuendo_id = ? ORDER BY e.rowid",
        (atuendo["id"],),
    )
    atuendo["elementos"] = [{"rol": p.pop("rol"), "prenda": preparar_prenda(p)} for p in prendas]
    return atuendo


@aplicacion.post("/api/atuendos", status_code=201)
def guardar_atuendo(datos: AtuendoNuevo, usuario: dict = Depends(usuario_actual)):
    if not datos.elementos:
        raise HTTPException(422, "El atuendo necesita al menos una prenda")
    for elemento in datos.elementos:
        buscar_prenda(elemento.prenda_id, usuario)  # comprueba que cada prenda sea del usuario

    atuendo_id = ejecutar(
        "INSERT INTO atuendos (usuario_id, puntuacion, reporte_clima, fecha_creacion) VALUES (?, ?, ?, datetime('now'))",
        (usuario["id"], datos.puntuacion, json.dumps(datos.reporte_clima)),
    )
    for elemento in datos.elementos:
        ejecutar(
            "INSERT INTO atuendo_elementos (atuendo_id, prenda_id, rol) VALUES (?, ?, ?)",
            (atuendo_id, elemento.prenda_id, elemento.rol),
        )
    return leer_atuendo(consultar_uno("SELECT * FROM atuendos WHERE id = ?", (atuendo_id,)))


@aplicacion.get("/api/atuendos")
def listar_atuendos(usuario: dict = Depends(usuario_actual)):
    atuendos = consultar("SELECT * FROM atuendos WHERE usuario_id = ? ORDER BY id DESC", (usuario["id"],))
    return [leer_atuendo(a) for a in atuendos]


@aplicacion.delete("/api/atuendos/{atuendo_id}", status_code=204)
def eliminar_atuendo(atuendo_id: int, usuario: dict = Depends(usuario_actual)):
    if not consultar_uno("SELECT id FROM atuendos WHERE id = ? AND usuario_id = ?", (atuendo_id, usuario["id"])):
        raise HTTPException(404, "Atuendo no encontrado")
    ejecutar("DELETE FROM atuendos WHERE id = ?", (atuendo_id,))


# ============================================================
# ESTADÍSTICAS (datos para las gráficas de la app)
# ============================================================

def redactar_hallazgo(prendas: list[dict], por_categoria: dict, neutras: int) -> str:
    """Una frase que explica lo más importante del armario, como la anotación de una gráfica."""
    if not prendas:
        return "Agrega prendas para ver las estadísticas de tu armario."
    faltantes = [c.replace("_", " ") for c in CATEGORIAS[:3] if por_categoria[c] == 0]
    if faltantes:
        return f"No tienes {' ni '.join(faltantes)}: sin eso no se puede armar un atuendo completo."
    porcentaje = round(100 * neutras / len(prendas))
    if porcentaje >= 50:
        return f"El {porcentaje} % de tu armario es de color neutro: combina con casi todo."
    return f"Solo el {porcentaje} % de tu armario es neutro: agrega básicos para tener más combinaciones."


def historial_de_prendas(prendas: list[dict]) -> dict:
    """Prendas acumuladas por día en que se agregaron: total y por categoría."""
    dias = sorted({str(p["fecha_creacion"])[:10] for p in prendas if p["fecha_creacion"]})
    if not dias:
        return {"fechas": [], "total": [], "por_categoria": {}}

    def acumulado(filtro):
        conteo = Counter(str(p["fecha_creacion"])[:10] for p in prendas if filtro(p) and p["fecha_creacion"])
        total, serie = 0, []
        for dia in dias:
            total += conteo.get(dia, 0)
            serie.append(total)
        return serie

    return {
        "fechas": dias,
        "total": acumulado(lambda p: True),
        "por_categoria": {c: acumulado(lambda p, c=c: p["categoria"] == c) for c in CATEGORIAS},
    }


@aplicacion.get("/api/estadisticas")
def ver_estadisticas(usuario: dict = Depends(usuario_actual)):
    prendas = consultar("SELECT * FROM prendas WHERE usuario_id = ?", (usuario["id"],))
    por_categoria = {c: 0 for c in CATEGORIAS} | Counter(p["categoria"] for p in prendas)
    por_color = dict(Counter(p["color_principal"] for p in prendas).most_common())
    por_nivel = {str(n): 0 for n in range(1, 6)} | Counter(str(p["nivel_abrigo"]) for p in prendas)
    neutras = sum(p["color_principal"] in COLORES_NEUTROS for p in prendas)
    guardados = consultar_uno("SELECT COUNT(*) AS total FROM atuendos WHERE usuario_id = ?", (usuario["id"],))

    # Mapa de calor: cuántas prendas hay en cada categoría y color, y cuántas son impermeables.
    mapa = {c: {color: 0 for color in COLORES} for c in CATEGORIAS}
    mapa_impermeables = {c: {color: 0 for color in COLORES} for c in CATEGORIAS}
    for p in prendas:
        mapa[p["categoria"]][p["color_principal"]] += 1
        if p["impermeable"]:
            mapa_impermeables[p["categoria"]][p["color_principal"]] += 1

    return {
        "indicadores": {
            "total_prendas": len(prendas),
            "color_mas_usado": next(iter(por_color), None),
            "impermeables": sum(bool(p["impermeable"]) for p in prendas),
            "atuendos_guardados": guardados["total"],
        },
        "por_categoria": por_categoria,
        "por_color": por_color,
        "por_nivel_abrigo": por_nivel,
        "hallazgo": redactar_hallazgo(prendas, por_categoria, neutras),
        "mapa": mapa,
        "mapa_impermeables": mapa_impermeables,
        "historial": historial_de_prendas(prendas),
    }


@aplicacion.get("/api/salud")
def verificar_salud():
    return {"estado": "ok"}
