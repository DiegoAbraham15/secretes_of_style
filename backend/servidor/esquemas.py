"""Validación ($jsonSchema) e índices de cada colección de MongoDB.

MongoDB rechaza cualquier documento que no cumpla su esquema, aunque no venga de la API (p. ej. desde mongosh).
Los catálogos (colores, estilos, respuestas del cuestionario...) se toman del código, así nunca se separan.
"""

from servidor.aprendizaje import ACCESORIOS, PESOS_DE_RESPUESTA
from servidor.logica import COLORES, ESTAMPADOS, ESTILOS

CATEGORIAS = ["parte_superior", "parte_inferior", "calzado", "abrigo", "accesorio"]
ESTADOS_PRENDA = ["disponible", "en_lavado", "archivada"]
ESTADOS_PRUEBA = ["en_cola", "procesando", "lista", "error"]
TEMPORADAS = ["primavera_verano", "todo_el_ano", "otono_invierno"]
NUMERO = ["double", "int", "long"]  # en BSON un número real puede llegar como double o como entero


def texto_o_nulo(descripcion: str) -> dict:
    return {"bsonType": ["string", "null"], "description": descripcion}


def numero_o_nulo(descripcion: str) -> dict:
    return {"bsonType": NUMERO + ["null"], "description": descripcion}


