"""API de Secrets of Style.

Ejecutar desde la carpeta backend:
    uvicorn servidor.principal:aplicacion --reload --host 0.0.0.0 --port 8000
"""

import secrets
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from servidor import (base_datos, busqueda_imagen, capsulas, colorimetria, compra, digitalizar, gpu, probador, rescate,
                      tiendas, viaje)
from servidor.algoritmos import ALGORITMOS
from servidor.aprendizaje import (ACCESORIOS, CANDIDATOS, PESOS_DE_RESPUESTA, RESPUESTA_POR_DEFECTO, caracteristicas_de,
                                  entrenar, firma_de, pesos_iniciales, reordenar)
from servidor.archivos import MAXIMO_IMAGEN_MB, borrar_imagen, guardar_imagen, revisar_imagen, ruta_de
from servidor.base_datos import CARPETA_ARCHIVOS, ahora, bd, como_dict, crear_colecciones, siguiente_id
from servidor.busqueda import recomendar
from servidor.clima import obtener_clima
from servidor.consultas import preferencias_de, prendas_de, uso_por_prenda, votos_de
from servidor.esquemas import CATEGORIAS, ESTADOS_PRENDA as ESTADOS, TEMPORADAS
from servidor.explicacion import explicar_atuendo
from limpieza_de_datos.limpieza_de_datos import limpiar_votos  # LIMPIEZA de datos (carpeta limpieza_de_datos/)
from limpieza_de_datos.rutas import rutas as rutas_limpieza  # LIMPIEZA de datos: votos, prendas y evaluación
from servidor.logica import COLORES, COLORES_NEUTROS, ESTAMPADOS, ESTILOS, OCASIONES, hechos_de_ocasion
from servidor.red_convolucional import probabilidades  # CNN 1D (entrenada aparte en entrenamiento_cnn/)
from servidor.seguridad import crear_token, generar_hash, usuario_actual, verificar_contraseña
from servidor.vision import detectar_para_tienda, detectar_prenda

LIMITE_LECTURA = MAXIMO_IMAGEN_MB * 1024 * 1024 + 1  # un byte de más basta para saber si se pasa
# CORS solo aplica a la versión web (la app del teléfono no lo usa): se permite la computadora
# y las IP de la red local, que es desde donde Expo sirve la app.
ORIGENES_PERMITIDOS = (
    r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+"
    r"|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?"
)

crear_colecciones()
CARPETA_ARCHIVOS.mkdir(exist_ok=True)

@asynccontextmanager
async def al_arrancar(_aplicacion):
    probador.iniciar()  # el hilo que atiende la cola del probador virtual
    yield


