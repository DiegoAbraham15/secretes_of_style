"""Rescate de prendas olvidadas: el reto de la semana.

  1. OLVIDADAS: prendas disponibles que no se usan hace 60 días o más ("Me lo puse hoy"), o que nunca se han usado y
     llevan al menos 14 días en el armario. Van de la más olvidada a la menos.
  2. RETO: cada semana (ISO, según la fecha del teléfono) se elige la más olvidada que no haya sido reto en las
     últimas 4 semanas y con la que A* pueda armar looks. Se puede cambiar por otra hasta 2 veces o dejarlo pasar.
  3. PROPUESTAS: A* arma 12 looks con la olvidada como base (sin clima: es para cualquier día), se ordenan con los
     gustos (perceptrón, parecido, CNN y colorimetría) y se premian las FAVORITAS (lo que más usas y lo que tiene
     corazón o guardaste). Se toman 3 que cambien la parte de abajo o el calzado entre sí.
  4. CUMPLIDO: si esa semana te pusiste la prenda (un uso que la incluya). Se calcula, no se guarda.
"""

from datetime import date, timedelta

from servidor import colorimetria
from servidor.aprendizaje import reordenar
from servidor.base_datos import ahora, bd, siguiente_id
from servidor.busqueda import recomendar
from servidor.red_convolucional import probabilidades

DIAS_OLVIDO = 60
DIAS_ALTA_MINIMA = 14
SEMANAS_SIN_REPETIR = 4
PROPUESTAS = 3
CANDIDATOS = 12
BONO_FAVORITA = 2.0  # lo que baja el costo de un look por cada favorita: más que el tono (A*) o los gustos (±1.25)
CAMBIOS_POR_SEMANA = 2
FAVORITAS_POR_USO = 8
VECES_FAVORITA = 3  # una prenda usada una o dos veces todavía no es favorita


def semana_de(dia: date) -> str:
    anio, semana, _ = dia.isocalendar()
    return f"{anio}-W{semana:02d}"


def dias_de_la_semana(semana: str) -> list[str]:
    anio, numero = semana.split("-W")
    lunes = date.fromisocalendar(int(anio), int(numero), 1)
    return [(lunes + timedelta(days=i)).isoformat() for i in range(7)]


def olvidadas(armario: list[dict], usos: dict, hoy: date) -> list[tuple[dict, int, bool]]:
    """(prenda, días sin usar, ¿nunca usada?) de la más olvidada a la menos."""
    lista = []
    for prenda in armario:
        if prenda["estado"] != "disponible":
            continue
        ultimo = usos.get(prenda["id"], {}).get("ultimo")
        if ultimo:
            dias = (hoy - date.fromisoformat(ultimo)).days
            if dias >= DIAS_OLVIDO:
                lista.append((prenda, dias, False))
        else:
            alta = (hoy - date.fromisoformat(str(prenda["fecha_creacion"])[:10])).days
            if alta >= DIAS_ALTA_MINIMA:
                lista.append((prenda, alta, True))
    return sorted(lista, key=lambda fila: (-fila[1], fila[0]["id"]))


def favoritas_de(usuario_id: int, usos: dict, gustos: dict) -> set[int]:
    """Las más usadas y las que salen en looks con corazón o guardados."""
    mas_usadas = sorted((i for i in usos if usos[i]["veces"] >= VECES_FAVORITA), key=lambda i: -usos[i]["veces"])[:FAVORITAS_POR_USO]
    con_corazon = {int(i) for firma, voto in gustos["votos"].items() if voto == 1 for i in firma.split("-") if i.isdigit()}
    guardadas = {e["prenda_id"] for a in bd().atuendos.find({"usuario_id": usuario_id}, {"elementos": 1}) for e in a["elementos"]}
    return set(mas_usadas) | con_corazon | guardadas


def distintas(a: dict, b: dict) -> bool:
    """Dos propuestas son distintas si cambian la parte de abajo o el calzado."""
    clave = lambda s: {e["prenda"]["id"] for e in s["elementos"] if e["prenda"]["categoria"] in ("parte_inferior", "calzado")}  # noqa: E731
    return clave(a) != clave(b)


