"""ETAPA 5 · Entrenamiento de la CNN 1D con PyTorch.

La red: Conv1d(k=2, relleno 1) → BatchNorm → ReLU → Conv1d(k=2) → BatchNorm → ReLU →
promedio → Dropout → lineal. Cambia la salida: un solo valor (logit) con BCEWithLogitsLoss, porque la pregunta
es sí/no (¿le dará corazón?).

Entrenamiento: Adam, lotes de 256, ReduceLROnPlateau, early stopping (paciencia 8) con la
pérdida de VALIDACIÓN y semillas fijas. La prueba se usa una sola vez, al final.

Al terminar exporta los pesos a backend/modelos_entrenados/cnn_atuendos.npz, que es lo único que lee la app
(con numpy, sin PyTorch), y comprueba que la cuenta de numpy da lo mismo que PyTorch.
"""

import copy
import json

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from comun import ARCHIVO_CHECKPOINT, ARCHIVO_METRICAS, ARCHIVO_TENSORES, SEMILLA, titulo
from servidor import red_convolucional

TAMANO_LOTE = 256
EPOCAS = 40
PACIENCIA = 8
TASA_APRENDIZAJE = 0.001


class CNNAtuendos(nn.Module):
    """Entrada [lote, canales, 5 posiciones] → logit de corazón."""

    def __init__(self, canales: int):
        super().__init__()
        self.conv1 = nn.Conv1d(canales, 16, kernel_size=2, padding=1)
        self.bn1 = nn.BatchNorm1d(16)
        self.conv2 = nn.Conv1d(16, 32, kernel_size=2)
        self.bn2 = nn.BatchNorm1d(32)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.dropout = nn.Dropout(0.25)
        self.clasificador = nn.Linear(32, 1)

    def forward(self, x):
        x = torch.relu(self.bn1(self.conv1(x)))
        x = torch.relu(self.bn2(self.conv2(x)))
        x = torch.flatten(self.pool(x), 1)
        return self.clasificador(self.dropout(x))[:, 0]


def cargar():
    titulo("1. CARGANDO LOS TENSORES DE LA ETAPA 4")
    if not ARCHIVO_TENSORES.exists():
        raise FileNotFoundError(f"No existe {ARCHIVO_TENSORES}: corre primero preparacion_tensores.py")
    with np.load(ARCHIVO_TENSORES) as d:
        datos = {nombre: d[nombre] for nombre in d.files}
    if list(datos["canales"]) != red_convolucional.CANALES:
        raise ValueError("Los canales de la etapa 4 no son los de servidor/red_convolucional.py: corre preparacion_tensores.py otra vez")
    for nombre in ("entrenamiento", "validacion", "prueba"):
        print(f"{nombre:14} X={datos[f'X_{nombre}'].shape}")
    return datos


def cargador(datos, nombre, revolver, generador=None):
    x = (datos[f"X_{nombre}"] - datos["media"]) / datos["desviacion"]
    conjunto = TensorDataset(torch.tensor(x, dtype=torch.float32), torch.tensor(datos[f"y_{nombre}"]))
    return DataLoader(conjunto, batch_size=TAMANO_LOTE, shuffle=revolver, generator=generador)


def perdida_promedio(modelo, lotes, criterio):
    modelo.eval()
    total, cuantos = 0.0, 0
    with torch.no_grad():
        for x, y in lotes:
            total += criterio(modelo(x), y).item() * len(y)
            cuantos += len(y)
    return total / cuantos


def probabilidades(modelo, lotes):
    modelo.eval()
    with torch.no_grad():
        return np.concatenate([torch.sigmoid(modelo(x)).numpy() for x, _ in lotes])


def entrenar(datos):
    titulo("2. ENTRENANDO")
    torch.manual_seed(SEMILLA)
    torch.use_deterministic_algorithms(True)
    entrenamiento = cargador(datos, "entrenamiento", True, torch.Generator().manual_seed(SEMILLA))
    validacion = cargador(datos, "validacion", False)
    modelo = CNNAtuendos(len(red_convolucional.CANALES))
    print(f"Parámetros entrenables: {sum(p.numel() for p in modelo.parameters() if p.requires_grad):,}")
    criterio = nn.BCEWithLogitsLoss()
    optimizador = torch.optim.Adam(modelo.parameters(), lr=TASA_APRENDIZAJE)
    planificador = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizador, mode="min", factor=0.5, patience=3, min_lr=1e-5)

    historial, mejor, mejor_epoca, mejor_estado, sin_mejora = [], float("inf"), 0, None, 0
    for epoca in range(1, EPOCAS + 1):
        modelo.train()
        for x, y in entrenamiento:
            optimizador.zero_grad(set_to_none=True)
            criterio(modelo(x), y).backward()
            optimizador.step()
        perdida_train = perdida_promedio(modelo, entrenamiento, criterio)
        perdida_val = perdida_promedio(modelo, validacion, criterio)
        planificador.step(perdida_val)
        historial.append({"epoca": epoca, "perdida_entrenamiento": perdida_train, "perdida_validacion": perdida_val})
        marca = ""
        if perdida_val < mejor:
            mejor, mejor_epoca, mejor_estado, sin_mejora = perdida_val, epoca, copy.deepcopy(modelo.state_dict()), 0
            marca = "  <- mejor"
        else:
            sin_mejora += 1
        print(f"Época {epoca:02d} · pérdida entrenamiento {perdida_train:.4f} · validación {perdida_val:.4f} · "
              f"tasa {optimizador.param_groups[0]['lr']:.5f}{marca}")
        if sin_mejora >= PACIENCIA:
            print("Early stopping: la validación dejó de mejorar")
            break
    modelo.load_state_dict(mejor_estado)
    print(f"Se queda la época {mejor_epoca} (pérdida de validación {mejor:.4f})")
    return modelo, historial, mejor_epoca


