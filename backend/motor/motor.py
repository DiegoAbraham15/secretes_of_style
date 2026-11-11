"""Motor del probador virtual: viste la foto de la persona con una prenda usando CatVTON.

Es un programa aparte del servidor, como Ollama: tiene su propio Python 3.11 (CatVTON fija torch 2.1.2) y
ocupa la GPU. El servidor le pide trabajos por HTTP local y le pasa rutas de archivos; el motor solo acepta
rutas dentro de backend\\privado y backend\\archivos_subidos, y solo escucha en esta computadora.

Ejecutar desde la carpeta backend\\motor:
    .venv\\Scripts\\python -m uvicorn motor:aplicacion --host 127.0.0.1 --port 8001

Cómo viste una prenda (lo que se midió en la Fase 0, en una RTX 4050 de 6 GB):
  1. SegFormer marca en la foto la ropa, la piel, el rostro y el cabello (CPU, ~2 s).
  2. Máscara envolvente, como la de CatVTON: el contorno convexo del torso y los brazos (o de las piernas),
     menos el rostro, el cabello, los accesorios y la otra mitad del cuerpo. Con la silueta exacta de la ropa
     la prenda nueva copiaba el largo de la anterior y los brazos descubiertos salían blancos.
  3. Se quita el fondo de la foto de la prenda (U2-Net, CPU, ~0.6 s): con la puerta o el gancho de fondo,
     CatVTON confundía el estampado.
  4. CatVTON genera a 768x1024 con 20 pasos en bf16 (~30 s y 5.4 GB). Abajo de esa resolución, que es con la
     que se entrenó, los colores salían mal (una playera roja salía rosa o blanca).
  5. Solo la zona de la máscara se pega sobre la foto original, así el rostro y el fondo no cambian.
"""

import gc
import os
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
CARPETA_MOTOR = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA_MOTOR / "catvton"))  # el código de CatVTON importa "model" y "utils"

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from PIL import Image, ImageFilter, ImageOps  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from transformers import AutoModelForSemanticSegmentation, SegformerImageProcessor  # noqa: E402

CARPETA_BACKEND = CARPETA_MOTOR.parent
CARPETAS_PERMITIDAS = [CARPETA_BACKEND / "privado", CARPETA_BACKEND / "archivos_subidos"]
ANCHO, ALTO = 768, 1024
PROPORCION = ANCHO / ALTO  # CatVTON trabaja en 3:4: la foto se recorta a esa proporción, nunca se estira
# Medido el 2026-11-10 con una foto real: 16 pasos se ven igual que 20 y ahorran ~5 s por prenda; con 12
# las mangas salen borrosas. Sin guía (1.0) cada paso cuesta la mitad, pero la prenda pierde el color.
PASOS = 16
GUIA = 2.5  # guidance_scale

# ------------------------------------------------
# 1. ETIQUETAS DE SEGFORMER (mattmdjaga/segformer_b2_clothes)
# ------------------------------------------------

(FONDO, SOMBRERO, CABELLO, LENTES, SUPERIOR, FALDA, PANTALON, VESTIDO, CINTURON, ZAPATO_IZQ, ZAPATO_DER,
 ROSTRO, PIERNA_IZQ, PIERNA_DER, BRAZO_IZQ, BRAZO_DER, BOLSA, BUFANDA) = range(18)

ZONA = {
    "upper": {SUPERIOR, VESTIDO, BUFANDA, BRAZO_IZQ, BRAZO_DER},
    "lower": {FALDA, PANTALON, VESTIDO, CINTURON, PIERNA_IZQ, PIERNA_DER},
}
PROTEGIDO = {
    "upper": {ROSTRO, CABELLO, LENTES, SOMBRERO, FALDA, PANTALON, PIERNA_IZQ, PIERNA_DER, ZAPATO_IZQ, ZAPATO_DER, BOLSA},
    "lower": {ROSTRO, CABELLO, LENTES, SOMBRERO, SUPERIOR, BRAZO_IZQ, BRAZO_DER, ZAPATO_IZQ, ZAPATO_DER, BOLSA},
}
# Si la foto de la prenda la trae puesta una persona (foto de catálogo con modelo), solo se toma la prenda.
PRENDA_DE = {"upper": {SUPERIOR, VESTIDO}, "lower": {PANTALON, FALDA}}
CUERPO = {ROSTRO, BRAZO_IZQ, BRAZO_DER, PIERNA_IZQ, PIERNA_DER}

