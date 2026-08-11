"""Cliente de AWS Athena para ejecutar consultas sobre los datos exportados."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_ANALYTICS_BUCKET", "kimumdata-demo-analytics")
AWS_REGION = os.environ.get("AWS_REGION_PRIMARY", "us-east-1")
ATHENA_DATABASE = "kimun_bigdata"
ATHENA_OUTPUT = f"s3://{S3_BUCKET}/athena-results/"


def _client(region: str | None = None):
    return boto3.client("athena", region_name=region or AWS_REGION)


def run_query(sql: str, database: str | None = None, wait: bool = True, timeout_s: int = 60) -> dict:
    """Ejecuta una consulta en Athena y devuelve los resultados.

    Returns:
        dict con ``rows`` (lista de dicts) y ``columns`` (nombres de columna).
    """
    client = _client()
    db = database or ATHENA_DATABASE

    response = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": db},
        ResultConfiguration={"OutputLocation": ATHENA_OUTPUT},
    )
    execution_id = response["QueryExecutionId"]

    if not wait:
        return {"execution_id": execution_id, "rows": [], "columns": []}

    # Esperar resultado
    elapsed = 0
    while elapsed < timeout_s:
        status = client.get_query_execution(QueryExecutionId=execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            break
        time.sleep(1)
        elapsed += 1

    if state != "SUCCEEDED":
        reason = status["QueryExecution"]["Status"].get("StateChangeReason", state)
        logger.error("Athena query %s terminó en estado %s: %s", execution_id, state, reason)
        return {"execution_id": execution_id, "rows": [], "columns": [], "error": reason}

    # Obtener resultados
    results = client.get_query_results(QueryExecutionId=execution_id)
    result_set = results.get("ResultSet", {})
    rows_data = result_set.get("Rows", [])

    if not rows_data:
        return {"execution_id": execution_id, "rows": [], "columns": []}

    # Primera fila = nombres de columna
    columns = [field.get("VarCharValue", "") for field in rows_data[0].get("Data", [])]

    # Filas siguientes = datos
    rows = []
    for row in rows_data[1:]:
        values = [field.get("VarCharValue", None) for field in row.get("Data", [])]
        rows.append(dict(zip(columns, values)))

    return {"execution_id": execution_id, "rows": rows, "columns": columns}


# ---------------------------------------------------------------------------
# Consultas predefinidas de los 5 KPIs
# ---------------------------------------------------------------------------

KPI_QUERIES: dict[str, dict[str, str]] = {
    "kpi1_tasa_completacion": {
        "titulo": "Tasa de Completación de Cursos",
        "descripcion": "Porcentaje de usuarios inscritos que completaron cada curso.",
        "sql": """
SELECT
    e.cursotitulo AS curso,
    COUNT(*) AS total_inscritos,
    COUNT(CASE WHEN e.estado = 'completado' THEN 1 END) AS completados,
    ROUND(COUNT(CASE WHEN e.estado = 'completado' THEN 1 END) * 100.0 / COUNT(*), 1) AS tasa_completacion_pct
FROM enrollments e
GROUP BY e.cursotitulo
ORDER BY tasa_completacion_pct DESC
LIMIT 20
""",
    },
    "kpi2_rendimiento_promedio": {
        "titulo": "Rendimiento Promedio por Curso",
        "descripcion": "Puntaje promedio de evaluaciones por curso (identifica cursos difíciles).",
        "sql": """
SELECT
    e.cursotitulo AS curso,
    e.titulo AS evaluacion,
    COUNT(*) AS intentos,
    ROUND(AVG(CAST(a.puntaje_obtenido AS DOUBLE)), 1) AS promedio_puntaje,
    ROUND(COUNT(CASE WHEN a.aprobado = TRUE THEN 1 END) * 100.0 / COUNT(*), 1) AS tasa_aprobacion_pct
FROM eval_attempts a
JOIN evaluations e ON a.evaluacion_id = e.id
GROUP BY e.cursotitulo, e.titulo
ORDER BY promedio_puntaje ASC
LIMIT 20
""",
    },
    "kpi3_tasa_certificacion": {
        "titulo": "Tasa de Certificación",
        "descripcion": "Cantidad de certificados emitidos, aprobados y pendientes.",
        "sql": """
SELECT
    estado,
    COUNT(*) AS total,
    COUNT(DISTINCT usuario_id) AS usuarios_unicos
FROM certificates
GROUP BY estado
ORDER BY total DESC
""",
    },
    "kpi4_distribucion_cargos": {
        "titulo": "Distribución de Usuarios por Cargo/Área",
        "descripcion": "Cantidad de colaboradores por área funcional.",
        "sql": """
SELECT
    COALESCE(u.areacargo_nombre, 'Sin área asignada') AS area_cargo,
    COUNT(*) AS total_usuarios
FROM user_profiles u
WHERE u.rol = 'colaborador'
GROUP BY u.areacargo_nombre
ORDER BY total_usuarios DESC
""",
    },
    "kpi5_tiempo_completacion": {
        "titulo": "Tiempo Promedio para Completar un Curso",
        "descripcion": "Días promedio entre inscripción y completación por curso.",
        "sql": """
SELECT
    e.cursotitulo AS curso,
    COUNT(*) AS completados,
    ROUND(AVG(
        DATE_DIFF('day',
            CAST(e.fecha_asignacion AS TIMESTAMP),
            CAST(e.fecha_completado AS TIMESTAMP)
        )
    ), 1) AS dias_promedio_completacion
FROM enrollments e
WHERE e.estado = 'completado'
  AND e.fecha_asignacion IS NOT NULL
  AND e.fecha_completado IS NOT NULL
GROUP BY e.cursotitulo
ORDER BY dias_promedio_completacion ASC
""",
    },
}


def ejecutar_todos_los_kpis() -> dict[str, dict]:
    """Ejecuta los 5 KPIs contra Athena y devuelve un diccionario indexado por clave."""
    resultados: dict[str, dict] = {}
    for key, meta in KPI_QUERIES.items():
        logger.info("Ejecutando KPI: %s", meta["titulo"])
        result = run_query(meta["sql"])
        result["titulo"] = meta["titulo"]
        result["descripcion"] = meta["descripcion"]
        resultados[key] = result
    return resultados
