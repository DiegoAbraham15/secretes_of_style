"""Consultas a MongoDB que usan varias partes del servidor (la API y los módulos de análisis de limpieza_de_datos).

Viven aquí y no en principal.py porque principal importa limpieza_de_datos: si limpieza_de_datos importara
principal, se importarían en círculo.
"""

from servidor.base_datos import bd, como_dict


def prendas_de(usuario_id: int) -> list[dict]:
    """Todas las prendas de la persona, de la más vieja a la más nueva, como las responde la API."""
    return [como_dict(p) for p in bd().prendas.find({"usuario_id": usuario_id}).sort("_id", 1)]


def votos_de(usuario_id: int) -> list[dict]:
    """Los votos de la persona, del más viejo al más nuevo (el ObjectId crece con el tiempo)."""
    campos = {"_id": 0, "firma": 1, "me_gusta": 1, "caracteristicas": 1}
    return list(bd().votos_atuendo.find({"usuario_id": usuario_id}, campos).sort("_id", 1))


def uso_por_prenda(usuario_id: int) -> dict[int, dict]:
    """Cuántas veces se usó cada prenda y cuándo fue la última ("Me lo puse hoy"), contando todos los días.

    No se guardan contadores en las prendas: se calculan de usos, así nunca se desfasan al deshacer un día.
    """
    filas = bd().usos.aggregate([
        {"$match": {"usuario_id": usuario_id}},
        {"$unwind": "$prenda_ids"},
        {"$group": {"_id": "$prenda_ids", "veces": {"$sum": 1}, "ultimo": {"$max": "$fecha"}}},
    ])
    return {fila["_id"]: {"veces": fila["veces"], "ultimo": fila["ultimo"]} for fila in filas}


def preferencias_de(usuario_id: int) -> dict | None:
    """Las respuestas del cuestionario de estilo (embebidas en el usuario); None si todavía no lo contesta."""
    usuario = bd().usuarios.find_one({"_id": usuario_id, "preferencias": {"$exists": True}}, {"preferencias": 1})
    return usuario["preferencias"] if usuario else None
