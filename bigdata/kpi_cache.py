"""Caché local de KPIs para el dashboard sin depender de Athena en vivo.

Estructura del archivo de caché::

    {
      "fecha_export": "2026-08-09T...",
      "s3_prefix": "exports/2026-08-09",
      "kpis": {
        "kpi1_tasa_completacion": {"rows": [...], "columns": [...]},
        ...
      }
    }

El módulo expone funciones que intentan leer de Athena; si falla (sin
credenciales, sin S3, timeout), devuelven la caché o datos simulados para
que el dashboard siempre muestre algo durante el desarrollo.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

CACHE_DIR = Path(settings.BASE_DIR) / "bigdata" / "cache"
CACHE_FILE = CACHE_DIR / "kpi_cache.json"


def _datos_simulados() -> dict:
    """Devuelve datos de ejemplo para desarrollo sin AWS."""
    return {
        "fecha_export": datetime.now(timezone.utc).isoformat(),
        "s3_prefix": "exports/demo",
        "kpis": {
            "kpi1_tasa_completacion": {
                "titulo": "Tasa de Completación de Cursos",
                "descripcion": "Porcentaje de usuarios inscritos que completaron cada curso.",
                "rows": [
                    {"curso": "Cuidados Básicos del Adulto Mayor", "total_inscritos": "45", "completados": "38", "tasa_completacion_pct": "84.4"},
                    {"curso": "Primeros Auxilios en ELEAM", "total_inscritos": "30", "completados": "22", "tasa_completacion_pct": "73.3"},
                    {"curso": "Marco Legal y Normativas", "total_inscritos": "25", "completados": "15", "tasa_completacion_pct": "60.0"},
                    {"curso": "Gestión Emocional del Cuidador", "total_inscritos": "20", "completados": "10", "tasa_completacion_pct": "50.0"},
                    {"curso": "Nutrición en la Tercera Edad", "total_inscritos": "35", "completados": "28", "tasa_completacion_pct": "80.0"},
                ],
            },
            "kpi2_rendimiento_promedio": {
                "titulo": "Rendimiento Promedio por Curso",
                "descripcion": "Puntaje promedio de evaluaciones por curso.",
                "rows": [
                    {"curso": "Cuidados Básicos del Adulto Mayor", "evaluacion": "Evaluación Final", "intentos": "52", "promedio_puntaje": "78.5", "tasa_aprobacion_pct": "82.7"},
                    {"curso": "Primeros Auxilios en ELEAM", "evaluacion": "Evaluación Final", "intentos": "38", "promedio_puntaje": "71.2", "tasa_aprobacion_pct": "68.4"},
                    {"curso": "Marco Legal y Normativas", "evaluacion": "Evaluación Final", "intentos": "22", "promedio_puntaje": "65.8", "tasa_aprobacion_pct": "59.1"},
                    {"curso": "Gestión Emocional del Cuidador", "evaluacion": "Evaluación Módulo 1", "intentos": "15", "promedio_puntaje": "82.0", "tasa_aprobacion_pct": "93.3"},
                    {"curso": "Nutrición en la Tercera Edad", "evaluacion": "Evaluación Final", "intentos": "40", "promedio_puntaje": "76.0", "tasa_aprobacion_pct": "80.0"},
                ],
            },
            "kpi3_tasa_certificacion": {
                "titulo": "Tasa de Certificación",
                "descripcion": "Cantidad de certificados emitidos, aprobados y pendientes.",
                "rows": [
                    {"estado": "aprobado", "total": "42", "usuarios_unicos": "38"},
                    {"estado": "pendiente", "total": "15", "usuarios_unicos": "12"},
                    {"estado": "rechazado", "total": "3", "usuarios_unicos": "3"},
                ],
            },
            "kpi4_distribucion_cargos": {
                "titulo": "Distribución de Usuarios por Cargo/Área",
                "descripcion": "Cantidad de colaboradores por área funcional.",
                "rows": [
                    {"area_cargo": "Profesional de Atención Directa", "total_usuarios": "28"},
                    {"area_cargo": "Técnico de Atención Directa", "total_usuarios": "22"},
                    {"area_cargo": "Asistente de Trato Directo", "total_usuarios": "18"},
                    {"area_cargo": "Auxiliares de Servicio", "total_usuarios": "12"},
                    {"area_cargo": "Manipuladores de Alimento", "total_usuarios": "10"},
                    {"area_cargo": "Administración y Apoyo", "total_usuarios": "8"},
                    {"area_cargo": "Directivos", "total_usuarios": "2"},
                ],
            },
            "kpi5_tiempo_completacion": {
                "titulo": "Tiempo Promedio para Completar un Curso",
                "descripcion": "Días promedio entre inscripción y completación por curso.",
                "rows": [
                    {"curso": "Cuidados Básicos del Adulto Mayor", "completados": "38", "dias_promedio_completacion": "45.2"},
                    {"curso": "Primeros Auxilios en ELEAM", "completados": "22", "dias_promedio_completacion": "52.8"},
                    {"curso": "Marco Legal y Normativas", "completados": "15", "dias_promedio_completacion": "68.3"},
                    {"curso": "Gestión Emocional del Cuidador", "completados": "10", "dias_promedio_completacion": "38.5"},
                    {"curso": "Nutrición en la Tercera Edad", "completados": "28", "dias_promedio_completacion": "41.7"},
                ],
            },
        },
    }


def cargar_cache() -> dict | None:
    """Carga el archivo de caché si existe."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Archivo de caché corrupto, se ignora.")
    return None


def guardar_cache(data: dict) -> None:
    """Guarda los resultados de KPIs en el archivo de caché."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    logger.info("Caché de KPIs guardada en %s", CACHE_FILE)


def obtener_kpis(forzar_athena: bool = False) -> dict:
    """Obtiene los KPIs (desde caché, Athena, o datos simulados)."""
    # 1. Intentar Athena si se fuerza explícitamente
    if forzar_athena:
        try:
            from bigdata.athena_client import ejecutar_todos_los_kpis
            resultados = ejecutar_todos_los_kpis()
            cache = {"fecha_export": datetime.now(timezone.utc).isoformat(), "kpis": resultados}
            guardar_cache(cache)
            return cache
        except Exception as exc:
            logger.warning("Athena no disponible (%s). Usando caché o simulados.", exc)

    # 2. Intentar caché
    cache = cargar_cache()
    if cache:
        return cache

    # 3. Datos simulados como fallback
    logger.info("Usando datos simulados para el dashboard.")
    simulados = _datos_simulados()
    guardar_cache(simulados)
    return simulados
