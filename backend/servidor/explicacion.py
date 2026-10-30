"""Explicación de un atuendo en lenguaje natural, redactada por un modelo local (Ollama).

A* y la lógica proposicional deciden el atuendo; el modelo NO decide nada. Solo recibe los hechos
que ya dedujo el sistema (clima, ocasión, por qué combina cada prenda, ventajas y problemas) y los
convierte en dos o tres oraciones para la persona. Así la explicación no puede inventar razones:
si un hecho no está en la lista, el modelo no lo conoce.
"""

from servidor.logica import (ESTILOS_ARREGLADOS, REGLAS_PRENDA, hechos_de_ocasion, hechos_de_prenda, inferir, por_que_combinan,
                             razonar_clima, se_recargan, ventajas_del_atuendo)
from servidor.ollama import preguntar

INSTRUCCIONES = """Eres el estilista de la app Secrets of Style. Explica a la persona, en dos o tres oraciones
(máximo 70 palabras) en español y hablándole de tú, por qué este atuendo le funciona hoy. Usa SOLO los
datos de abajo y llama a cada prenda como aparece ahí: no inventes prendas, colores, estilos, marcas ni
datos del clima. Si hay un problema, menciónalo con tacto al final.
Escribe un solo párrafo, sin saludar, sin listas, sin markdown y sin emojis.

Datos:
"""
NOMBRE_OCASION = {"diario": "el día a día", "formal": "una ocasión formal", "deporte": "hacer deporte"}
# Cómo se llama el estilo que pide cada ocasión y qué estilos lo cumplen.
ESTILO_DE_LA_OCASION = {"formal": ("formal", ESTILOS_ARREGLADOS), "deporte": ("deportivo", {"deportivo"})}
NOMBRE_CATEGORIA = {"parte_superior": "prenda de arriba", "parte_inferior": "prenda de abajo",
                    "calzado": "calzado", "abrigo": "abrigo", "accesorio": "accesorio"}


def nombre_de(prenda: dict) -> str:
    tipo = prenda.get("subcategoria") or NOMBRE_CATEGORIA[prenda["categoria"]]
    color = {"cafe": "café"}.get(prenda["color_principal"], prenda["color_principal"].replace("_", " "))
    estampado = "" if prenda.get("estampado") in (None, "liso") else f" de estampado {prenda['estampado']}"
    return f"{tipo} {color}{estampado} (estilo {prenda.get('estilo') or 'casual'})"


def hechos_para_explicar(prendas: list[dict], clima: dict, ocasion: str) -> list[str]:
    """Los datos que recibe el modelo, uno por línea. La primera prenda es la base."""
    hechos, deducciones = razonar_clima(set(clima["hechos"]) | hechos_de_ocasion(ocasion))
    base = prendas[0]
    lineas = [
        f"Clima: {clima['descripcion'].lower()}, {round(clima['temperatura_c'])} °C "
        f"(se siente como {round(clima['sensacion_termica_c'])} °C), {clima['probabilidad_lluvia']} % de probabilidad de lluvia.",
        f"Ocasión: {NOMBRE_OCASION.get(ocasion, ocasion)}.",
        *[f"Recomendación por el clima: {d}." for d in deducciones],
        f"Prenda base que eligió la persona: {nombre_de(base)}, abriga {base['nivel_abrigo']} de 5.",
    ]
    for prenda in prendas[1:]:
        motivo = por_que_combinan(base["color_principal"], prenda["color_principal"])
        lineas.append(f"Se agrega {nombre_de(prenda)}: {motivo}.")
    lineas += [f"Ventaja: {v}." for v in ventajas_del_atuendo(prendas, hechos)]
    for prenda in prendas:
        # Las mismas reglas que deciden si una prenda es apta dicen por qué no lo es.
        _, disparadas = inferir(hechos | hechos_de_prenda(prenda), REGLAS_PRENDA)
        lineas += [f"Problema: {regla.nombre} ({nombre_de(prenda)})." for regla in disparadas]
    if any(se_recargan(a, b) for i, a in enumerate(prendas) for b in prendas[i + 1:]):
        lineas.append("Problema: lleva más de un estampado y el atuendo se ve recargado.")
    if ocasion in ESTILO_DE_LA_OCASION:
        estilo, cumplen = ESTILO_DE_LA_OCASION[ocasion]
        if any(p.get("estilo") not in cumplen for p in prendas if p["categoria"] != "accesorio"):
            lineas.append(f"Problema: no todas las prendas son de estilo {estilo}, como pide la ocasión.")
    return lineas


def explicar_atuendo(prendas: list[dict], clima: dict, ocasion: str) -> str:
    datos = "\n".join(f"- {linea}" for linea in hechos_para_explicar(prendas, clima, ocasion))
    aviso = "La explicación con IA no está disponible ahora; revisa que Ollama esté abierto"
    return preguntar(INSTRUCCIONES + datos, aviso, temperatura=0.2).strip()
