"""¿Vale la pena comprarla? Cuántos looks arma con tu ropa una prenda que viste en una tienda, antes de comprarla.

Usa lo que ya existe:
  1. Lo que vio la IA en la foto de la tienda (deseos.detectado) se vuelve una prenda "virtual" que no se guarda.
  2. A* (busqueda.py) cuenta los looks completos que arma esa prenda como base con la ropa disponible. No se usa el
     clima: lo que interesa es si combina con tu armario, no si sirve para hoy.
  3. Para comparar, se cuentan igual los looks de cada prenda de esa categoría que ya tienes.
  4. Los ejemplos se ordenan con tus gustos (perceptrón, parecido y CNN), como cualquier recomendación.
Nada se guarda ni cuenta como voto.
"""

from statistics import mean

from servidor import colorimetria
from servidor.aprendizaje import reordenar
from servidor.busqueda import recomendar
from servidor.esquemas import CATEGORIAS
from servidor.logica import COLORES, ESTAMPADOS, ESTILOS, por_que_combinan
from servidor.red_convolucional import probabilidades

LOOKS_MAXIMOS = 500  # tope de A* para que un armario enorme no tarde: con 29 prendas, un abrigo arma 295 (0.02 s)
EJEMPLOS = 2
# Si la IA no dijo qué tan abrigadora es (deseos anteriores), lo típico de su categoría (escala de 1 a 5).
ABRIGO_TIPICO = {"parte_superior": 2, "parte_inferior": 3, "calzado": 3, "abrigo": 4, "accesorio": 2}
# Cómo se nombra cada categoría en las frases: (singular, plural, ¿femenino?).
NOMBRE = {
    "parte_superior": ("parte de arriba", "partes de arriba", True),
    "parte_inferior": ("parte de abajo", "partes de abajo", True),
    "calzado": ("par de zapatos", "pares de zapatos", False),
    "abrigo": ("abrigo", "abrigos", False),
    "accesorio": ("accesorio", "accesorios", False),
}


def prenda_del_deseo(deseo: dict) -> dict | None:
    """La prenda de la foto como si estuviera en el armario (id 0, nunca choca con una real). None si no se sabe qué es."""
    visto = deseo.get("detectado") or {}
    categoria, color = visto.get("categoria"), visto.get("color_principal")
    if categoria not in CATEGORIAS or color not in COLORES:
        return None
    abrigo = visto.get("nivel_abrigo")
    return {
        "id": 0,
        "categoria": categoria,
        "subcategoria": visto.get("subcategoria"),
        "color_principal": color,
        "estampado": visto.get("estampado") if visto.get("estampado") in ESTAMPADOS else "liso",
        "estilo": visto.get("estilo") if visto.get("estilo") in ESTILOS else "casual",
        "nivel_abrigo": abrigo if isinstance(abrigo, int) and 1 <= abrigo <= 5 else ABRIGO_TIPICO[categoria],
        "impermeable": visto.get("impermeable") is True,
        "estado": "disponible",
        "url_imagen": deseo["url_imagen"],
    }


def looks_de(prenda: dict, armario: list[dict]) -> dict:
    """Los looks completos que arma la prenda como base (hasta LOOKS_MAXIMOS), sin clima ni ocasión."""
    return recomendar(prenda, armario, set(), cantidad=LOOKS_MAXIMOS, con_accesorio=False)


def parecidas_en_texto(n: int, categoria: str) -> str:
    """"1 parte de arriba parecida", "2 pares de zapatos parecidos"."""
    singular, varias, femenino = NOMBRE[categoria]
    return f"{n} {singular if n == 1 else varias} parecid{'a' if femenino else 'o'}{'' if n == 1 else 's'}"


