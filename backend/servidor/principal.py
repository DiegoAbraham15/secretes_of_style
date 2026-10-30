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

from servidor.algoritmos import ALGORITMOS
from servidor.aprendizaje import (ACCESORIOS, CANDIDATOS, PESOS_DE_RESPUESTA, RESPUESTA_POR_DEFECTO, caracteristicas_de,
                                  entrenar, firma_de, pesos_iniciales, reordenar)
from servidor.base_datos import CARPETA_ARCHIVOS, consultar, consultar_uno, crear_tablas, ejecutar
from servidor.busqueda import recomendar
from servidor.clima import obtener_clima
from servidor.explicacion import explicar_atuendo
from servidor.logica import COLORES_NEUTROS, COLORES_VIVOS, ESTAMPADOS, ESTILOS, OCASIONES, hechos_de_ocasion
from servidor.seguridad import crear_token, generar_hash, usuario_actual, verificar_contraseña
from servidor.vision import detectar_prenda

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
    return {**usuario, "cuestionario_listo": leer_preferencias(usuario["id"]) is not None}


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


def revisar_imagen(contenido: bytes) -> str:
    """Rechaza archivos muy pesados o que no son imagen; devuelve la extensión."""
    if len(contenido) > MAXIMO_IMAGEN_MB * 1024 * 1024:
        raise HTTPException(413, f"La imagen supera {MAXIMO_IMAGEN_MB} MB")
    extension = extension_de_imagen(contenido)
    if extension is None:
        raise HTTPException(415, "El archivo no es una imagen JPG, PNG, WEBP o HEIC.")
    return extension


async def guardar_imagen(archivo: UploadFile, carpeta: str) -> str:
    """Guarda la imagen en disco y devuelve su ruta pública, p. ej. /archivos/prendas/abc.jpg."""
    contenido = await archivo.read(MAXIMO_IMAGEN_MB * 1024 * 1024 + 1)  # un byte de más basta para saber si se pasa
    extension = revisar_imagen(contenido)

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
    estampado: str = Form("liso"),
    estilo: str = Form("casual"),
    usuario: dict = Depends(usuario_actual),
):
    if categoria not in CATEGORIAS or color_principal not in COLORES or not 1 <= nivel_abrigo <= 5:
        raise HTTPException(422, "Revisa la categoría, el color y el nivel de abrigo (1 a 5)")
    if estampado not in ESTAMPADOS or estilo not in ESTILOS:
        raise HTTPException(422, "Revisa el estampado y el estilo")

    prenda_id = ejecutar(
        "INSERT INTO prendas (usuario_id, url_imagen, categoria, subcategoria, color_principal, nivel_abrigo,"
        " impermeable, estampado, estilo, estado, fecha_creacion)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'disponible', datetime('now'))",
        (usuario["id"], await guardar_imagen(imagen, "prendas"), categoria, subcategoria.strip()[:60] or None,
         color_principal, nivel_abrigo, impermeable, estampado, estilo),
    )
    return buscar_prenda(prenda_id, usuario)


@aplicacion.post("/api/prendas/analizar")
def analizar_prenda(imagen: UploadFile = File(...), _usuario: dict = Depends(usuario_actual)):
    """Datos de la prenda que propone el modelo de visión para llenar el formulario. No guarda nada.

    Es def (no async) para que FastAPI la corra en otro hilo mientras Ollama responde.
    """
    contenido = imagen.file.read(MAXIMO_IMAGEN_MB * 1024 * 1024 + 1)
    revisar_imagen(contenido)
    return detectar_prenda(contenido)


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


class CambioEstilo(BaseModel):
    estampado: str
    estilo: str


@aplicacion.patch("/api/prendas/{prenda_id}/estilo")
def cambiar_estilo(prenda_id: int, datos: CambioEstilo, usuario: dict = Depends(usuario_actual)):
    """Corrige el estampado y el estilo, p. ej. de prendas registradas antes de que existieran."""
    buscar_prenda(prenda_id, usuario)
    if datos.estampado not in ESTAMPADOS or datos.estilo not in ESTILOS:
        raise HTTPException(422, "Revisa el estampado y el estilo")
    ejecutar("UPDATE prendas SET estampado = ?, estilo = ? WHERE id = ?", (datos.estampado, datos.estilo, prenda_id))
    return buscar_prenda(prenda_id, usuario)


@aplicacion.post("/api/prendas/{prenda_id}/detectar-estilo")
def detectar_estilo(prenda_id: int, usuario: dict = Depends(usuario_actual)):
    """La IA vuelve a mirar la foto guardada y actualiza el estampado y el estilo.

    Sirve para las prendas registradas antes de la IA, que quedaron como lisas y casuales.
    """
    prenda = buscar_prenda(prenda_id, usuario)
    foto = CARPETA_ARCHIVOS / prenda["url_imagen"].removeprefix("/archivos/")
    if not foto.exists():
        raise HTTPException(404, "La foto de la prenda ya no existe")
    deteccion = detectar_prenda(foto.read_bytes())
    estampado = deteccion["estampado"] or prenda["estampado"]
    estilo = deteccion["estilo"] or prenda["estilo"]
    ejecutar("UPDATE prendas SET estampado = ?, estilo = ? WHERE id = ?", (estampado, estilo, prenda_id))
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