# ------------------------------------------------
# 2. MODELOS (se cargan la primera vez que se usan)
# ------------------------------------------------

candado = threading.Lock()  # un trabajo a la vez: la GPU no alcanza para dos
modelos = {}


def segmentador():
    if "segformer" not in modelos:
        nombre = "mattmdjaga/segformer_b2_clothes"
        modelos["segformer"] = (SegformerImageProcessor.from_pretrained(nombre),
                                AutoModelForSemanticSegmentation.from_pretrained(nombre).eval())
    return modelos["segformer"]


def quitafondos():
    if "u2net" not in modelos:
        from rembg import new_session
        modelos["u2net"] = new_session("u2net", providers=["CPUExecutionProvider"])
    return modelos["u2net"]


def catvton():
    if "catvton" not in modelos:
        from model.pipeline import CatVTONPipeline
        atencion = snapshot_download("zhengchong/CatVTON", allow_patterns=["mix-48k-1024/attention/*"])
        modelos["catvton"] = CatVTONPipeline(
            base_ckpt="booksforcharlie/stable-diffusion-inpainting",
            attn_ckpt=atencion,
            attn_ckpt_version="mix",
            weight_dtype=torch.bfloat16,
            skip_safety_check=True,
            use_tf32=True,
        )
    return modelos["catvton"]


def liberar_gpu():
    modelos.pop("catvton", None)
    gc.collect()
    torch.cuda.empty_cache()


# ------------------------------------------------
# 3. IMÁGENES
# ------------------------------------------------

def ruta_segura(texto: str, debe_existir: bool = True) -> Path:
    ruta = Path(texto).resolve()
    if not any(ruta.is_relative_to(carpeta.resolve()) for carpeta in CARPETAS_PERMITIDAS):
        raise HTTPException(403, "Ruta fuera de las carpetas del proyecto")
    if debe_existir and not ruta.is_file():
        raise HTTPException(404, f"No existe {ruta.name}")
    return ruta


def abrir(ruta: Path) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")  # respeta la orientación del celular


def etiquetas_de(foto: Image.Image) -> np.ndarray:
    procesador, modelo = segmentador()
    with torch.no_grad():
        salida = modelo(**procesador(images=foto, return_tensors="pt")).logits
    grande = torch.nn.functional.interpolate(salida, size=foto.size[::-1], mode="bilinear", align_corners=False)
    return grande.argmax(1)[0].numpy()


