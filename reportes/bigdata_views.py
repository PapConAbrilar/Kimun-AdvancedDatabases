"""Dashboard Big Data — vista y lógica de presentación de KPIs."""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from bigdata.kpi_cache import obtener_kpis
from usuarios.decorators import admin_required

logger = logging.getLogger(__name__)

# Interpretaciones de negocio para cada KPI (se muestran en el dashboard)
DECISIONES_NEGOCIO: dict[str, str] = {
    "kpi1_tasa_completacion": (
        "Cursos con tasa de completación inferior al 50% requieren rediseño de "
        "contenidos, extensión de plazos o sesiones de refuerzo presencial. "
        "Un alto abandono indica que el material no se adapta al ritmo del personal "
        "de las residencias ELEAM."
    ),
    "kpi2_rendimiento_promedio": (
        "Cursos con promedio de evaluación inferior al 60% indican que los contenidos "
        "no están siendo comprendidos. Se recomienda asignar instructores de refuerzo, "
        "agregar material complementario o ajustar la dificultad de las evaluaciones."
    ),
    "kpi3_tasa_certificacion": (
        "Un alto número de certificados pendientes sugiere un cuello de botella en la "
        "revisión administrativa. Si hay certificados rechazados, es necesario analizar "
        "los motivos y ajustar los criterios de aprobación."
    ),
    "kpi4_distribucion_cargos": (
        "Áreas con baja representación en la plataforma indican residencias ELEAM que "
        "no están siendo alcanzadas por el programa de capacitación. La ONG puede "
        "focalizar campañas de inscripción en esas áreas específicas."
    ),
    "kpi5_tiempo_completacion": (
        "Cursos que toman más de 60 días en completarse en promedio pueden tener "
        "demasiado contenido para el tiempo disponible del personal. Considere "
        "dividir el curso en módulos más cortos o extender los plazos oficiales."
    ),
}


@login_required
@admin_required
def bigdata_dashboard(request):
    """Vista principal del dashboard de Big Data con los 5 KPIs."""
    cache = obtener_kpis()
    kpis = cache.get("kpis", {})
    fecha_export = cache.get("fecha_export", "N/A")

    # Inyectar la decisión de negocio en cada KPI para el template
    for key, kpi in kpis.items():
        kpi["decision"] = DECISIONES_NEGOCIO.get(key, "")

    # Preparar datos para Chart.js (etiquetas + valores)
    charts: dict[str, dict] = {}

    for key, kpi in kpis.items():
        rows = kpi.get("rows", [])
        if not rows:
            charts[key] = {"labels": [], "datasets": []}
            continue

        # Determinar tipo de gráfico según el KPI
        if key == "kpi3_tasa_certificacion":
            # Pie chart — distribución de estados de certificados
            charts[key] = {
                "labels": [row.get("estado", "") for row in rows],
                "values": [int(row.get("total", 0)) for row in rows],
                "type": "pie",
            }
        elif key == "kpi4_distribucion_cargos":
            # Horizontal bar — distribución por cargo
            charts[key] = {
                "labels": [row.get("area_cargo", "") for row in rows],
                "values": [int(row.get("total_usuarios", 0)) for row in rows],
                "type": "horizontalBar",
            }
        elif key in ("kpi1_tasa_completacion", "kpi2_rendimiento_promedio"):
            # Bar chart — curso vs métrica
            charts[key] = {
                "labels": [row.get("curso", row.get("evaluacion", ""))[:20] for row in rows],
                "datasets": [
                    {
                        "label": kpi.get("titulo", ""),
                        "data": [
                            float(row.get("tasa_completacion_pct", row.get("promedio_puntaje", 0)))
                            for row in rows
                        ],
                    }
                ],
                "type": "bar",
            }
        elif key == "kpi5_tiempo_completacion":
            # Scatter/bar — curso vs días
            charts[key] = {
                "labels": [row.get("curso", "")[:20] for row in rows],
                "datasets": [
                    {
                        "label": "Días promedio",
                        "data": [float(row.get("dias_promedio_completacion", 0)) for row in rows],
                    }
                ],
                "type": "bar",
            }

    return render(
        request,
        "reportes/bigdata_dashboard.html",
        {
            "kpis": kpis,
            "charts_json": json.dumps(charts, ensure_ascii=False),
            "fecha_export": fecha_export,
        },
    )