def leer_pesos(usuario_id: int) -> dict:
    fila = consultar_uno("SELECT pesos FROM pesos_usuario WHERE usuario_id = ?", (usuario_id,))
    return json.loads(fila["pesos"]) if fila else {}  # sin votos: pesos en cero, el orden de A*


def leer_votos(usuario_id: int) -> list[dict]:
    """Los votos de la persona, del más viejo al más nuevo."""
    votos = consultar("SELECT firma, me_gusta, caracteristicas FROM votos_atuendo WHERE usuario_id = ? ORDER BY id", (usuario_id,))
    return [{**v, "caracteristicas": json.loads(v["caracteristicas"])} for v in votos]


def leer_preferencias(usuario_id: int) -> dict | None:
    return consultar_uno("SELECT * FROM preferencias_usuario WHERE usuario_id = ?", (usuario_id,))


def reentrenar(usuario_id: int) -> int:
    """Vuelve a calcular los pesos con el cuestionario y todos los votos; devuelve cuántos votos son."""
    votos = leer_votos(usuario_id)
    iniciales = pesos_iniciales(leer_preferencias(usuario_id) or {})
    ejecutar(
        "INSERT INTO pesos_usuario (usuario_id, pesos) VALUES (?, ?) ON CONFLICT (usuario_id) "
        "DO UPDATE SET pesos = excluded.pesos, fecha_actualizacion = CURRENT_TIMESTAMP",
        (usuario_id, json.dumps(entrenar(votos, iniciales))),
    )
    return len(votos)


def guardar_voto(usuario_id: int, prendas: list[dict], me_gusta: int) -> int:
    """Guarda el voto de un atuendo (si ya tenía, lo reemplaza), reentrena y devuelve cuántos votos hay.

    Las características se calculan aquí con las prendas de la base; no se le creen a la app.
    """
    ejecutar(
        "INSERT INTO votos_atuendo (usuario_id, firma, me_gusta, caracteristicas) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (usuario_id, firma) DO UPDATE SET me_gusta = excluded.me_gusta, caracteristicas = excluded.caracteristicas",
        (usuario_id, firma_de([p["id"] for p in prendas]), me_gusta, json.dumps(caracteristicas_de(prendas))),
    )
    return reentrenar(usuario_id)


def registrar_sin_corazon(usuario_id: int, sugerencias: list[dict]) -> None:
    """Un atuendo que se muestra cuenta como "no me gusta" hasta que reciba corazón.

    Estos atuendos ya salieron ordenados con los pesos anteriores, así que el voto se nota hasta la siguiente
    vez: si la persona les da corazón antes, el voto cambia y no se castigan.
    """
    nuevas = [s for s in sugerencias if s["voto"] is None]
    for sugerencia in nuevas:
        prendas = [e["prenda"] for e in sugerencia["elementos"]]
        ejecutar(
            "INSERT INTO votos_atuendo (usuario_id, firma, me_gusta, caracteristicas) VALUES (?, ?, -1, ?) "
            "ON CONFLICT (usuario_id, firma) DO NOTHING",
            (usuario_id, firma_de([p["id"] for p in prendas]), json.dumps(caracteristicas_de(prendas))),
        )
    if nuevas:
        reentrenar(usuario_id)


class Preferencias(BaseModel):
    paleta: str = RESPUESTA_POR_DEFECTO["paleta"]
    ropa: str = RESPUESTA_POR_DEFECTO["ropa"]
    estampados: str = RESPUESTA_POR_DEFECTO["estampados"]
    accesorios: str = RESPUESTA_POR_DEFECTO["accesorios"]


@aplicacion.put("/api/preferencias")
def guardar_preferencias(datos: Preferencias, usuario: dict = Depends(usuario_actual)):
    """Guarda el cuestionario de estilo y recalcula los pesos sin perder los votos. Omitirlo manda los valores por defecto."""
    if (datos.paleta not in PESOS_DE_RESPUESTA["paleta"] or datos.ropa not in PESOS_DE_RESPUESTA["ropa"]
            or datos.estampados not in PESOS_DE_RESPUESTA["estampados"] or datos.accesorios not in ACCESORIOS):
        raise HTTPException(422, "Revisa las respuestas del cuestionario")
    ejecutar(
        "INSERT INTO preferencias_usuario (usuario_id, paleta, ropa, estampados, accesorios) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (usuario_id) DO UPDATE SET paleta = excluded.paleta, ropa = excluded.ropa, "
        "estampados = excluded.estampados, accesorios = excluded.accesorios, fecha_actualizacion = CURRENT_TIMESTAMP",
        (usuario["id"], datos.paleta, datos.ropa, datos.estampados, datos.accesorios),
    )
    reentrenar(usuario["id"])
    return leer_preferencias(usuario["id"])