def mascara_envolvente(etiquetas: np.ndarray, tipo: str) -> Image.Image:
    zona = np.isin(etiquetas, list(ZONA[tipo])).astype("uint8")
    mascara = np.zeros_like(zona)
    puntos = cv2.findNonZero(zona)
    if puntos is not None:
        cv2.fillPoly(mascara, [cv2.convexHull(puntos)], 1)
    mascara[np.isin(etiquetas, list(PROTEGIDO[tipo]))] = 0
    lado = max(9, etiquetas.shape[0] // 60)
    mascara = cv2.dilate(mascara, np.ones((lado, lado), np.uint8))
    mascara[np.isin(etiquetas, [ROSTRO, CABELLO])] = 0  # el rostro y el cabello nunca se tocan
    return Image.fromarray(mascara * 255)


def sobre_blanco(imagen: Image.Image, alfa: Image.Image) -> Image.Image:
    """Lo que marca alfa sobre fondo blanco, recortado a su contorno con un margen pequeño."""
    caja = alfa.point(lambda a: 255 if a > 30 else 0).getbbox()
    if caja is None:
        return imagen  # no encontró la prenda: se usa la foto como está
    margen = int(0.04 * max(imagen.size))
    caja = (max(caja[0] - margen, 0), max(caja[1] - margen, 0),
            min(caja[2] + margen, imagen.width), min(caja[3] + margen, imagen.height))
    blanco = Image.new("RGB", imagen.size, "white")
    blanco.paste(imagen, mask=alfa)
    return blanco.crop(caja)


def prenda_sin_fondo(imagen: Image.Image) -> Image.Image:
    """Prenda sola (en gancho, en el piso o en maniquí): U2-Net le quita el fondo."""
    from rembg import remove
    return sobre_blanco(imagen, remove(imagen, session=quitafondos()).getchannel("A"))


prendas_listas = {}  # (ruta, fecha de modificación, tipo) -> imagen ya preparada


def prenda_limpia(ruta: Path, tipo: str) -> Image.Image:
    """La prenda lista para CatVTON. Se guarda en memoria: la misma prenda sale en muchos looks.

    Si en la foto la trae puesta una persona, U2-Net dejaría a toda la persona (con el abrigo rojo de una
    modelo, el gorro gris de pelo salía como mangas grises). Entonces SegFormer marca solo la prenda.
    """
    clave = (str(ruta), ruta.stat().st_mtime, tipo)
    if clave not in prendas_listas:
        imagen = abrir(ruta)
        etiquetas = etiquetas_de(imagen)
        lista = None
        if np.isin(etiquetas, list(CUERPO)).mean() > 0.01:
            zona = np.isin(etiquetas, list(PRENDA_DE[tipo]))
            if zona.mean() > 0.05:
                lista = sobre_blanco(imagen, Image.fromarray(zona.astype("uint8") * 255))
        if len(prendas_listas) >= 40:
            prendas_listas.clear()
        prendas_listas[clave] = lista or prenda_sin_fondo(imagen)
    return prendas_listas[clave]


def caja_de_persona(etiquetas: np.ndarray) -> tuple[int, int, int, int]:
    """Recuadro 3:4 alrededor de la persona, con margen. Si no cabe en la foto, se sale (y se rellena).

    Antes la foto completa se estiraba a 768x1024: una foto cuadrada del iPhone deformaba el cuerpo. Así
    además la persona ocupa todo el recuadro y CatVTON trabaja con más detalle.
    """
    alto_foto, ancho_foto = etiquetas.shape
    filas, columnas = np.nonzero(etiquetas != FONDO)
    if filas.size:
        x0, x1, y0, y1 = columnas.min(), columnas.max() + 1, filas.min(), filas.max() + 1
    else:
        x0, x1, y0, y1 = 0, ancho_foto, 0, alto_foto
    margen = 0.06 * (y1 - y0)
    x0, x1, y0, y1 = x0 - margen, x1 + margen, y0 - margen, y1 + margen
    ancho, alto = x1 - x0, y1 - y0
    if ancho / alto < PROPORCION:
        ancho = alto * PROPORCION
    else:
        alto = ancho / PROPORCION

    def acomodar(centro, lado, limite):  # dentro de la foto si cabe; si no, centrado
        inicio = centro - lado / 2
        return min(max(inicio, 0), limite - lado) if lado <= limite else inicio

    x0 = acomodar((x0 + x1) / 2, ancho, ancho_foto)
    y0 = acomodar((y0 + y1) / 2, alto, alto_foto)
    return round(x0), round(y0), round(x0 + ancho), round(y0 + alto)


def recortar(imagen: Image.Image, caja: tuple, relleno) -> Image.Image:
    """Como Image.crop, pero lo que queda fuera de la foto se rellena con un color."""
    lienzo = Image.new(imagen.mode, (caja[2] - caja[0], caja[3] - caja[1]), relleno)
    lienzo.paste(imagen, (-caja[0], -caja[1]))
    return lienzo


# ------------------------------------------------
# 4. RUTAS
# ------------------------------------------------

aplicacion = FastAPI(title="Motor del probador")


class Validacion(BaseModel):
    foto: str


class Trabajo(BaseModel):
    foto: str
    prenda: str
    tipo: str  # "upper" o "lower"
    salida: str
    pasos: int = PASOS  # se pueden cambiar para comparar calidad contra tiempo
    guia: float = GUIA


@aplicacion.get("/salud")
def salud():
    return {"listo": True, "catvton_en_gpu": "catvton" in modelos, "gpu": torch.cuda.is_available()}


@aplicacion.post("/validar")
def validar(datos: Validacion):
    """Revisa que en la foto se vean el rostro, el torso y las piernas. No usa la GPU."""
    foto = abrir(ruta_segura(datos.foto))
    with candado:
        etiquetas = etiquetas_de(foto)
    total = etiquetas.size
    proporcion = lambda clases: np.isin(etiquetas, list(clases)).sum() / total  # noqa: E731
    if proporcion({ROSTRO}) < 0.002:
        return {"valida": False, "motivo": "No se ve tu rostro. Toma la foto de frente y con buena luz."}
    if proporcion({SUPERIOR, VESTIDO, BRAZO_IZQ, BRAZO_DER}) < 0.03:
        return {"valida": False, "motivo": "No se ve tu torso. Aléjate un poco de la cámara."}
    if proporcion({PANTALON, FALDA, VESTIDO, PIERNA_IZQ, PIERNA_DER}) < 0.03:
        return {"valida": False, "motivo": "No se ven tus piernas. Toma la foto de cuerpo completo."}
    return {"valida": True, "motivo": None}


@aplicacion.post("/vestir")
def vestir(datos: Trabajo):
    if datos.tipo not in ZONA:
        raise HTTPException(422, "El tipo debe ser upper o lower")
    if not 1 <= datos.pasos <= 50 or not 1 <= datos.guia <= 5:
        raise HTTPException(422, "Pasos de 1 a 50 y guía de 1 a 5")
    foto = abrir(ruta_segura(datos.foto))
    ruta_prenda = ruta_segura(datos.prenda)
    salida = ruta_segura(datos.salida, debe_existir=False)
    inicio = time.time()
    with candado:
        etiquetas = etiquetas_de(foto)
        caja = caja_de_persona(etiquetas)
        recorte = recortar(foto, caja, "white")
        mascara = recortar(mascara_envolvente(etiquetas, datos.tipo), caja, 0)
        prenda = prenda_limpia(ruta_prenda, datos.tipo)
        try:
            generada = catvton()(
                image=recorte.resize((ANCHO, ALTO), Image.LANCZOS),
                condition_image=prenda,
                mask=mascara.resize((ANCHO, ALTO), Image.NEAREST),
                num_inference_steps=datos.pasos,
                guidance_scale=datos.guia,
                height=ALTO,
                width=ANCHO,
                generator=torch.Generator(device="cuda").manual_seed(42),
            )[0]
        except torch.cuda.OutOfMemoryError:
            liberar_gpu()
            raise HTTPException(507, "La GPU se quedó sin memoria")
    # Solo la zona de la máscara se pega sobre el recorte, y el recorte vuelve a su lugar en la foto.
    suave = mascara.filter(ImageFilter.GaussianBlur(max(3, recorte.height // 200)))
    recorte = Image.composite(generada.resize(recorte.size, Image.LANCZOS), recorte, suave)
    final = foto.copy()
    final.paste(recorte, caja[:2])
    salida.parent.mkdir(parents=True, exist_ok=True)
    final.save(salida, quality=90)
    return {"segundos": round(time.time() - inicio, 1)}


@aplicacion.post("/liberar")
def liberar():
    """Saca CatVTON de la GPU para que Gemma (Ollama) pueda usarla."""
    with candado:
        liberar_gpu()
    return {"catvton_en_gpu": False}