def propuestas_para(prenda: dict, armario: list[dict], gustos: dict, favoritas: set[int]) -> list[dict]:
    sugerencias = recomendar(prenda, armario, set(), cantidad=CANDIDATOS, con_accesorio=gustos["con_accesorio"])["sugerencias"]
    if not sugerencias:
        return []
    cnn = probabilidades([[e["prenda"] for e in s["elementos"]] for s in sugerencias], gustos["preferencias"])
    sugerencias = reordenar(sugerencias, gustos["pesos"], gustos["votos"], gustos["gustados"], cnn)
    sugerencias = colorimetria.ajustar(sugerencias, gustos.get("colorimetria"))
    for s in sugerencias:
        s["costo_reto"] = s["costo_final"] - BONO_FAVORITA * sum(
            e["prenda"]["id"] in favoritas for e in s["elementos"] if e["prenda"]["id"] != prenda["id"])
    sugerencias.sort(key=lambda s: (s["costo_reto"], s["costo"]))
    elegidas = []
    for s in sugerencias:
        if all(distintas(s, e) for e in elegidas):
            elegidas.append(s)
        if len(elegidas) == PROPUESTAS:
            return elegidas
    return elegidas + [s for s in sugerencias if s not in elegidas][:PROPUESTAS - len(elegidas)]


def elegir(usuario_id: int, armario: list[dict], usos: dict, gustos: dict, hoy: date, excluir: set[int]):
    """(prenda, propuestas) de la más olvidada que se pueda rescatar, o None."""
    favoritas = favoritas_de(usuario_id, usos, gustos)
    for prenda, _, _ in olvidadas(armario, usos, hoy):
        if prenda["id"] in excluir:
            continue
        propuestas = propuestas_para(prenda, armario, gustos, favoritas)
        if propuestas:
            return prenda, propuestas
    return None


def recientes(usuario_id: int) -> set[int]:
    """Las prendas que fueron reto (o se cambiaron por otra) en las últimas 4 semanas, contando esta."""
    anteriores = bd().retos.find({"usuario_id": usuario_id}).sort("_id", -1).limit(SEMANAS_SIN_REPETIR + 1)
    return {i for r in anteriores for i in [r["prenda_id"], *r.get("descartadas", [])]}


def reto_de_la_semana(usuario_id: int, armario: list[dict], usos: dict, gustos: dict, hoy: date) -> dict | None:
    """El reto guardado de esta semana (se crea la primera vez). Si su prenda ya no está disponible, se cambia."""
    semana = semana_de(hoy)
    reto = bd().retos.find_one({"usuario_id": usuario_id, "semana": semana})
    por_id = {p["id"]: p for p in armario}
    if reto and por_id.get(reto["prenda_id"], {}).get("estado") == "disponible":
        if all(i in por_id for look in reto["propuestas"] for i in look):
            return reto
        propuestas = propuestas_para(por_id[reto["prenda_id"]], armario, gustos, favoritas_de(usuario_id, usos, gustos))
        bd().retos.update_one({"_id": reto["_id"]}, {"$set": {"propuestas": ids_de(propuestas)}})
        return bd().retos.find_one({"_id": reto["_id"]})
    elegido = elegir(usuario_id, armario, usos, gustos, hoy, recientes(usuario_id))
    if elegido is None:
        return None
    prenda, propuestas = elegido
    if reto:  # la prenda del reto se borró o se archivó: se cambia sin gastar un cambio
        bd().retos.update_one({"_id": reto["_id"]}, {"$set": {"prenda_id": prenda["id"], "propuestas": ids_de(propuestas)}})
        return bd().retos.find_one({"_id": reto["_id"]})
    documento = {"_id": siguiente_id("retos"), "usuario_id": usuario_id, "semana": semana, "prenda_id": prenda["id"],
                 "propuestas": ids_de(propuestas), "estado": "activo", "cambios": 0, "fecha_creacion": ahora()}
    bd().retos.insert_one(documento)
    return documento


def ids_de(propuestas: list[dict]) -> list[list[int]]:
    return [[e["prenda"]["id"] for e in s["elementos"]] for s in propuestas]