class SolicitudRecomendacion(BaseModel):
    prenda_base_id: int
    latitud: float
    longitud: float
    cantidad: int = Field(default=3, ge=1, le=10)
    algoritmo: str = "astar"  # la app no lo manda: siempre usa A*
    ocasion: str = "diario"


@aplicacion.post("/api/recomendaciones")
def generar_recomendaciones(datos: SolicitudRecomendacion, usuario: dict = Depends(usuario_actual)):
    """Los mejores atuendos con la prenda base según A* (u otro algoritmo), el clima real y la ocasión.

    Con A*, que es lo que usa la app, se piden más candidatos y el perceptrón los ordena según los gustos de la
    persona. Los otros algoritmos no pasan por él: existen para compararlos y deben devolver su propio resultado.
    """
    if datos.algoritmo not in ALGORITMOS:
        raise HTTPException(422, f"El algoritmo debe ser uno de: {', '.join(ALGORITMOS)}")
    if datos.ocasion not in OCASIONES:
        raise HTTPException(422, f"La ocasión debe ser una de: {', '.join(OCASIONES)}")
    base = buscar_prenda(datos.prenda_base_id, usuario)
    clima = obtener_clima(datos.latitud, datos.longitud)
    armario = [preparar_prenda(p) for p in consultar("SELECT * FROM prendas WHERE usuario_id = ?", (usuario["id"],))]
    hechos = set(clima["hechos"]) | hechos_de_ocasion(datos.ocasion)
    con_gustos = datos.algoritmo == "astar"
    cantidad = max(datos.cantidad, CANDIDATOS) if con_gustos else datos.cantidad
    preferencias = leer_preferencias(usuario["id"]) or {}
    sugerencias = recomendar(base, armario, hechos, cantidad, ALGORITMOS[datos.algoritmo],
                             con_accesorio=preferencias.get("accesorios") != "casi_nunca")
    if con_gustos:
        votos = leer_votos(usuario["id"])
        gustados = [v["caracteristicas"] for v in votos if v["me_gusta"] == 1]
        por_firma = {v["firma"]: v["me_gusta"] for v in votos}
        ordenadas = reordenar(sugerencias["sugerencias"], leer_pesos(usuario["id"]), por_firma, gustados)
        sugerencias["sugerencias"] = ordenadas[:datos.cantidad]
        registrar_sin_corazon(usuario["id"], sugerencias["sugerencias"])
    return {"clima": clima, "prenda_base": base, "ocasion": datos.ocasion, **sugerencias}


class SolicitudExplicacion(BaseModel):
    prenda_ids: list[int] = Field(min_length=1, max_length=6)  # la primera es la prenda base
    latitud: float
    longitud: float
    ocasion: str = "diario"


@aplicacion.post("/api/recomendaciones/explicacion")
def explicar_recomendacion(datos: SolicitudExplicacion, usuario: dict = Depends(usuario_actual)):
    """Por qué funciona un atuendo, en lenguaje natural. Los hechos los pone la lógica; la IA solo redacta.

    Es def (no async) para que FastAPI la corra en otro hilo mientras Ollama responde.
    """
    if datos.ocasion not in OCASIONES:
        raise HTTPException(422, f"La ocasión debe ser una de: {', '.join(OCASIONES)}")
    prendas = [buscar_prenda(prenda_id, usuario) for prenda_id in datos.prenda_ids]
    clima = obtener_clima(datos.latitud, datos.longitud)  # se reutiliza el de la recomendación (caché de 30 min)
    return {"explicacion": explicar_atuendo(prendas, clima, datos.ocasion)}


class VotoAtuendo(BaseModel):
    prenda_ids: list[int] = Field(min_length=2, max_length=6)
    me_gusta: bool


@aplicacion.post("/api/atuendos/voto")
def votar_atuendo(datos: VotoAtuendo, usuario: dict = Depends(usuario_actual)):
    """Poner o quitar el corazón de un atuendo."""
    if len(set(datos.prenda_ids)) != len(datos.prenda_ids):
        raise HTTPException(422, "Un atuendo no puede repetir prendas")
    prendas = [buscar_prenda(prenda_id, usuario) for prenda_id in datos.prenda_ids]
    me_gusta = 1 if datos.me_gusta else -1
    return {"voto": me_gusta, "votos": guardar_voto(usuario["id"], prendas, me_gusta)}


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
    # buscar_prenda comprueba que cada prenda sea del usuario.
    prendas = [buscar_prenda(elemento.prenda_id, usuario) for elemento in datos.elementos]

    atuendo_id = ejecutar(
        "INSERT INTO atuendos (usuario_id, puntuacion, reporte_clima, fecha_creacion) VALUES (?, ?, ?, datetime('now'))",
        (usuario["id"], datos.puntuacion, json.dumps(datos.reporte_clima)),
    )
    for elemento in datos.elementos:
        ejecutar(
            "INSERT INTO atuendo_elementos (atuendo_id, prenda_id, rol) VALUES (?, ?, ?)",
            (atuendo_id, elemento.prenda_id, elemento.rol),
        )
    guardar_voto(usuario["id"], prendas, 1)  # guardar un atuendo cuenta como darle corazón
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