aplicacion = FastAPI(title="Secrets of Style", lifespan=al_arrancar)
aplicacion.add_middleware(
    CORSMiddleware,
    allow_origin_regex=ORIGENES_PERMITIDOS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
aplicacion.mount("/archivos", StaticFiles(directory=CARPETA_ARCHIVOS), name="archivos")
aplicacion.include_router(rutas_limpieza)  # LIMPIEZA de datos: rutas de limpieza_de_datos/rutas.py


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
    if bd().usuarios.find_one({"correo": correo}, {"_id": 1}):
        raise HTTPException(409, "Ese correo ya está registrado")

    usuario_id = siguiente_id("usuarios")
    try:
        bd().usuarios.insert_one({
            "_id": usuario_id, "correo": correo, "contraseña_hash": generar_hash(datos.contraseña),
            "version_sesion": 0, "fecha_creacion": ahora(), "perfil": dict(PERFIL_VACIO),
        })
    except DuplicateKeyError:  # el índice único de correo frena dos registros iguales al mismo tiempo
        raise HTTPException(409, "Ese correo ya está registrado")
    return respuesta_token({"id": usuario_id, "correo": correo})


@aplicacion.post("/api/auth/login")
def iniciar_sesion(datos: Cuenta):
    # El correo siempre es texto: Pydantic rechaza un objeto como {"$ne": ""} (inyección NoSQL) con 422.
    usuario = como_dict(bd().usuarios.find_one({"correo": datos.correo.strip().lower()}))
    if not usuario or not verificar_contraseña(datos.contraseña, usuario["contraseña_hash"]):
        raise HTTPException(401, "Correo o contraseña incorrectos")
    return respuesta_token(usuario)


@aplicacion.get("/api/auth/yo")
def usuario_de_la_sesion(usuario: dict = Depends(usuario_actual)):
    return {**usuario, "cuestionario_listo": leer_preferencias(usuario["id"]) is not None}


@aplicacion.post("/api/auth/cerrar-sesion", status_code=204)
def cerrar_sesion(usuario: dict = Depends(usuario_actual)):
    """Sube la versión de sesión: todos los tokens emitidos hasta ahora dejan de ser válidos."""
    bd().usuarios.update_one({"_id": usuario["id"]}, {"$inc": {"version_sesion": 1}})


# ============================================================
# PERFIL
# ============================================================

# El perfil va embebido en el documento del usuario (relación 1:1): la foto de cuerpo del probador y su versión.
PERFIL_VACIO = {"foto_cuerpo": None, "version_foto": 0}


def leer_perfil(usuario_id: int) -> dict:
    usuario = bd().usuarios.find_one({"_id": usuario_id}, {"perfil": 1}) or {}
    perfil = {"usuario_id": usuario_id, **PERFIL_VACIO, **usuario.get("perfil", {})}
    perfil["tiene_foto"] = perfil.pop("foto_cuerpo") is not None  # la ruta privada no sale del servidor
    return perfil


@aplicacion.get("/api/perfil")
def ver_perfil(usuario: dict = Depends(usuario_actual)):
    return leer_perfil(usuario["id"])


# ============================================================
# ARMARIO
# ============================================================

def leer_imagen(archivo: UploadFile) -> tuple[bytes, str]:
    """Lee la imagen que mandó la app sin pasar del límite y la revisa; devuelve (contenido, extensión)."""
    contenido = archivo.file.read(LIMITE_LECTURA)
    return contenido, revisar_imagen(contenido)


def preparar_prenda(prenda: dict) -> dict:
    return como_dict(prenda)  # _id pasa a id y la fecha a texto "AAAA-MM-DD HH:MM:SS", el formato que usa la app


def buscar_prenda(prenda_id: int, usuario: dict) -> dict:
    """La prenda, solo si es de la persona: el filtro lleva siempre usuario_id."""
    prenda = bd().prendas.find_one({"_id": prenda_id, "usuario_id": usuario["id"]})
    if prenda is None:
        raise HTTPException(404, "Prenda no encontrada")
    return preparar_prenda(prenda)


def prendas_del_atuendo(prenda_ids: list[int], usuario: dict) -> list[dict]:
    """Las prendas de un atuendo: sin repetir (si no, 422) y todas de la persona (si no, 404)."""
    if len(set(prenda_ids)) != len(prenda_ids):
        raise HTTPException(422, "Un atuendo no puede repetir prendas")
    return [buscar_prenda(prenda_id, usuario) for prenda_id in prenda_ids]


class DatosPrenda(BaseModel):
    """Los datos de una prenda: al confirmar un borrador (todos) o al editarla (solo los que cambian)."""
    categoria: str | None = None
    subcategoria: str | None = Field(default=None, max_length=60)
    color_principal: str | None = None
    nivel_abrigo: int | None = None
    impermeable: bool | None = None
    estampado: str | None = None
    estilo: str | None = None
    temporada: str | None = None
    precio_compra: float | None = Field(default=None, ge=0, le=1_000_000)
    fecha_adquisicion: str | None = None


def validar_prenda(datos: dict) -> dict:
    """Revisa los campos que vienen (los que no, se dejan) y los deja listos para guardar."""
    reglas = [
        ("categoria", lambda v: v in CATEGORIAS, "Revisa la categoría"),
        ("color_principal", lambda v: v in COLORES, "Revisa el color"),
        ("nivel_abrigo", lambda v: isinstance(v, int) and 1 <= v <= 5, "El nivel de abrigo va de 1 a 5"),
        ("estampado", lambda v: v in ESTAMPADOS, "Revisa el estampado"),
        ("estilo", lambda v: v in ESTILOS, "Revisa el estilo"),
        ("temporada", lambda v: v in TEMPORADAS, "Revisa la temporada"),
    ]
    for campo, valido, mensaje in reglas:
        if datos.get(campo) is not None and not valido(datos[campo]):
            raise HTTPException(422, mensaje)
    if "subcategoria" in datos:
        datos["subcategoria"] = (datos["subcategoria"] or "").strip()[:60] or None
    if datos.get("fecha_adquisicion"):
        if leer_fecha(datos["fecha_adquisicion"]) > ahora().date() + timedelta(days=1):
            raise HTTPException(422, "La fecha de compra no puede ser en el futuro")
    return datos


@aplicacion.post("/api/prendas", status_code=201)
def subir_prenda(
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
    validar_prenda({"categoria": categoria, "color_principal": color_principal, "nivel_abrigo": nivel_abrigo,
                    "estampado": estampado, "estilo": estilo})
    url_imagen = guardar_imagen(*leer_imagen(imagen), "prendas")
    prenda_id = siguiente_id("prendas")
    bd().prendas.insert_one({
        "_id": prenda_id, "usuario_id": usuario["id"], "url_imagen": url_imagen, "categoria": categoria,
        "subcategoria": subcategoria.strip()[:60] or None, "color_principal": color_principal,
        "nivel_abrigo": nivel_abrigo, "impermeable": impermeable, "estampado": estampado, "estilo": estilo,
        "estado": "disponible", "fecha_creacion": ahora(),
    })
    return buscar_prenda(prenda_id, usuario)


@aplicacion.post("/api/prendas/analizar")
def analizar_prenda(imagen: UploadFile = File(...), _usuario: dict = Depends(usuario_actual)):
    """Datos de la prenda que propone el modelo de visión para llenar el formulario. No guarda nada.

    Es def (no async) para que FastAPI la corra en otro hilo mientras Ollama responde.
    """
    contenido, _ = leer_imagen(imagen)
    return detectar_prenda(contenido)


SIN_USO = {"veces": 0, "ultimo": None}


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
    filtro = {"usuario_id": usuario["id"], "nivel_abrigo": {"$gte": nivel_abrigo_minimo, "$lte": nivel_abrigo_maximo}}
    # Cada filtro opcional agrega una condición. FastAPI ya los convirtió a str, bool o int: no llegan operadores.
    for campo, valor in [("categoria", categoria), ("color_principal", color_principal),
                         ("estado", estado), ("impermeable", impermeable)]:
        if valor is not None:
            filtro[campo] = valor
    usos = uso_por_prenda(usuario["id"])
    return [{**preparar_prenda(p), "uso": usos.get(p["_id"], SIN_USO)} for p in bd().prendas.find(filtro).sort("_id", -1)]


# ---------- Digitalización: borradores (ver digitalizar.py) ----------

def como_borrador(documento: dict) -> dict:
    borrador = como_dict(documento)
    borrador.pop("huella", None)
    return borrador


def buscar_borrador(borrador_id: int, usuario: dict) -> dict:
    borrador = bd().borradores.find_one({"_id": borrador_id, "usuario_id": usuario["id"]})
    if borrador is None:
        raise HTTPException(404, "Esa foto ya no está por confirmar")
    return borrador


@aplicacion.post("/api/prendas/borradores", status_code=201)
def crear_borrador(imagen: UploadFile = File(...), usuario: dict = Depends(usuario_actual)):
    """Sube una foto: queda en la fila y la IA y el motor la procesan en segundo plano (consulta con GET)."""
    contenido, extension = leer_imagen(imagen)
    return como_borrador(digitalizar.crear_borrador(usuario["id"], contenido, extension, {"tipo": "foto"}))


class ImportarUrl(BaseModel):
    url: str = Field(min_length=8, max_length=2000)


@aplicacion.post("/api/prendas/borradores/url", status_code=201)
def importar_borrador(datos: ImportarUrl, usuario: dict = Depends(usuario_actual)):
    """El link de una tienda (o de una imagen): baja la foto, el nombre y el precio, y la procesa como las demás."""
    contenido, extension, pagina = digitalizar.importar_url(datos.url)
    origen = {"tipo": "url", "url_tienda": pagina["url_tienda"], "titulo": pagina["titulo"]}
    propuesta = {"precio_compra": pagina["precio"]} if pagina["precio"] else {}
    return como_borrador(digitalizar.crear_borrador(usuario["id"], contenido, extension, origen, propuesta))


@aplicacion.get("/api/prendas/borradores")
def listar_borradores(usuario: dict = Depends(usuario_actual)):
    """Las fotos por confirmar, de la más vieja a la más nueva (también las de una carga anterior)."""
    digitalizar.limpiar_borradores(usuario["id"])
    return [como_borrador(b) for b in bd().borradores.find({"usuario_id": usuario["id"]}).sort("_id", 1)]


@aplicacion.get("/api/prendas/borradores/{borrador_id}")
def ver_borrador(borrador_id: int, usuario: dict = Depends(usuario_actual)):
    return como_borrador(buscar_borrador(borrador_id, usuario))


@aplicacion.post("/api/prendas/borradores/{borrador_id}/reintentar")
def reintentar_borrador(borrador_id: int, usuario: dict = Depends(usuario_actual)):
    borrador = buscar_borrador(borrador_id, usuario)
    if borrador["estado"] in ("en_fila", "analizando"):
        return como_borrador(borrador)
    bd().borradores.update_one({"_id": borrador_id}, {"$set": {"estado": "en_fila", "avisos": []}})
    digitalizar.encolar(digitalizar.procesar_borrador, borrador_id)
    return como_borrador(buscar_borrador(borrador_id, usuario))


@aplicacion.post("/api/prendas/borradores/{borrador_id}/confirmar", status_code=201)
def confirmar_borrador(borrador_id: int, datos: DatosPrenda, usuario: dict = Depends(usuario_actual)):
    """Con los datos que revisó la persona, el borrador se vuelve una prenda del armario."""
    borrador = buscar_borrador(borrador_id, usuario)
    valores = validar_prenda(datos.model_dump())
    if not (valores["categoria"] and valores["color_principal"] and valores["nivel_abrigo"]):
        raise HTTPException(422, "Falta la categoría, el color o el nivel de abrigo")
    origen = borrador.get("origen") or {"tipo": "foto"}
    prenda_id = siguiente_id("prendas")
    bd().prendas.insert_one({
        "_id": prenda_id, "usuario_id": usuario["id"], "url_imagen": borrador["url_imagen"],
        "url_original": borrador["url_original"], "sin_fondo": bool(borrador.get("sin_fondo")),
        "huella": borrador.get("huella"), "color_hex": borrador["propuesta"].get("color_hex"),
        "categoria": valores["categoria"], "subcategoria": valores.get("subcategoria"),
        "color_principal": valores["color_principal"], "nivel_abrigo": valores["nivel_abrigo"],
        "impermeable": bool(valores.get("impermeable")), "estampado": valores.get("estampado") or "liso",
        "estilo": valores.get("estilo") or "casual",
        "temporada": valores.get("temporada") or digitalizar.temporada_de(valores["nivel_abrigo"]),
        "precio_compra": valores.get("precio_compra"), "fecha_adquisicion": valores.get("fecha_adquisicion"),
        "origen": origen, "estado": "disponible", "fecha_creacion": ahora(),
    })
    bd().borradores.delete_one({"_id": borrador_id})  # las fotos ya son de la prenda
    return buscar_prenda(prenda_id, usuario)


@aplicacion.delete("/api/prendas/borradores/{borrador_id}", status_code=204)
def descartar_borrador(borrador_id: int, usuario: dict = Depends(usuario_actual)):
    digitalizar.descartar(buscar_borrador(borrador_id, usuario))


@aplicacion.get("/api/prendas/{prenda_id}")
def ver_prenda(prenda_id: int, usuario: dict = Depends(usuario_actual)):
    """La prenda con su uso (veces y última vez) y, si tiene precio, su costo por puesta."""
    prenda = buscar_prenda(prenda_id, usuario)
    uso = uso_por_prenda(usuario["id"]).get(prenda_id, SIN_USO)
    costo = round(prenda["precio_compra"] / max(uso["veces"], 1), 2) if prenda.get("precio_compra") else None
    dias = (ahora().date() - date.fromisoformat(uso["ultimo"])).days if uso["ultimo"] else None
    return {**prenda, "uso": {**uso, "dias_sin_usar": dias}, "costo_por_uso": costo}


class CambioEstado(BaseModel):
    estado: str


@aplicacion.patch("/api/prendas/{prenda_id}/estado")
def cambiar_estado(prenda_id: int, datos: CambioEstado, usuario: dict = Depends(usuario_actual)):
    buscar_prenda(prenda_id, usuario)
    if datos.estado not in ESTADOS:
        raise HTTPException(422, "El estado debe ser disponible, en_lavado o archivada")
    bd().prendas.update_one({"_id": prenda_id}, {"$set": {"estado": datos.estado}})
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
    bd().prendas.update_one({"_id": prenda_id}, {"$set": {"estampado": datos.estampado, "estilo": datos.estilo}})
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
    bd().prendas.update_one({"_id": prenda_id}, {"$set": {"estampado": estampado, "estilo": estilo}})
    return buscar_prenda(prenda_id, usuario)


@aplicacion.patch("/api/prendas/{prenda_id}")
def editar_prenda(prenda_id: int, datos: DatosPrenda, usuario: dict = Depends(usuario_actual)):
    """Corrige cualquier dato de la prenda (también precio, fecha de compra y temporada). Lo que no viene, se queda."""
    buscar_prenda(prenda_id, usuario)
    cambios = validar_prenda(datos.model_dump(exclude_unset=True))
    for campo in ("categoria", "color_principal", "nivel_abrigo", "impermeable", "estampado", "estilo"):
        if campo in cambios and cambios[campo] is None:
            raise HTTPException(422, "Ese dato no se puede dejar vacío")
    if cambios:
        bd().prendas.update_one({"_id": prenda_id}, {"$set": cambios})
    return buscar_prenda(prenda_id, usuario)


@aplicacion.post("/api/prendas/{prenda_id}/quitar-fondo")
def quitar_fondo_prenda(prenda_id: int, usuario: dict = Depends(usuario_actual)):
    """Para las prendas de antes: el motor le quita el fondo y se mide su color. La foto original se guarda."""
    prenda = buscar_prenda(prenda_id, usuario)
    if prenda.get("sin_fondo"):
        return prenda
    original = prenda.get("url_original") or prenda["url_imagen"]
    if not ruta_de(original).is_file():
        raise HTTPException(404, "La foto de la prenda ya no existe")
    sin_fondo = digitalizar.quitar_fondo(original)
    if sin_fondo is None:
        raise HTTPException(503, "El motor está apagado: abre backend\\motor para quitar el fondo")
    medido = digitalizar.color_dominante(ruta_de(sin_fondo))
    bd().prendas.update_one({"_id": prenda_id}, {"$set": {
        "url_imagen": sin_fondo, "url_original": original, "sin_fondo": True,
        "color_hex": medido[0] if medido else prenda.get("color_hex")}})
    probador.olvidar_prenda(usuario["id"], prenda_id)  # las pruebas viejas usaban la foto con fondo
    return buscar_prenda(prenda_id, usuario)


@aplicacion.delete("/api/prendas/{prenda_id}", status_code=204)
def eliminar_prenda(prenda_id: int, usuario: dict = Depends(usuario_actual)):
    prenda = buscar_prenda(prenda_id, usuario)
    bd().prendas.delete_one({"_id": prenda_id})
    # MongoDB no borra en cascada: también se quita de los atuendos guardados.
    bd().atuendos.update_many({"elementos.prenda_id": prenda_id}, {"$pull": {"elementos": {"prenda_id": prenda_id}}})
    bd().usos.update_many({"prenda_ids": prenda_id}, {"$pull": {"prenda_ids": prenda_id}})
    bd().usos.delete_many({"usuario_id": usuario["id"], "prenda_ids": {"$size": 0}})  # días que se quedaron sin prendas
    bd().capsulas.update_many({"usuario_id": usuario["id"]}, {"$pull": {"prenda_ids": prenda_id, "empacadas": prenda_id}})
    borrar_imagen(prenda["url_imagen"])
    if prenda.get("url_original") != prenda["url_imagen"]:
        borrar_imagen(prenda.get("url_original"))
    probador.olvidar_prenda(usuario["id"], prenda_id)


# ============================================================
# RECOMENDACIONES Y ATUENDOS
# ============================================================

def leer_pesos(usuario_id: int) -> dict:
    usuario = bd().usuarios.find_one({"_id": usuario_id}, {"pesos": 1}) or {}
    return usuario.get("pesos", {}).get("valores", {})  # sin votos: pesos en cero, el orden de A*


def leer_preferencias(usuario_id: int) -> dict | None:
    """Las respuestas del cuestionario como las responde la API; None si todavía no lo contesta."""
    preferencias = preferencias_de(usuario_id)
    return {"usuario_id": usuario_id, **como_dict(preferencias)} if preferencias else None


def reentrenar(usuario_id: int) -> int:
    """Vuelve a calcular los pesos con el cuestionario y los votos; devuelve cuántos votos son."""
    votos = votos_de(usuario_id)
    para_entrenar = votos
    para_entrenar = limpiar_votos(votos)["validos"]  # LIMPIEZA de datos: sin esta línea entrena con todos
    iniciales = pesos_iniciales(leer_preferencias(usuario_id) or {})
    pesos = {"valores": entrenar(para_entrenar, iniciales), "fecha_actualizacion": ahora()}
    bd().usuarios.update_one({"_id": usuario_id}, {"$set": {"pesos": pesos}})
    return len(votos)


def guardar_voto(usuario_id: int, prendas: list[dict], me_gusta: int) -> int:
    """Guarda el voto de un atuendo (si ya tenía, lo reemplaza), reentrena y devuelve cuántos votos hay.

    Las características se calculan aquí con las prendas de la base; no se le creen a la app.
    """
    # upsert: si ya hay voto de ese atuendo lo actualiza (conserva su _id y su lugar); si no, lo crea.
    bd().votos_atuendo.update_one(
        {"usuario_id": usuario_id, "firma": firma_de([p["id"] for p in prendas])},
        {"$set": {"me_gusta": me_gusta, "caracteristicas": caracteristicas_de(prendas)},
         "$setOnInsert": {"fecha_creacion": ahora()}},
        upsert=True,
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
        # $setOnInsert solo escribe si el voto no existía: un voto que ya tenía corazón no se toca.
        bd().votos_atuendo.update_one(
            {"usuario_id": usuario_id, "firma": firma_de([p["id"] for p in prendas])},
            {"$setOnInsert": {"me_gusta": -1, "caracteristicas": caracteristicas_de(prendas), "fecha_creacion": ahora()}},
            upsert=True,
        )
    if nuevas:
        reentrenar(usuario_id)


class Preferencias(BaseModel):
    paleta: str = RESPUESTA_POR_DEFECTO["paleta"]
    ropa: str = RESPUESTA_POR_DEFECTO["ropa"]
    estampados: str = RESPUESTA_POR_DEFECTO["estampados"]
    accesorios: str = RESPUESTA_POR_DEFECTO["accesorios"]


@aplicacion.get("/api/preferencias")
def ver_preferencias(usuario: dict = Depends(usuario_actual)):
    """Las respuestas actuales del cuestionario, para editarlas desde "Tus gustos"."""
    preferencias = leer_preferencias(usuario["id"])
    if preferencias is None:
        raise HTTPException(404, "Todavía no contestas el cuestionario")
    return preferencias


@aplicacion.put("/api/preferencias")
def guardar_preferencias(datos: Preferencias, usuario: dict = Depends(usuario_actual)):
    """Guarda el cuestionario de estilo y recalcula los pesos sin perder los votos. Omitirlo manda los valores por defecto."""
    if (datos.paleta not in PESOS_DE_RESPUESTA["paleta"] or datos.ropa not in PESOS_DE_RESPUESTA["ropa"]
            or datos.estampados not in PESOS_DE_RESPUESTA["estampados"] or datos.accesorios not in ACCESORIOS):
        raise HTTPException(422, "Revisa las respuestas del cuestionario")
    bd().usuarios.update_one({"_id": usuario["id"]}, {"$set": {"preferencias": {
        "paleta": datos.paleta, "ropa": datos.ropa, "estampados": datos.estampados, "accesorios": datos.accesorios,
        "fecha_actualizacion": ahora(),
    }}})
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
    armario = prendas_de(usuario["id"])
    hechos = set(clima["hechos"]) | hechos_de_ocasion(datos.ocasion)
    con_gustos = datos.algoritmo == "astar"
    cantidad = max(datos.cantidad, CANDIDATOS) if con_gustos else datos.cantidad
    preferencias = leer_preferencias(usuario["id"]) or {}
    sugerencias = recomendar(base, armario, hechos, cantidad, ALGORITMOS[datos.algoritmo],
                             con_accesorio=preferencias.get("accesorios") != "casi_nunca")
    if con_gustos:
        gustos = gustos_de(usuario["id"], preferencias)
        # CNN 1D: solo predice con los pesos ya entrenados; None si no hay modelo.
        cnn = probabilidades([[e["prenda"] for e in s["elementos"]] for s in sugerencias["sugerencias"]], preferencias)
        ordenadas = reordenar(sugerencias["sugerencias"], gustos["pesos"], gustos["votos"], gustos["gustados"], cnn)
        ordenadas = colorimetria.ajustar(ordenadas, gustos["colorimetria"])  # insignia y, si se pidió, prioridad
        sugerencias["sugerencias"] = ordenadas[:datos.cantidad]
        registrar_sin_corazon(usuario["id"], sugerencias["sugerencias"])
    return {"clima": clima, "prenda_base": base, "ocasion": datos.ocasion, **sugerencias}


def gustos_de(usuario_id: int, preferencias: dict) -> dict:
    """Lo que la app sabe de los gustos de la persona, para reordenar lo que propone A*."""
    votos = votos_de(usuario_id)
    return {
        "pesos": leer_pesos(usuario_id),
        "votos": {v["firma"]: v["me_gusta"] for v in votos},  # lo ya votado: +1 o -1
        "gustados": [v["caracteristicas"] for v in votos if v["me_gusta"] == 1],
        "preferencias": preferencias,
        "con_accesorio": preferencias.get("accesorios") != "casi_nunca",
        "colorimetria": leer_colorimetria(usuario_id),
    }


# ---------- Colorimetría personal (ver colorimetria.py) ----------

def leer_colorimetria(usuario_id: int) -> dict | None:
    """El diagnóstico guardado, listo para la app y para ajustar los looks; None si todavía no lo hace."""
    usuario = bd().usuarios.find_one({"_id": usuario_id}, {"colorimetria": 1}) or {}
    guardado = usuario.get("colorimetria")
    if not guardado:
        return None
    diagnostico = colorimetria.diagnosticar(guardado.get("respuestas"), guardado.get("selfie"))
    selfie = guardado.get("selfie") or {}
    return {**diagnostico, "priorizar": guardado["priorizar"], "respuestas": guardado.get("respuestas"),
            "piel_hex": (selfie.get("piel") or {}).get("hex"),
            "fecha_actualizacion": como_dict({"f": guardado["fecha_actualizacion"]})["f"]}


def guardar_colorimetria(usuario_id: int, respuestas: dict | None, selfie: dict | None) -> dict:
    anterior = (bd().usuarios.find_one({"_id": usuario_id}, {"colorimetria": 1}) or {}).get("colorimetria") or {}
    diagnostico = colorimetria.diagnosticar(respuestas, selfie)
    bd().usuarios.update_one({"_id": usuario_id}, {"$set": {"colorimetria": {
        "estacion": diagnostico["estacion"], "subtono": diagnostico["subtono"], "paleta": diagnostico["paleta"],
        "evitar": diagnostico["evitar"], "priorizar": anterior.get("priorizar", True), "respuestas": respuestas,
        "selfie": selfie, "fecha_actualizacion": ahora()}}})
    return leer_colorimetria(usuario_id)


@aplicacion.get("/api/colorimetria/preguntas")
def preguntas_de_colorimetria(_usuario: dict = Depends(usuario_actual)):
    """Las 5 preguntas visuales, con sus opciones y colores de muestra (sin los puntos)."""
    return [{**p, "opciones": [{k: v for k, v in o.items() if k != "puntos"} for o in p["opciones"]]}
            for p in colorimetria.PREGUNTAS]


@aplicacion.get("/api/colorimetria")
def ver_colorimetria(usuario: dict = Depends(usuario_actual)):
    """El diagnóstico de la persona, o null si todavía no lo hace."""
    return leer_colorimetria(usuario["id"])


class RespuestasColor(BaseModel):
    respuestas: dict[str, str]


@aplicacion.post("/api/colorimetria/cuestionario")
def contestar_colorimetria(datos: RespuestasColor, usuario: dict = Depends(usuario_actual)):
    """El cuestionario. Si ya había una selfie, se combinan."""
    try:
        colorimetria.puntos_del_cuestionario(datos.respuestas)
    except KeyError:
        raise HTTPException(422, "Contesta las 5 preguntas")
    anterior = (bd().usuarios.find_one({"_id": usuario["id"]}, {"colorimetria": 1}) or {}).get("colorimetria") or {}
    return guardar_colorimetria(usuario["id"], {k: datos.respuestas[k] for k in colorimetria.OPCIONES},
                                anterior.get("selfie"))


@aplicacion.post("/api/colorimetria/selfie")
def selfie_de_colorimetria(imagen: UploadFile | None = File(None), usar_foto_probador: bool = Form(False),
                           usuario: dict = Depends(usuario_actual)):
    """Una selfie con luz natural (o la foto del probador): el motor mide el color de la piel y del cabello.
    La selfie se borra en cuanto se mide; solo se guardan los colores. Es def: el motor tarda unos segundos."""
    temporal = None
    if usar_foto_probador:
        foto = probador.foto_de(usuario["id"]).get("foto_cuerpo")
        if not foto or not Path(foto).is_file():
            raise HTTPException(409, "Todavía no subes tu foto del probador")
    else:
        if imagen is None:
            raise HTTPException(422, "Falta la selfie")
        contenido, extension = leer_imagen(imagen)
        if extension == ".heic":
            raise HTTPException(415, "Manda la selfie en JPG o PNG.")
        carpeta = base_datos.CARPETA_PRIVADA / "selfies"
        carpeta.mkdir(parents=True, exist_ok=True)
        temporal = carpeta / f"{usuario['id']}-{secrets.token_hex(8)}{extension}"
        temporal.write_bytes(contenido)
        foto = str(temporal)
    try:
        medidas = gpu.pedir_al_motor("/colorimetria", {"foto": str(foto)}, espera=120)
    finally:
        if temporal:
            temporal.unlink(missing_ok=True)
    if not medidas.get("valida"):
        raise HTTPException(422, medidas.get("motivo") or "No se pudo leer el color de tu piel")
    anterior = (bd().usuarios.find_one({"_id": usuario["id"]}, {"colorimetria": 1}) or {}).get("colorimetria") or {}
    return guardar_colorimetria(usuario["id"], anterior.get("respuestas"),
                                {"piel": medidas["piel"], "cabello": medidas.get("cabello")})


class CambioColorimetria(BaseModel):
    priorizar: bool


@aplicacion.patch("/api/colorimetria")
def cambiar_colorimetria(datos: CambioColorimetria, usuario: dict = Depends(usuario_actual)):
    """Priorizar (o no) los colores de la paleta al ordenar los looks."""
    if leer_colorimetria(usuario["id"]) is None:
        raise HTTPException(404, "Primero haz tu diagnóstico de color")
    bd().usuarios.update_one({"_id": usuario["id"]}, {"$set": {"colorimetria.priorizar": datos.priorizar}})
    return leer_colorimetria(usuario["id"])


@aplicacion.delete("/api/colorimetria", status_code=204)
def borrar_colorimetria(usuario: dict = Depends(usuario_actual)):
    bd().usuarios.update_one({"_id": usuario["id"]}, {"$unset": {"colorimetria": ""}})


# ---------- Look del día ----------

DIAS_SIN_REPETIR = 3  # lo que te pusiste en estos días cuesta más (REPETIR de viaje.py por cada vez)


def leer_fecha(texto: str | None) -> date:
    """La fecha AAAA-MM-DD que manda el teléfono (es su día, no el del servidor en UTC); sin ella, hoy en UTC."""
    if texto is None:
        return ahora().date()
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise HTTPException(422, "La fecha debe ser AAAA-MM-DD")


class SolicitudDia(BaseModel):
    latitud: float
    longitud: float
    ocasion: str = "diario"
    fecha: str | None = None  # el día de hoy en el teléfono


@aplicacion.post("/api/recomendaciones/dia")
def look_de_hoy(datos: SolicitudDia, usuario: dict = Depends(usuario_actual)):
    """El mejor look de hoy sin elegir prenda base: A* con cada parte de arriba, tus gustos y sin repetir lo de
    los últimos días. Responde como /api/recomendaciones (con una sola sugerencia) para que la app lo muestre igual.
    """
    if datos.ocasion not in OCASIONES:
        raise HTTPException(422, f"La ocasión debe ser una de: {', '.join(OCASIONES)}")
    hoy = leer_fecha(datos.fecha)
    clima = obtener_clima(datos.latitud, datos.longitud)
    recientes = bd().usos.find({"usuario_id": usuario["id"], "fecha": {
        "$gte": (hoy - timedelta(days=DIAS_SIN_REPETIR)).isoformat(), "$lt": hoy.isoformat()}})
    usadas = Counter(i for uso in recientes for i in uso["prenda_ids"])
    preferencias = leer_preferencias(usuario["id"]) or {}
    hechos = set(clima["hechos"]) | hechos_de_ocasion(datos.ocasion)
    sugerencia, avisos = viaje.look_del_dia(prendas_de(usuario["id"]), hechos, usadas,
                                            gustos_de(usuario["id"], preferencias), maleta=False)
    sugerencias = [sugerencia] if sugerencia else []
    registrar_sin_corazon(usuario["id"], sugerencias)  # como los demás looks: sin corazón cuenta como "no me gusta"
    return {"clima": clima, "prenda_base": None, "ocasion": datos.ocasion, "sugerencias": sugerencias,
            "categorias_faltantes": [], "avisos": avisos, "del_dia": True}


# ---------- Modo viaje ----------

@aplicacion.get("/api/viaje/lugares")
def buscar_destino(nombre: str = Query(min_length=2, max_length=80), _usuario: dict = Depends(usuario_actual)):
    """Ciudades con ese nombre (Open-Meteo), para elegir a dónde se va."""
    return viaje.buscar_lugares(nombre.strip())


class SolicitudViaje(BaseModel):
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    lugar: str = Field(default="", max_length=120)
    salida: int = Field(default=0, ge=0, le=7)  # en cuántos días sale (0 = hoy)
    dias: int = Field(default=3, ge=1, le=7)  # el pronóstico confiable llega a una semana
    ocasion: str = "diario"


@aplicacion.post("/api/viaje")
def planear_viaje(datos: SolicitudViaje, usuario: dict = Depends(usuario_actual)):
    """Un look por día con el pronóstico del destino y la maleta. No guarda nada ni cuenta como voto."""
    if datos.ocasion not in OCASIONES:
        raise HTTPException(422, f"La ocasión debe ser una de: {', '.join(OCASIONES)}")
    preferencias = leer_preferencias(usuario["id"]) or {}
    return viaje.planear(prendas_de(usuario["id"]), datos.latitud, datos.longitud, datos.lugar, datos.salida,
                         datos.dias, datos.ocasion, gustos_de(usuario["id"], preferencias))


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
    prendas = prendas_del_atuendo(datos.prenda_ids, usuario)
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
    """Cambia las referencias (prenda_id) de los elementos por las prendas completas, en el orden guardado."""
    ids = [e["prenda_id"] for e in atuendo["elementos"]]
    prendas = {p["_id"]: preparar_prenda(p) for p in bd().prendas.find({"_id": {"$in": ids}})}
    resultado = como_dict(atuendo)
    resultado["elementos"] = [{"rol": e["rol"], "prenda": prendas[e["prenda_id"]]}
                              for e in atuendo["elementos"] if e["prenda_id"] in prendas]
    return resultado


@aplicacion.post("/api/atuendos", status_code=201)
def guardar_atuendo(datos: AtuendoNuevo, usuario: dict = Depends(usuario_actual)):
    if not datos.elementos:
        raise HTTPException(422, "El atuendo necesita al menos una prenda")
    prendas = prendas_del_atuendo([e.prenda_id for e in datos.elementos], usuario)

    # Los elementos van embebidos: un solo insert guarda el atuendo con sus prendas (referencias por _id).
    atuendo = {
        "_id": siguiente_id("atuendos"), "usuario_id": usuario["id"], "puntuacion": float(datos.puntuacion),
        "reporte_clima": datos.reporte_clima, "fecha_creacion": ahora(),
        "elementos": [{"prenda_id": e.prenda_id, "rol": e.rol} for e in datos.elementos],
    }
    bd().atuendos.insert_one(atuendo)
    guardar_voto(usuario["id"], prendas, 1)  # guardar un atuendo cuenta como darle corazón
    return leer_atuendo(atuendo)


@aplicacion.get("/api/atuendos")
def listar_atuendos(usuario: dict = Depends(usuario_actual)):
    return [leer_atuendo(a) for a in bd().atuendos.find({"usuario_id": usuario["id"]}).sort("_id", -1)]


@aplicacion.delete("/api/atuendos/{atuendo_id}", status_code=204)
def eliminar_atuendo(atuendo_id: int, usuario: dict = Depends(usuario_actual)):
    if bd().atuendos.delete_one({"_id": atuendo_id, "usuario_id": usuario["id"]}).deleted_count == 0:
        raise HTTPException(404, "Atuendo no encontrado")


# ============================================================
# RESCATE DE PRENDAS OLVIDADAS: el reto de la semana (ver rescate.py)
# ============================================================

def como_reto(reto: dict | None, usuario: dict, hoy: date) -> dict | None:
    """El reto con su prenda, sus 3 looks (como sugerencias, para guardarlos o marcarlos) y si ya se cumplió."""
    if reto is None:
        return None
    prendas = {p["id"]: p for p in prendas_de(usuario["id"])}
    prenda = prendas[reto["prenda_id"]]
    usos = uso_por_prenda(usuario["id"]).get(prenda["id"], SIN_USO)
    dias = (hoy - date.fromisoformat(usos["ultimo"] or str(prenda["fecha_creacion"])[:10])).days
    cumplido = bd().usos.count_documents({"usuario_id": usuario["id"], "prenda_ids": prenda["id"],
                                          "fecha": {"$in": rescate.dias_de_la_semana(reto["semana"])}}) > 0
    propuestas = [{"elementos": [{"rol": prendas[i]["categoria"], "prenda": prendas[i]} for i in look], "puntuacion": 0,
                   "ventajas": []} for look in reto["propuestas"]]
    return {"id": reto["_id"], "semana": reto["semana"], "prenda": prenda, "dias_sin_usar": dias,
            "nunca_usada": usos["ultimo"] is None, "propuestas": propuestas, "estado": reto["estado"],
            "cambios_restantes": rescate.CAMBIOS_POR_SEMANA - reto["cambios"], "cumplido": cumplido}


def datos_del_reto(usuario: dict):
    preferencias = leer_preferencias(usuario["id"]) or {}
    return prendas_de(usuario["id"]), uso_por_prenda(usuario["id"]), gustos_de(usuario["id"], preferencias)


@aplicacion.get("/api/reto")
def ver_reto(fecha: str | None = None, usuario: dict = Depends(usuario_actual)):
    """El reto de esta semana (se elige la primera vez que se pide), o null si no hay prendas olvidadas."""
    hoy = leer_fecha(fecha)
    armario, usos, gustos = datos_del_reto(usuario)
    return como_reto(rescate.reto_de_la_semana(usuario["id"], armario, usos, gustos, hoy), usuario, hoy)


@aplicacion.post("/api/reto/cambiar")
def cambiar_reto(fecha: str | None = None, usuario: dict = Depends(usuario_actual)):
    """Otra prenda olvidada para esta semana (hasta 2 veces)."""
    hoy = leer_fecha(fecha)
    reto = bd().retos.find_one({"usuario_id": usuario["id"], "semana": rescate.semana_de(hoy)})
    if reto is None:
        raise HTTPException(404, "Esta semana todavía no hay reto")
    if reto["cambios"] >= rescate.CAMBIOS_POR_SEMANA:
        raise HTTPException(422, "Ya cambiaste la prenda 2 veces esta semana")
    armario, usos, gustos = datos_del_reto(usuario)
    excluir = rescate.recientes(usuario["id"])
    elegido = rescate.elegir(usuario["id"], armario, usos, gustos, hoy, excluir)
    if elegido is None:
        raise HTTPException(404, "No hay otra prenda olvidada para rescatar")
    prenda, propuestas = elegido
    bd().retos.update_one({"_id": reto["_id"]}, {"$set": {"prenda_id": prenda["id"], "propuestas": rescate.ids_de(propuestas),
                                                          "estado": "activo"}, "$inc": {"cambios": 1},
                                                 "$addToSet": {"descartadas": reto["prenda_id"]}})  # no vuelve a salir
    return como_reto(bd().retos.find_one({"_id": reto["_id"]}), usuario, hoy)


@aplicacion.post("/api/reto/omitir")
def omitir_reto(fecha: str | None = None, usuario: dict = Depends(usuario_actual)):
    """"Ahora no": el reto de esta semana deja de mostrarse."""
    hoy = leer_fecha(fecha)
    hecho = bd().retos.update_one({"usuario_id": usuario["id"], "semana": rescate.semana_de(hoy)}, {"$set": {"estado": "omitido"}})
    if hecho.matched_count == 0:
        raise HTTPException(404, "Esta semana todavía no hay reto")
    return como_reto(bd().retos.find_one({"usuario_id": usuario["id"], "semana": rescate.semana_de(hoy)}), usuario, hoy)


# ============================================================
# CÁPSULAS DE GUARDARROPA (ver capsulas.py)
# ============================================================

class SolicitudCapsula(BaseModel):
    escenario: str = "mensual"
    ocasion: str = "diario"
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    lugar: str = Field(default="", max_length=120)
    salida: int = Field(default=0, ge=0, le=7)
    dias: int = Field(default=5, ge=1, le=7)


def hechos_de_capsula(datos: SolicitudCapsula) -> list[set[str]]:
    """Los hechos de cada día: el pronóstico del destino (viaje) o el clima de hoy (mes). Sin ubicación, templado."""
    ocasion = hechos_de_ocasion(datos.ocasion)
    if datos.latitud is None or datos.longitud is None:
        return [ocasion]
    if datos.escenario == "viaje":
        pronostico = viaje.pronostico_diario(datos.latitud, datos.longitud)
        return [viaje.clima_del_dia(pronostico, i)[1] | ocasion for i in range(datos.salida, datos.salida + datos.dias)]
    return [set(obtener_clima(datos.latitud, datos.longitud)["hechos"]) | ocasion]


@aplicacion.post("/api/capsulas/generar")
def generar_capsula(datos: SolicitudCapsula, usuario: dict = Depends(usuario_actual)):
    """La mejor cápsula con tu ropa para el escenario, el clima y la ocasión. No guarda nada."""
    if datos.escenario not in capsulas.ESCENARIOS:
        raise HTTPException(422, "El escenario debe ser mensual o viaje")
    if datos.ocasion not in OCASIONES:
        raise HTTPException(422, f"La ocasión debe ser una de: {', '.join(OCASIONES)}")
    if datos.escenario == "viaje" and datos.latitud is None:
        raise HTTPException(422, "Elige el destino del viaje")
    usos = {i: u["veces"] for i, u in uso_por_prenda(usuario["id"]).items()}
    resultado = capsulas.armar(prendas_de(usuario["id"]), datos.escenario, hechos_de_capsula(datos),
                               leer_colorimetria(usuario["id"]), usos)
    return {**resultado, "detalles": {"ocasion": datos.ocasion, "lugar": datos.lugar or None, "dias": datos.dias,
                                      "salida": datos.salida, "con_abrigo": resultado["con_abrigo"]}}


class CapsulaNueva(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    escenario: str
    prenda_ids: list[int] = Field(min_length=1, max_length=30)
    detalles: dict = {}


def leer_capsula(capsula: dict, usuario: dict) -> dict:
    """La cápsula con sus prendas de hoy y sus looks recalculados (si borraste o lavas una, se nota)."""
    prendas = [preparar_prenda(p) for p in bd().prendas.find({"_id": {"$in": capsula["prenda_ids"]}, "usuario_id": usuario["id"]})]
    combina = capsulas.Combinaciones(prendas)
    con_abrigo = bool(capsula["detalles"].get("con_abrigo"))
    looks = capsulas.looks_de(prendas, combina, con_abrigo)
    resultado = como_dict(capsula)
    resultado.update(prendas=sorted(prendas, key=lambda p: (CATEGORIAS.index(p["categoria"]), p["id"])), looks=len(looks),
                     combinaciones=[[p["id"] for p in look] for look in looks[:capsulas.MAXIMO_LOOKS_EN_RESPUESTA]])
    return resultado


def buscar_capsula(capsula_id: int, usuario: dict) -> dict:
    capsula = bd().capsulas.find_one({"_id": capsula_id, "usuario_id": usuario["id"]})
    if capsula is None:
        raise HTTPException(404, "Cápsula no encontrada")
    return capsula


@aplicacion.post("/api/capsulas", status_code=201)
def guardar_capsula(datos: CapsulaNueva, usuario: dict = Depends(usuario_actual)):
    if datos.escenario not in capsulas.ESCENARIOS:
        raise HTTPException(422, "El escenario debe ser mensual o viaje")
    prendas_del_atuendo(datos.prenda_ids, usuario)  # sin repetidas y todas de la persona
    capsula = {"_id": siguiente_id("capsulas"), "usuario_id": usuario["id"], "nombre": datos.nombre.strip(),
               "escenario": datos.escenario, "prenda_ids": datos.prenda_ids, "empacadas": [],
               "detalles": {k: datos.detalles.get(k) for k in ("ocasion", "lugar", "dias", "salida", "con_abrigo")},
               "fecha_creacion": ahora()}
    bd().capsulas.insert_one(capsula)
    return leer_capsula(capsula, usuario)


@aplicacion.get("/api/capsulas")
def listar_capsulas(usuario: dict = Depends(usuario_actual)):
    return [leer_capsula(c, usuario) for c in bd().capsulas.find({"usuario_id": usuario["id"]}).sort("_id", -1)]


@aplicacion.get("/api/capsulas/{capsula_id}")
def ver_capsula(capsula_id: int, usuario: dict = Depends(usuario_actual)):
    return leer_capsula(buscar_capsula(capsula_id, usuario), usuario)


class CambioCapsula(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    empacadas: list[int] | None = None


@aplicacion.patch("/api/capsulas/{capsula_id}")
def cambiar_capsula(capsula_id: int, datos: CambioCapsula, usuario: dict = Depends(usuario_actual)):
    """Renombrarla o marcar qué ya va en la maleta (checklist)."""
    capsula = buscar_capsula(capsula_id, usuario)
    cambios = {}
    if datos.nombre is not None:
        cambios["nombre"] = datos.nombre.strip()
    if datos.empacadas is not None:
        if not set(datos.empacadas) <= set(capsula["prenda_ids"]):
            raise HTTPException(422, "Solo se pueden marcar prendas de la cápsula")
        cambios["empacadas"] = sorted(set(datos.empacadas))
    if cambios:
        bd().capsulas.update_one({"_id": capsula_id}, {"$set": cambios})
    return leer_capsula(buscar_capsula(capsula_id, usuario), usuario)


@aplicacion.delete("/api/capsulas/{capsula_id}", status_code=204)
def eliminar_capsula(capsula_id: int, usuario: dict = Depends(usuario_actual)):
    buscar_capsula(capsula_id, usuario)
    bd().capsulas.delete_one({"_id": capsula_id})


# ============================================================
# USO DE LA ROPA: "Me lo puse hoy" (un look por día)
# ============================================================

class UsoNuevo(BaseModel):
    prenda_ids: list[int] = Field(min_length=1, max_length=6)
    fecha: str | None = None  # el día en el teléfono; sin ella, hoy en UTC


def leer_uso(uso: dict) -> dict:
    """El día con sus prendas completas (como los atuendos guardados), en orden del cuerpo."""
    prendas = {p["_id"]: preparar_prenda(p) for p in bd().prendas.find({"_id": {"$in": uso["prenda_ids"]}})}
    resultado = como_dict(uso)
    resultado["elementos"] = sorted(
        ({"rol": prendas[i]["categoria"], "prenda": prendas[i]} for i in uso["prenda_ids"] if i in prendas),
        key=lambda e: viaje.ORDEN_MALETA.index(e["rol"]))
    return resultado


@aplicacion.post("/api/usos", status_code=201)
def registrar_uso(datos: UsoNuevo, usuario: dict = Depends(usuario_actual)):
    """Lo que te pusiste ese día. Si ya había algo ese día, lo reemplaza. Un look completo cuenta como corazón."""
    dia = leer_fecha(datos.fecha)
    if dia > ahora().date() + timedelta(days=1):  # un día de margen: en México ya es mañana en UTC desde las 18 h
        raise HTTPException(422, "No puedes registrar un día que todavía no llega")
    prendas = prendas_del_atuendo(datos.prenda_ids, usuario)
    filtro = {"usuario_id": usuario["id"], "fecha": dia.isoformat()}
    cambios = {"prenda_ids": datos.prenda_ids, "fecha_creacion": ahora()}
    if bd().usos.update_one(filtro, {"$set": cambios}).matched_count == 0:
        try:
            bd().usos.insert_one({"_id": siguiente_id("usos"), **filtro, **cambios})
        except DuplicateKeyError:  # otra petición registró ese día al mismo tiempo: se reemplaza
            bd().usos.update_one(filtro, {"$set": cambios})
    if len(prendas) >= 2:
        guardar_voto(usuario["id"], prendas, 1)  # ponértelo dice más que un corazón
    return leer_uso(bd().usos.find_one(filtro))


@aplicacion.get("/api/usos")
def listar_usos(desde: str | None = None, usuario: dict = Depends(usuario_actual)):
    """Los días registrados, del más reciente al más viejo; con desde (AAAA-MM-DD), solo de ese día en adelante."""
    filtro = {"usuario_id": usuario["id"]}
    if desde is not None:
        filtro["fecha"] = {"$gte": leer_fecha(desde).isoformat()}
    return [leer_uso(u) for u in bd().usos.find(filtro).sort("fecha", -1)]


@aplicacion.delete("/api/usos/{fecha}", status_code=204)
def quitar_uso(fecha: str, usuario: dict = Depends(usuario_actual)):
    """Deshacer "Me lo puse": el voto se queda (sigue siendo un look que te gustó)."""
    if bd().usos.delete_one({"usuario_id": usuario["id"], "fecha": leer_fecha(fecha).isoformat()}).deleted_count == 0:
        raise HTTPException(404, "Ese día no tiene nada registrado")


# ============================================================
# TIENDAS: prendas que te gustaron en una tienda (ver tiendas.py)
# ============================================================

AVISO_SIN_IA = "La IA no está disponible ahora: escribe qué prenda es para buscarla."
# Lo que vio la IA: la búsqueda usa el tipo, el color, el estampado, el estilo, la marca y los detalles;
# "¿Vale la pena?" (compra.py) también el abrigo.
DETECTADO = ("categoria", "subcategoria", "color_principal", "estampado", "estilo", "nivel_abrigo", "impermeable",
             "marca", "detalles")


def como_deseo(documento: dict) -> dict:
    """El deseo como lo usa la app: primero los links de la misma prenda (su texto de búsqueda) y después los de
    parecidas (solo tipo, color y estampado), si ese texto es distinto."""
    deseo = como_dict(documento)
    imagen_web = deseo.get("imagen_web")
    if imagen_web:  # la fecha va anidada: como_dict solo convierte las de primer nivel
        deseo["imagen_web"] = {**imagen_web, "fecha": como_dict({"f": imagen_web["fecha"]})["f"]}
    parecida = tiendas.texto_de_busqueda(deseo.get("detectado")) or None
    if parecida and parecida.lower() == deseo["busqueda"].lower():
        parecida = None
    return {**deseo, "imagen_web": deseo.get("imagen_web"), "por_imagen": busqueda_imagen.activa(),
            "links": tiendas.links(deseo["busqueda"], deseo["para"]), "parecida": parecida,
            "links_parecidas": tiendas.links(parecida, deseo["para"]) if parecida else []}


def ver_prenda_de_la_tienda(contenido: bytes) -> tuple[dict | None, str | None]:
    """(lo que vio la IA, aviso). Si la IA no responde, (None, aviso): la persona escribe qué buscar."""
    try:
        visto = detectar_para_tienda(contenido)
    except HTTPException:  # Ollama apagado u ocupado
        return None, AVISO_SIN_IA
    return {campo: visto.get(campo) for campo in DETECTADO}, None


def buscar_en_internet(contenido: bytes) -> tuple[dict | None, str | None]:
    """(lo que encontró Google con la foto, aviso). Sin clave de Cloud Vision: (None, None)."""
    try:
        return busqueda_imagen.buscar_por_imagen(contenido), None
    except busqueda_imagen.ErrorDeBusqueda as error:
        return None, str(error)


def buscar_deseo(deseo_id: int, usuario: dict) -> dict:
    deseo = bd().deseos.find_one({"_id": deseo_id, "usuario_id": usuario["id"]})
    if deseo is None:
        raise HTTPException(404, "No encontramos esa prenda en tu lista")
    return deseo


@aplicacion.post("/api/deseos", status_code=201)
def buscar_en_tiendas(imagen: UploadFile = File(...), para: str = Form("sin_especificar"),
                      usuario: dict = Depends(usuario_actual)):
    """La IA local ve la foto, propone qué buscar y la prenda queda en la lista con sus links de tiendas.

    Si la IA no responde, igual se guarda: la persona escribe qué buscar. Es def para no frenar el servidor.
    """
    if para not in tiendas.PARA:
        raise HTTPException(422, "Elige para quién es: mujer, hombre o sin especificar")
    contenido, extension = leer_imagen(imagen)
    # La IA local (qué es) y Google (dónde está la misma prenda) trabajan al mismo tiempo.
    with ThreadPoolExecutor(max_workers=2) as hilos:
        local, web = hilos.submit(ver_prenda_de_la_tienda, contenido), hilos.submit(buscar_en_internet, contenido)
        (detectado, aviso), (imagen_web, aviso_imagen) = local.result(), web.result()
    documento = {
        "_id": siguiente_id("deseos"),
        "usuario_id": usuario["id"],
        "url_imagen": guardar_imagen(contenido, extension, "deseos"),
        "busqueda": (tiendas.texto_de_busqueda(detectado, exacta=True) or "Ropa")[:120],
        "para": para,
        "detectado": detectado,
        "imagen_web": imagen_web,
        "fecha_creacion": ahora(),
    }
    bd().deseos.insert_one(documento)
    return {**como_deseo(documento), "aviso": aviso, "aviso_imagen": aviso_imagen}


@aplicacion.get("/api/deseos")
def listar_deseos(usuario: dict = Depends(usuario_actual)):
    return [como_deseo(d) for d in bd().deseos.find({"usuario_id": usuario["id"]}).sort("_id", -1)]


class CambioDeseo(BaseModel):
    busqueda: str | None = Field(default=None, min_length=1, max_length=120)
    para: str | None = None


@aplicacion.patch("/api/deseos/{deseo_id}")
def cambiar_deseo(deseo_id: int, datos: CambioDeseo, usuario: dict = Depends(usuario_actual)):
    """Corregir qué se busca (si la IA se equivocó) o para quién es."""
    buscar_deseo(deseo_id, usuario)
    cambios = {}
    if datos.busqueda is not None:
        if not datos.busqueda.strip():
            raise HTTPException(422, "Escribe qué prenda buscar")
        cambios["busqueda"] = datos.busqueda.strip()
    if datos.para is not None:
        if datos.para not in tiendas.PARA:
            raise HTTPException(422, "Elige para quién es: mujer, hombre o sin especificar")
        cambios["para"] = datos.para
    if cambios:
        bd().deseos.update_one({"_id": deseo_id}, {"$set": cambios})
    return como_deseo(buscar_deseo(deseo_id, usuario))


@aplicacion.post("/api/deseos/{deseo_id}/analizar")
def analizar_deseo(deseo_id: int, usuario: dict = Depends(usuario_actual)):
    """La IA vuelve a mirar la foto guardada (p. ej. si estaba apagada, o para un deseo de antes de leer la marca)
    y rehace la búsqueda exacta. Es def para no frenar el servidor mientras Ollama responde."""
    deseo = buscar_deseo(deseo_id, usuario)
    foto = CARPETA_ARCHIVOS / deseo["url_imagen"].removeprefix("/archivos/")
    if not foto.exists():
        raise HTTPException(404, "La foto ya no existe")
    detectado, aviso = ver_prenda_de_la_tienda(foto.read_bytes())
    if detectado is None:
        raise HTTPException(503, aviso)
    busqueda = (tiendas.texto_de_busqueda(detectado, exacta=True) or deseo["busqueda"])[:120]
    bd().deseos.update_one({"_id": deseo_id}, {"$set": {"detectado": detectado, "busqueda": busqueda}})
    return como_deseo(buscar_deseo(deseo_id, usuario))


@aplicacion.post("/api/deseos/{deseo_id}/buscar-por-imagen")
def buscar_deseo_por_imagen(deseo_id: int, usuario: dict = Depends(usuario_actual)):
    """Busca (otra vez) en internet la prenda exacta de la foto guardada con Google Cloud Vision."""
    deseo = buscar_deseo(deseo_id, usuario)
    if not busqueda_imagen.activa():
        raise HTTPException(503, "La búsqueda por imagen no está activada: falta GOOGLE_VISION_CLAVE en backend/.env")
    foto = CARPETA_ARCHIVOS / deseo["url_imagen"].removeprefix("/archivos/")
    if not foto.exists():
        raise HTTPException(404, "La foto ya no existe")
    imagen_web, aviso = buscar_en_internet(foto.read_bytes())
    if imagen_web is None:
        raise HTTPException(502, aviso)
    bd().deseos.update_one({"_id": deseo_id}, {"$set": {"imagen_web": imagen_web}})
    return como_deseo(buscar_deseo(deseo_id, usuario))


@aplicacion.get("/api/deseos/{deseo_id}/vale-la-pena")
def vale_la_pena(deseo_id: int, usuario: dict = Depends(usuario_actual)):
    """Cuántos looks arma con tu ropa, comparado con lo que ya tienes, y si ya tienes algo parecido (compra.py)."""
    deseo = buscar_deseo(deseo_id, usuario)
    preferencias = leer_preferencias(usuario["id"]) or {}
    analisis = compra.analizar(deseo, prendas_de(usuario["id"]), gustos_de(usuario["id"], preferencias))
    if analisis is None:
        raise HTTPException(422, "La IA no reconoció qué prenda es: vuelve a tomarle foto para calcularlo")
    return analisis


@aplicacion.delete("/api/deseos/{deseo_id}", status_code=204)
def eliminar_deseo(deseo_id: int, usuario: dict = Depends(usuario_actual)):
    """Quitarla de la lista (p. ej. porque ya la compraste); también se borra su foto."""
    deseo = buscar_deseo(deseo_id, usuario)
    bd().deseos.delete_one({"_id": deseo_id})
    borrar_imagen(deseo["url_imagen"])


# ============================================================
# PROBADOR VIRTUAL (la IA corre en el motor: ver probador.py y backend/motor)
# ============================================================

@aplicacion.post("/api/perfil/foto")
def subir_foto_cuerpo(imagen: UploadFile = File(...), usuario: dict = Depends(usuario_actual)):
    """La foto con la que se prueban los looks. El motor revisa que sirva; queda en backend/privado.

    Es def (no async) para que FastAPI la corra en otro hilo mientras el motor la revisa.
    """
    contenido, extension = leer_imagen(imagen)
    if extension == ".heic":
        raise HTTPException(415, "Manda la foto en JPG o PNG.")
    probador.guardar_foto(usuario["id"], contenido, extension)
    return leer_perfil(usuario["id"])


@aplicacion.get("/api/perfil/foto")
def ver_foto_cuerpo(usuario: dict = Depends(usuario_actual)):
    """La foto de la persona, solo para ella (pide la sesión). La app agrega ?v=version_foto para no ver una vieja."""
    foto = probador.foto_de(usuario["id"]).get("foto_cuerpo")
    if not foto or not Path(foto).is_file():
        raise HTTPException(404, "Todavía no subes tu foto")
    return FileResponse(foto, headers={"Cache-Control": "private, max-age=86400"})


@aplicacion.delete("/api/perfil/foto")
def borrar_foto_cuerpo(usuario: dict = Depends(usuario_actual)):
    """Borra la foto y todas las imágenes generadas con ella."""
    probador.borrar_foto(usuario["id"])
    return leer_perfil(usuario["id"])


class SolicitudPrueba(BaseModel):
    prenda_ids: list[int] = Field(min_length=1, max_length=6)


@aplicacion.post("/api/atuendos/probador")
def pedir_prueba(datos: SolicitudPrueba, usuario: dict = Depends(usuario_actual)):
    """Pide ver un look puesto. Si ya se generó, responde "lista"; si no, queda en la cola."""
    return probador.pedir(usuario["id"], prendas_del_atuendo(datos.prenda_ids, usuario))


@aplicacion.get("/api/atuendos/probador/{prueba_id}")
def consultar_prueba(prueba_id: int, usuario: dict = Depends(usuario_actual)):
    return probador.consultar_estado(usuario["id"], prueba_id)


@aplicacion.get("/api/atuendos/probador/{prueba_id}/imagen")
def imagen_de_prueba(prueba_id: int, usuario: dict = Depends(usuario_actual)):
    return FileResponse(probador.ruta_de_imagen(usuario["id"], prueba_id), media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=86400"})


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


DIAS_DE_USO = 30
MINIMO_DIAS_REGISTRADOS = 5  # con menos días, "sin usar" sería casi todo el armario
MAS_USADAS = 5


def resumen_de_uso(usuario_id: int, prendas: list[dict], hoy: date) -> dict:
    """Qué tanto del armario usas: días registrados, % de prendas usadas, las más usadas y las que no.

    Cuenta las prendas que no están archivadas; las de los últimos 30 días según la fecha del teléfono.
    """
    desde = (hoy - timedelta(days=DIAS_DE_USO - 1)).isoformat()
    usos = list(bd().usos.find({"usuario_id": usuario_id, "fecha": {"$gte": desde}}))
    veces = Counter(i for uso in usos for i in uso["prenda_ids"])
    activas = [p for p in prendas if p["estado"] != "archivada"]
    usadas = [p for p in activas if veces[p["id"]]]
    return {
        "dias": DIAS_DE_USO,
        "dias_registrados": len(usos),
        "listo": len(usos) >= MINIMO_DIAS_REGISTRADOS,
        "minimo": MINIMO_DIAS_REGISTRADOS,
        "porcentaje_usado": round(100 * len(usadas) / len(activas)) if activas else 0,
        "mas_usadas": [{"prenda": p, "veces": veces[p["id"]]}
                       for p in sorted(usadas, key=lambda p: (-veces[p["id"]], p["id"]))[:MAS_USADAS]],
        "sin_usar": [p for p in activas if not veces[p["id"]]],
    }


DIAS_ACTIVA = 30  # semáforo de rotación
DIAS_POCO_USADA = 90
DIAS_NUEVA = 60  # sin uso pero dada de alta hace menos: todavía no se juzga
MEJORES = 5


def analitica_de_uso(usuario_id: int, prendas: list[dict], hoy: date) -> dict:
    """Costo por puesta, aprovechamiento a 30 y 90 días y el semáforo de rotación (prendas no archivadas)."""
    usos = uso_por_prenda(usuario_id)
    activas = [p for p in prendas if p["estado"] != "archivada"]

    def dias_desde(texto: str | None) -> int | None:
        return (hoy - date.fromisoformat(texto[:10])).days if texto else None

    filas = []
    for prenda in activas:
        uso = usos.get(prenda["id"], SIN_USO)
        filas.append({"prenda": prenda, "veces": uso["veces"], "ultimo": uso["ultimo"],
                      "dias_sin_usar": dias_desde(uso["ultimo"]), "dias_de_alta": dias_desde(prenda["fecha_creacion"])})

    def porcentaje(dias: int) -> int:
        usadas = sum(1 for f in filas if f["dias_sin_usar"] is not None and f["dias_sin_usar"] < dias)
        return round(100 * usadas / len(filas)) if filas else 0

    rotacion = {"activas": [], "poco_usadas": [], "nuevas": [], "candidatas": []}
    for fila in filas:
        if fila["dias_sin_usar"] is not None and fila["dias_sin_usar"] < DIAS_ACTIVA:
            rotacion["activas"].append(fila)
        elif fila["dias_sin_usar"] is not None and fila["dias_sin_usar"] < DIAS_POCO_USADA:
            rotacion["poco_usadas"].append(fila)
        elif fila["dias_sin_usar"] is None and (fila["dias_de_alta"] or 0) < DIAS_NUEVA:
            rotacion["nuevas"].append(fila)
        else:
            rotacion["candidatas"].append(fila)
    for grupo in rotacion.values():  # de la más olvidada a la menos (si nunca se usó, cuenta desde que se dio de alta)
        grupo.sort(key=lambda f: -(f["dias_sin_usar"] if f["dias_sin_usar"] is not None else f["dias_de_alta"] or 0))

    con_precio = [{**f, "costo_por_uso": round(f["prenda"]["precio_compra"] / max(f["veces"], 1), 2)}
                  for f in filas if f["prenda"].get("precio_compra")]
    usadas = [f for f in con_precio if f["veces"] > 0]
    return {
        "aprovechamiento": {"30": porcentaje(30), "90": porcentaje(90)},
        "rotacion": rotacion,
        "costo_por_uso": {
            "prendas_con_precio": len(con_precio),
            "invertido": round(sum(f["prenda"]["precio_compra"] for f in con_precio), 2),
            "mas_rentables": sorted(usadas, key=lambda f: f["costo_por_uso"])[:MEJORES],
            "menos_amortizadas": sorted(con_precio, key=lambda f: -f["costo_por_uso"])[:MEJORES],
        },
    }


@aplicacion.get("/api/estadisticas")
def ver_estadisticas(fecha: str | None = None, usuario: dict = Depends(usuario_actual)):
    prendas = prendas_de(usuario["id"])
    por_categoria = {c: 0 for c in CATEGORIAS} | Counter(p["categoria"] for p in prendas)
    por_color = dict(Counter(p["color_principal"] for p in prendas).most_common())
    por_nivel = {str(n): 0 for n in range(1, 6)} | Counter(str(p["nivel_abrigo"]) for p in prendas)
    neutras = sum(p["color_principal"] in COLORES_NEUTROS for p in prendas)
    guardados = bd().atuendos.count_documents({"usuario_id": usuario["id"]})

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
            "atuendos_guardados": guardados,
        },
        "por_categoria": por_categoria,
        "por_color": por_color,
        "por_nivel_abrigo": por_nivel,
        "hallazgo": redactar_hallazgo(prendas, por_categoria, neutras),
        "mapa": mapa,
        "mapa_impermeables": mapa_impermeables,
        "historial": historial_de_prendas(prendas),
        "uso": resumen_de_uso(usuario["id"], prendas, leer_fecha(fecha)),
        "analitica": analitica_de_uso(usuario["id"], prendas, leer_fecha(fecha)),
    }


@aplicacion.get("/api/salud")
def verificar_salud():
    bd().command("ping")  # también comprueba que MongoDB responda
    return {"estado": "ok"}
