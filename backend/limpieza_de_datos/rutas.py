"""Junta las rutas de la carpeta limpieza_de_datos para que principal.py las agregue con una sola línea."""
from fastapi import APIRouter

from limpieza_de_datos.evaluacion_del_modelo import rutas as rutas_evaluacion
from limpieza_de_datos.limpieza_de_datos import rutas as rutas_votos
from limpieza_de_datos.limpieza_de_prendas import rutas as rutas_prendas
from limpieza_de_datos.seleccion_del_modelo import rutas as rutas_seleccion
from limpieza_de_datos.optimizacion_hiperparametros import rutas as rutas_optimizacion
from limpieza_de_datos.segmentacion_kmeans import rutas as rutas_segmentos
from limpieza_de_datos.analisis_de_segmentos import rutas as rutas_analisis_segmentos
from limpieza_de_datos.pca_prendas import rutas as rutas_pca
from limpieza_de_datos.grupos_del_armario import rutas as rutas_grupos

rutas = APIRouter()
rutas.include_router(rutas_votos)  # GET /api/votos/limpieza
rutas.include_router(rutas_prendas)  # GET /api/prendas/revision y /api/prendas/{id}/revision
rutas.include_router(rutas_evaluacion)  # GET /api/votos/evaluacion
rutas.include_router(rutas_seleccion)  # GET /api/votos/seleccion (entrenamiento/validación/prueba)
rutas.include_router(rutas_optimizacion)  # GET /api/votos/optimizacion (hiperparámetros)
rutas.include_router(rutas_segmentos)  # GET /api/prendas/segmentos (K-means)
rutas.include_router(rutas_analisis_segmentos)  # GET /api/prendas/segmentos/analisis (validación de segmentos)
rutas.include_router(rutas_pca)  # GET /api/prendas/pca (reducción de dimensionalidad)
rutas.include_router(rutas_grupos)  # GET /api/prendas/grupos (grupos, mapa y atípicos de la pantalla Estadísticas)