def veredicto(looks: int, promedio: float | None, parecidas: int, categoria: str, faltantes: list[str]) -> tuple[str, str]:
    """("vale_la_pena" | "piensalo" | "no_combina", la frase que lo explica)."""
    tope = f"{LOOKS_MAXIMOS} o más" if looks >= LOOKS_MAXIMOS else str(looks)
    if looks == 0:
        que = " ni ".join(f"{'una' if NOMBRE[c][2] else 'un'} {NOMBRE[c][0]}" for c in faltantes)
        falta = f" No tienes {que} que combine con ella." if faltantes else ""
        return "no_combina", f"Con tu ropa no se arma ningún look completo: tendrías que comprar algo más para usarla.{falta}"
    if parecidas:
        return "piensalo", (f"Ya tienes {parecidas_en_texto(parecidas, categoria)} (misma categoría y color). "
                            f"Arma {tope} looks, pero se parecerían a los que ya usas.")
    varias = NOMBRE[categoria][1]
    if promedio is None:
        return "vale_la_pena", f"No tienes {varias}: llenaría ese hueco y arma {tope} looks con tu ropa."
    if looks > promedio:
        return "vale_la_pena", (f"Arma {tope} looks con tu ropa, más que tus {varias} ({promedio:.0f} en promedio). "
                                f"Le sacarías mucho provecho.")
    if looks == promedio:
        return "vale_la_pena", f"Arma {tope} looks con tu ropa, igual que tus {varias} ({promedio:.0f} en promedio)."
    return "piensalo", (f"Arma {tope} looks con tu ropa, menos que tus {varias} ({promedio:.0f} en promedio): "
                        f"combinaría con pocas cosas.")


def color_para_ti(prenda: dict, perfil: dict | None) -> dict | None:
    """Qué tan bien le va el color de la prenda a la persona, según su colorimetría (None si no la ha hecho)."""
    if not perfil:
        return None
    nivel = colorimetria.nivel_de_color(prenda["color_principal"], perfil)
    textos = {"favorece": f"Este color está en tu paleta de {perfil['nombre']}: te favorece.",
              "evitar": f"Este color está entre los que conviene evitar en {perfil['nombre']}.",
              "neutral": "Este color no está ni en tu paleta ni entre los que evitar."}
    return {"nivel": nivel, "texto": textos[nivel]}


def analizar(deseo: dict, armario: list[dict], gustos: dict) -> dict | None:
    """Todo lo que la app muestra en "¿Vale la pena?". None si la IA no supo qué prenda es."""
    prenda = prenda_del_deseo(deseo)
    if prenda is None:
        return None
    categoria = prenda["categoria"]
    disponibles = [p for p in armario if p["estado"] == "disponible"]
    resultado = looks_de(prenda, armario)
    looks = resultado["sugerencias"]

    # La comparación: cuántos looks arma cada prenda de esa categoría que ya tienes.
    propias = [p for p in disponibles if p["categoria"] == categoria]
    conteos = [len(looks_de(p, armario)["sugerencias"]) for p in propias]
    promedio = round(mean(conteos), 1) if conteos else None
    parecidas = [p for p in propias if p["color_principal"] == prenda["color_principal"]]
    otras = [p for p in disponibles if p["categoria"] != categoria]
    tipo, mensaje = veredicto(len(looks), promedio, len(parecidas), categoria, resultado["categorias_faltantes"])

    ejemplos = []
    if looks:
        cnn = probabilidades([[e["prenda"] for e in s["elementos"]] for s in looks], gustos["preferencias"])
        ordenados = reordenar(looks, gustos["pesos"], gustos["votos"], gustos["gustados"], cnn)
        ejemplos = colorimetria.ajustar(ordenados, gustos.get("colorimetria"))[:EJEMPLOS]

    return {
        "prenda": prenda,
        "looks": len(looks),
        "looks_tope": len(looks) >= LOOKS_MAXIMOS,
        "promedio_categoria": promedio,
        "comparadas": len(propias),
        "supera": sum(len(looks) > n for n in conteos),
        "parecidas": parecidas,
        "combina_con": sum(bool(por_que_combinan(prenda["color_principal"], p["color_principal"])) for p in otras),
        "otras_prendas": len(otras),
        "faltantes": resultado["categorias_faltantes"],
        "veredicto": tipo,
        "mensaje": mensaje,
        "colorimetria": color_para_ti(prenda, gustos.get("colorimetria")),
        "ejemplos": ejemplos,
    }