def evaluar(modelo, datos):
    """El umbral para decir "sí" se elige en VALIDACIÓN (el que da mejor F1); la prueba solo se mide."""
    titulo("3. EVALUACIÓN")
    p_val = probabilidades(modelo, cargador(datos, "validacion", False))
    umbrales = np.linspace(0.05, 0.95, 91)
    umbral = float(max(umbrales, key=lambda u: f1_score(datos["y_validacion"], p_val >= u)))
    p_prueba = probabilidades(modelo, cargador(datos, "prueba", False))
    y = datos["y_prueba"]
    metricas = {
        "umbral": umbral,
        "exactitud": float(accuracy_score(y, p_prueba >= umbral)),
        "f1": float(f1_score(y, p_prueba >= umbral)),
        "auc": float(roc_auc_score(y, p_prueba)),
        "exactitud_siempre_no": float(1 - y.mean()),
    }
    print(f"Umbral (elegido en validación): {umbral:.2f}")
    print(f"Prueba · exactitud {metricas['exactitud']:.3f} · F1 {metricas['f1']:.3f} · AUC {metricas['auc']:.3f}")
    print(f"Referencia: decir siempre que no acierta {metricas['exactitud_siempre_no']:.3f} (por eso importan F1 y AUC)")
    return metricas, p_prueba


def exportar(modelo, datos, metricas, historial, mejor_epoca, p_prueba):
    titulo("4. EXPORTANDO PARA LA APP")
    torch.save({"model_state_dict": modelo.state_dict(), "canales": red_convolucional.CANALES,
                "orden": red_convolucional.ORDEN, "metricas_prueba": metricas, "mejor_epoca": mejor_epoca},
               ARCHIVO_CHECKPOINT)
    pesos = {nombre: valor.detach().numpy() for nombre, valor in modelo.state_dict().items()
             if not nombre.endswith("num_batches_tracked")}
    np.savez(red_convolucional.ARCHIVO_MODELO, **pesos, eps=np.float32(modelo.bn1.eps),
             media=datos["media"], desviacion=datos["desviacion"], canales=np.array(red_convolucional.CANALES))
    print(f"Pesos para la app: {red_convolucional.ARCHIVO_MODELO} ({red_convolucional.ARCHIVO_MODELO.stat().st_size / 1e3:.1f} KB)")

    # La app hace la cuenta con numpy: debe dar lo mismo que PyTorch en toda la prueba.
    red_convolucional._cargado.clear()
    p_numpy = red_convolucional.probabilidad_de_lote(datos["X_prueba"], red_convolucional.modelo())
    diferencia = float(np.abs(p_numpy - p_prueba).max())
    print(f"Diferencia máxima numpy vs PyTorch en {len(p_prueba):,} looks: {diferencia:.2e}")
    if diferencia > 1e-5:
        raise ValueError("La cuenta con numpy no coincide con PyTorch")

    ARCHIVO_METRICAS.write_text(json.dumps({
        "cnn": metricas, "mejor_epoca": mejor_epoca, "diferencia_numpy_pytorch": diferencia,
        "historial": historial, "parametros": sum(p.numel() for p in modelo.parameters()),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Métricas: {ARCHIVO_METRICAS}")


def main():
    titulo("SECRETS OF STYLE · ETAPA 5 · ENTRENAMIENTO DE LA CNN 1D")
    datos = cargar()
    modelo, historial, mejor_epoca = entrenar(datos)
    metricas, p_prueba = evaluar(modelo, datos)
    exportar(modelo, datos, metricas, historial, mejor_epoca, p_prueba)
    titulo("ETAPA 5 FINALIZADA")


if __name__ == "__main__":
    main()