ESQUEMAS = {
    "usuarios": {
        "bsonType": "object",
        "required": ["_id", "correo", "contraseña_hash", "version_sesion", "fecha_creacion", "perfil"],
        "properties": {
            "_id": {"bsonType": "int", "minimum": 1, "description": "número consecutivo (contadores.usuarios)"},
            "correo": {"bsonType": "string", "pattern": "@", "description": "en minúsculas, único"},
            "contraseña_hash": {"bsonType": "string", "pattern": "^[0-9a-f]{32}\\$[0-9a-f]{64}$",
                                "description": "sal$hash, PBKDF2-SHA256 con 100 000 iteraciones"},
            "version_sesion": {"bsonType": "int", "minimum": 0, "description": "sube al cerrar sesión"},
            "fecha_creacion": {"bsonType": "date"},
            "perfil": {
                "bsonType": "object",
                "required": ["version_foto"],
                "properties": {
                    "foto_cuerpo": texto_o_nulo("ruta privada de la foto del probador"),
                    "version_foto": {"bsonType": "int", "minimum": 0, "description": "sube cada vez que cambia la foto"},
                },
            },
            "preferencias": {
                "bsonType": "object",
                "required": ["paleta", "ropa", "estampados", "accesorios", "fecha_actualizacion"],
                "properties": {
                    "paleta": {"enum": list(PESOS_DE_RESPUESTA["paleta"])},
                    "ropa": {"enum": list(PESOS_DE_RESPUESTA["ropa"])},
                    "estampados": {"enum": list(PESOS_DE_RESPUESTA["estampados"])},
                    "accesorios": {"enum": ACCESORIOS},
                    "fecha_actualizacion": {"bsonType": "date"},
                },
            },
            "colorimetria": {
                "bsonType": "object",
                "required": ["estacion", "subtono", "paleta", "evitar", "priorizar", "fecha_actualizacion"],
                "properties": {
                    "estacion": {"enum": ["primavera", "verano", "otono", "invierno"]},
                    "subtono": {"enum": ["calido", "frio", "neutro"]},
                    "paleta": {"bsonType": "array", "items": {"enum": sorted(COLORES)}},
                    "evitar": {"bsonType": "array", "items": {"enum": sorted(COLORES)}},
                    "priorizar": {"bsonType": "bool"},
                    "respuestas": {"bsonType": ["object", "null"], "description": "el cuestionario de 5 preguntas"},
                    "selfie": {"bsonType": ["object", "null"], "description": "color de piel y cabello (sin la foto)"},
                    "fecha_actualizacion": {"bsonType": "date"},
                },
            },
            "pesos": {
                "bsonType": "object",
                "required": ["valores", "fecha_actualizacion"],
                "properties": {
                    "valores": {"bsonType": "object", "description": "peso del perceptrón por característica"},
                    "fecha_actualizacion": {"bsonType": "date"},
                },
            },
        },
    },
    "prendas": {
        "bsonType": "object",
        "required": ["_id", "usuario_id", "url_imagen", "categoria", "color_principal", "nivel_abrigo", "impermeable",
                     "estampado", "estilo", "estado", "fecha_creacion"],
        "properties": {
            "_id": {"bsonType": "int", "minimum": 1},
            "usuario_id": {"bsonType": "int", "description": "referencia a usuarios._id"},
            "url_imagen": {"bsonType": "string", "description": "ruta pública /archivos/prendas/<uuid>.<ext>"},
            "categoria": {"enum": CATEGORIAS},
            "subcategoria": {"bsonType": ["string", "null"], "maxLength": 60},
            "color_principal": {"enum": sorted(COLORES)},
            "nivel_abrigo": {"bsonType": "int", "minimum": 1, "maximum": 5},
            "impermeable": {"bsonType": "bool"},
            "estampado": {"enum": ESTAMPADOS},
            "estilo": {"enum": ESTILOS},
            "estado": {"enum": ESTADOS_PRENDA},
            "fecha_creacion": {"bsonType": "date"},
            # Digitalización y analítica (opcionales: las prendas de antes no los tienen)
            "url_original": texto_o_nulo("la foto con fondo, si url_imagen es el PNG sin fondo"),
            "sin_fondo": {"bsonType": "bool"},
            "color_hex": {"bsonType": ["string", "null"], "pattern": "^#[0-9A-F]{6}$", "description": "color medido"},
            "temporada": {"enum": TEMPORADAS + [None]},
            "huella": texto_o_nulo("md5 de la foto original, para avisar de duplicados"),
            "precio_compra": {"bsonType": NUMERO + ["null"], "minimum": 0},
            "fecha_adquisicion": {"bsonType": ["string", "null"], "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
            "origen": {"bsonType": ["object", "null"], "description": "foto o url (con url_tienda y título)"},
        },
    },
    "capsulas": {
        "bsonType": "object",
        "required": ["_id", "usuario_id", "nombre", "escenario", "prenda_ids", "empacadas", "detalles", "fecha_creacion"],
        "properties": {
            "_id": {"bsonType": "int", "minimum": 1},
            "usuario_id": {"bsonType": "int"},
            "nombre": {"bsonType": "string", "minLength": 1, "maxLength": 60},
            "escenario": {"enum": ["mensual", "viaje"]},
            "prenda_ids": {"bsonType": "array", "items": {"bsonType": "int"}},
            "empacadas": {"bsonType": "array", "items": {"bsonType": "int"}, "description": "checklist de equipaje"},
            "detalles": {"bsonType": "object", "description": "ocasión, lugar, días y si el clima pide abrigo"},
            "fecha_creacion": {"bsonType": "date"},
        },
    },
    "retos": {
        "bsonType": "object",
        "required": ["_id", "usuario_id", "semana", "prenda_id", "propuestas", "estado", "cambios", "fecha_creacion"],
        "properties": {
            "_id": {"bsonType": "int", "minimum": 1},
            "usuario_id": {"bsonType": "int"},
            "semana": {"bsonType": "string", "pattern": "^\\d{4}-W\\d{2}$", "description": "semana ISO, p. ej. 2026-W47"},
            "prenda_id": {"bsonType": "int", "description": "la prenda olvidada que se rescata"},
            "propuestas": {"bsonType": "array", "items": {"bsonType": "array", "items": {"bsonType": "int"}}},
            "estado": {"enum": ["activo", "omitido"]},
            "cambios": {"bsonType": "int", "minimum": 0, "description": "veces que se pidió otra prenda"},
            "fecha_creacion": {"bsonType": "date"},
        },
    },
    "borradores": {
        "bsonType": "object",
        "required": ["_id", "usuario_id", "url_original", "url_imagen", "estado", "propuesta", "fecha_creacion"],
        "properties": {
            "_id": {"bsonType": "int", "minimum": 1},
            "usuario_id": {"bsonType": "int"},
            "url_original": {"bsonType": "string"},
            "url_imagen": {"bsonType": "string", "description": "el PNG sin fondo cuando ya está; si no, el original"},
            "sin_fondo": {"bsonType": "bool"},
            "huella": texto_o_nulo("md5 de la foto original"),
            "estado": {"enum": ["en_fila", "analizando", "lista", "error"]},
            "propuesta": {"bsonType": "object", "description": "lo que propone la IA más el color medido y la temporada"},
            "avisos": {"bsonType": "array", "items": {"bsonType": "string"}},
            "duplicada_de": {"bsonType": ["int", "null"], "description": "prenda con la misma foto"},
            "origen": {"bsonType": ["object", "null"]},
            "fecha_creacion": {"bsonType": "date"},
        },
    },
    "atuendos": {
        "bsonType": "object",
        "required": ["_id", "usuario_id", "puntuacion", "elementos", "fecha_creacion"],
        "properties": {
            "_id": {"bsonType": "int", "minimum": 1},
            "usuario_id": {"bsonType": "int"},
            "puntuacion": {"bsonType": NUMERO},
            "reporte_clima": {"bsonType": ["object", "null"], "description": "el clima con que se generó"},
            "elementos": {
                "bsonType": "array",
                "description": "prendas del atuendo en orden (la base primero)",
                "items": {
                    "bsonType": "object",
                    "required": ["prenda_id", "rol"],
                    "properties": {"prenda_id": {"bsonType": "int"}, "rol": {"bsonType": "string"}},
                },
            },
            "fecha_creacion": {"bsonType": "date"},
        },
    },
    "votos_atuendo": {
        "bsonType": "object",
        "required": ["_id", "usuario_id", "firma", "me_gusta", "caracteristicas", "fecha_creacion"],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "usuario_id": {"bsonType": "int"},
            "firma": {"bsonType": "string", "minLength": 1, "description": "ids de las prendas ordenados: '3-16-28'"},
            "me_gusta": {"bsonType": "int", "enum": [1, -1]},
            "caracteristicas": {"bsonType": "object", "description": "las 13 características del perceptrón"},
            "fecha_creacion": {"bsonType": "date"},
        },
    },
    "pruebas_atuendo": {
        "bsonType": "object",
        "required": ["_id", "usuario_id", "firma", "version_foto", "estado", "paso", "pasos", "fecha_creacion", "fecha_uso"],
        "properties": {
            "_id": {"bsonType": "int", "minimum": 1},
            "usuario_id": {"bsonType": "int"},
            "firma": {"bsonType": "string", "description": "ids de las prendas vestidas: '2-7'"},
            "version_foto": {"bsonType": "int", "minimum": 0},
            "estado": {"enum": ESTADOS_PRUEBA},
            "paso": {"bsonType": "int", "minimum": 0},
            "pasos": {"bsonType": "int", "minimum": 1},
            "ruta": texto_o_nulo("imagen generada en backend/privado/pruebas"),
            "segundos": numero_o_nulo("lo que tardó la generación"),
            "error": texto_o_nulo("mensaje si falló"),
            "fecha_creacion": {"bsonType": "date"},
            "fecha_uso": {"bsonType": "date", "description": "última vez que se pidió o se vio"},
        },
    },
    "climas": {
        "bsonType": "object",
        "required": ["_id", "consultado", "reporte"],
        "properties": {
            "_id": {"bsonType": "string", "description": "latitud,longitud redondeadas a 2 decimales"},
            "consultado": {"bsonType": NUMERO, "description": "segundos desde 1970 (time.time())"},
            "reporte": {"bsonType": "object"},
        },
    },
    "deseos": {
        "bsonType": "object",
        "required": ["_id", "usuario_id", "url_imagen", "busqueda", "para", "fecha_creacion"],
        "properties": {
            "_id": {"bsonType": "int", "minimum": 1},
            "usuario_id": {"bsonType": "int"},
            "url_imagen": {"bsonType": "string", "description": "foto que tomó en la tienda: /archivos/deseos/<uuid>.<ext>"},
            "busqueda": {"bsonType": "string", "minLength": 1, "maxLength": 120,
                         "description": "lo que se busca en las tiendas; lo propone la IA y la persona lo corrige"},
            "para": {"enum": ["mujer", "hombre", "sin_especificar"]},
            "detectado": {"bsonType": ["object", "null"], "description": "lo que vio la IA: categoría, color, estampado…"},
            "imagen_web": {"bsonType": ["object", "null"],
                           "description": "lo que encontró Google Cloud Vision con la foto: exactas, parecidas y fecha"},
            "fecha_creacion": {"bsonType": "date"},
        },
    },
    "usos": {
        "bsonType": "object",
        "required": ["_id", "usuario_id", "fecha", "prenda_ids", "fecha_creacion"],
        "properties": {
            "_id": {"bsonType": "int", "minimum": 1},
            "usuario_id": {"bsonType": "int"},
            "fecha": {"bsonType": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                      "description": "el día en que se usó, según el teléfono (AAAA-MM-DD): uno por día"},
            "prenda_ids": {"bsonType": "array", "items": {"bsonType": "int"},
                           "description": "las prendas que se puso (referencias a prendas._id)"},
            "fecha_creacion": {"bsonType": "date"},
        },
    },
    "contadores": {
        "bsonType": "object",
        "required": ["_id", "valor"],
        "properties": {
            "_id": {"bsonType": "string", "description": "nombre de la colección"},
            "valor": {"bsonType": ["int", "long"], "description": "último número entregado"},
        },
    },
}

