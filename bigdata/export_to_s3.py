"""Exporta los datos de DynamoDB hacia S3 en formato JSON Lines particionado.

La elección de un script custom sobre ``ExportTableToPointInTime`` obedece a:
- No requiere PITR habilitado (ahorra costos en Learner Lab).
- El formato de salida es JSON Lines plano, listo para Athena (sin necesidad de
  transformar el JSON anidado de DynamoDB).
- Permite filtrar y agrupar por ``entity_type`` antes de escribir.
- El scan se pagina automáticamente y ejecuta en segundos sobre tablas chicas.
"""

from __future__ import annotations

import gzip
import json
import logging
import os
from datetime import datetime, timezone

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)

# Archivos de configuración (sin dependencia de Django settings para CLI standalone)
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE_NAME", "KimunData-Demo")
S3_BUCKET = os.environ.get("S3_ANALYTICS_BUCKET", "kimumdata-demo-analytics")
AWS_REGION = os.environ.get("AWS_REGION_PRIMARY", "us-east-1")

ENTITY_TYPES = [
    "USER_PROFILE",
    "AREA_CARGO",
    "COURSE_METADATA",
    "CATEGORY",
    "MATERIAL",
    "CLASS",
    "ENROLLMENT",
    "CLASS_PROGRESS",
    "EVALUATION",
    "QUESTION",
    "QUESTION_BANK",
    "EVAL_ATTEMPT",
    "TASK",
    "TASK_SUBMISSION",
    "CERTIFICATE",
    "CALENDAR_EVENT",
    "ANNOUNCEMENT",
    "ANNOUNCEMENT_READ",
    "REMINDER",
]


def _flatten_item(raw: dict) -> dict:
    """Convierte un item DynamoDB (con tipos) a un diccionario plano JSON."""
    flat: dict[str, object] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            # DynamoDB typed value: {"S": "...", "N": "...", "BOOL": ...}
            flat[key] = _unwrap_dynamodb_value(value)
        elif isinstance(value, list):
            flat[key] = [_unwrap_dynamodb_value(v) if isinstance(v, dict) else v for v in value]
        else:
            flat[key] = value
    return flat


def _unwrap_dynamodb_value(typed: dict) -> object:
    """Desenvuelve un valor tipado de DynamoDB."""
    if "S" in typed:
        return typed["S"]
    if "N" in typed:
        n = typed["N"]
        return int(n) if "." not in n else float(n)
    if "BOOL" in typed:
        return typed["BOOL"]
    if "NULL" in typed:
        return None
    if "L" in typed:
        return [_unwrap_dynamodb_value(v) if isinstance(v, dict) else v for v in typed["L"]]
    if "M" in typed:
        return {k: _unwrap_dynamodb_value(v) if isinstance(v, dict) else v for k, v in typed["M"].items()}
    # Valor crudo (poco común)
    return typed


def _scan_table(table) -> list[dict]:
    """Escanea la tabla DynamoDB completa con paginación."""
    items: list[dict] = []
    params: dict = {}
    while True:
        response = table.scan(**params)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        params["ExclusiveStartKey"] = last_key
    return items


def export_to_s3(
    table_name: str | None = None,
    bucket: str | None = None,
    region: str | None = None,
    prefix: str | None = None,
    compress: bool = True,
) -> dict[str, int]:
    """Escanea DynamoDB y escribe los datos en S3 particionados por entity_type.

    Returns:
        dict con ``{entity_type: count}`` para cada tipo exportado.
    """
    table_name = table_name or DYNAMODB_TABLE
    bucket = bucket or S3_BUCKET
    region = region or AWS_REGION
    prefix = prefix or f"exports/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    logger.info("Escaneando DynamoDB tabla=%s región=%s …", table_name, region)
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)
    raw_items = _scan_table(table)
    logger.info("Leídos %d items de DynamoDB.", len(raw_items))

    # Aplanar y agrupar por entity_type
    grouped: dict[str, list[dict]] = {}
    unknown = 0
    for raw in raw_items:
        item = _flatten_item(raw)
        entity = item.get("entity_type", "__UNKNOWN__")
        if entity == "__UNKNOWN__":
            unknown += 1
        grouped.setdefault(entity, []).append(item)

    if unknown:
        logger.warning("%d items sin entity_type — se guardan como __UNKNOWN__.", unknown)

    # Escribir a S3
    s3 = boto3.client("s3", region_name=region)
    counts: dict[str, int] = {}

    for entity_type, items in sorted(grouped.items()):
        lines = "\n".join(json.dumps(item, default=str, ensure_ascii=False) for item in items)
        body = gzip.compress(lines.encode("utf-8")) if compress else lines.encode("utf-8")
        ext = "jsonl.gz" if compress else "jsonl"
        key = f"{prefix}/{entity_type}/data.{ext}"

        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/x-gzip" if compress else "application/json",
            Metadata={"entity_type": entity_type, "item_count": str(len(items))},
        )
        counts[entity_type] = len(items)
        logger.info("  s3://%s/%s  → %d items", bucket, key, len(items))

    logger.info("Exportación completada: %d tipos, %d items totales.", len(counts), sum(counts.values()))
    return counts
