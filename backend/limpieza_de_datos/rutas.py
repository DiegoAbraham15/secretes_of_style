"""Junta las rutas de la carpeta limpieza_de_datos para que principal.py las agregue con una sola línea."""
from fastapi import APIRouter

from limpieza_de_datos.evaluacion_del_modelo import rutas as rutas_evaluacion
from limpieza_de_datos.limpieza_de_datos import rutas as rutas_votos
from limpieza_de_datos.limpieza_de_prendas import rutas as rutas_prendas

rutas = APIRouter()
rutas.include_router(rutas_votos)  # GET /api/votos/limpieza
rutas.include_router(rutas_prendas)  # GET /api/prendas/revision y /api/prendas/{id}/revision
rutas.include_router(rutas_evaluacion)  # GET /api/votos/evaluacion