# (campos, opciones) de cada índice además del de _id, que MongoDB crea solo.
INDICES = {
    "usuarios": [([("correo", 1)], {"unique": True, "name": "correo_unico"})],
    "prendas": [([("usuario_id", 1), ("_id", -1)], {"name": "prendas_por_usuario"})],
    "atuendos": [
        ([("usuario_id", 1), ("_id", -1)], {"name": "atuendos_por_usuario"}),
        ([("elementos.prenda_id", 1)], {"name": "atuendos_por_prenda"}),
    ],
    "votos_atuendo": [([("usuario_id", 1), ("firma", 1)], {"unique": True, "name": "un_voto_por_atuendo"})],
    "pruebas_atuendo": [
        ([("usuario_id", 1), ("firma", 1), ("version_foto", 1)], {"unique": True, "name": "una_prueba_por_look"}),
        ([("estado", 1), ("_id", 1)], {"name": "cola_del_probador"}),
    ],
    "deseos": [([("usuario_id", 1), ("_id", -1)], {"name": "deseos_por_usuario"})],
    "borradores": [([("usuario_id", 1), ("_id", 1)], {"name": "borradores_por_usuario"})],
    "capsulas": [([("usuario_id", 1), ("_id", -1)], {"name": "capsulas_por_usuario"})],
    "retos": [([("usuario_id", 1), ("semana", 1)], {"unique": True, "name": "un_reto_por_semana"})],
    "usos": [
        ([("usuario_id", 1), ("fecha", -1)], {"unique": True, "name": "un_look_por_dia"}),
        ([("prenda_ids", 1)], {"name": "usos_por_prenda"}),
    ],
}
