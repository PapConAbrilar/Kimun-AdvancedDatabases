"""Management command: crea tablas externas en Athena automáticamente.

Uso:
    python manage.py setup_athena_tables [--database kimun_bigdata]
"""

import logging
import os

from django.core.management.base import BaseCommand

from bigdata.athena_client import ATHENA_DATABASE, ATHENA_OUTPUT, S3_BUCKET, run_query

logger = logging.getLogger(__name__)

# Tablas externas con sus columnas y prefijo de carpeta en S3
_TABLES = {
    "user_profiles": {
        "prefix": "USER_PROFILE",
        "columns": [
            "PK STRING", "SK STRING", "id STRING", "entity_type STRING",
            "email STRING", "username STRING", "rol STRING", "nombre STRING",
            "first_name STRING", "last_name STRING", "rut STRING",
            "cargo_id STRING", "areacargo_nombre STRING", "is_active BOOLEAN",
        ],
    },
    "course_metadata": {
        "prefix": "COURSE_METADATA",
        "columns": [
            "PK STRING", "SK STRING", "id STRING", "entity_type STRING",
            "titulo STRING", "descripcion STRING", "docente_creador_id STRING",
            "categoria_id STRING", "estado STRING", "fecha_limite STRING",
        ],
    },
    "enrollments": {
        "prefix": "ENROLLMENT",
        "columns": [
            "PK STRING", "SK STRING", "id STRING", "entity_type STRING",
            "usuario_id STRING", "curso_id STRING", "cursotitulo STRING",
            "estado STRING", "fecha_asignacion STRING", "fecha_completado STRING",
        ],
    },
    "evaluations": {
        "prefix": "EVALUATION",
        "columns": [
            "PK STRING", "SK STRING", "id STRING", "entity_type STRING",
            "titulo STRING", "curso_id STRING", "cursotitulo STRING",
            "porcentaje_aprobacion INT", "max_intentos INT",
        ],
    },
    "eval_attempts": {
        "prefix": "EVAL_ATTEMPT",
        "columns": [
            "PK STRING", "SK STRING", "id STRING", "entity_type STRING",
            "usuario_id STRING", "evaluacion_id STRING",
            "puntaje_obtenido INT", "aprobado BOOLEAN",
        ],
    },
    "certificates": {
        "prefix": "CERTIFICATE",
        "columns": [
            "PK STRING", "SK STRING", "id STRING", "entity_type STRING",
            "usuario_id STRING", "curso_id STRING", "estado STRING",
        ],
    },
    "tasks": {
        "prefix": "TASK",
        "columns": [
            "PK STRING", "SK STRING", "id STRING", "entity_type STRING",
            "titulo STRING", "curso_id STRING", "fecha_limite STRING",
        ],
    },
    "task_submissions": {
        "prefix": "TASK_SUBMISSION",
        "columns": [
            "PK STRING", "SK STRING", "id STRING", "entity_type STRING",
            "tarea_id STRING", "estudiante_id STRING", "puntaje_obtenido INT", "estado STRING",
        ],
    },
    "calendar_events": {
        "prefix": "CALENDAR_EVENT",
        "columns": [
            "PK STRING", "SK STRING", "id STRING", "entity_type STRING",
            "titulo STRING", "tipo STRING", "fecha_inicio STRING", "fecha_fin STRING",
        ],
    },
    "announcements": {
        "prefix": "ANNOUNCEMENT",
        "columns": [
            "PK STRING", "SK STRING", "id STRING", "entity_type STRING",
            "titulo STRING", "contenido STRING", "prioridad STRING",
        ],
    },
}


def _make_ddl(table_name: str, columns: list[str], location: str) -> str:
    cols = ",\n    ".join(columns)
    return (
        f"CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (\n"
        f"    {cols}\n"
        f") ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'\n"
        f"LOCATION '{location.strip('/')}/'"
    )


class Command(BaseCommand):
    help = "Crea las tablas externas de Athena apuntando al export más reciente en S3."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=ATHENA_DATABASE,
            help=f"Base de datos de Athena (default: {ATHENA_DATABASE})",
        )

    def handle(self, *args, **options):
        database = options["database"]
        self.stdout.write(f"🔍 Buscando exports en s3://{S3_BUCKET}/exports/ …")

        # 1. Crear database si no existe
        self.stdout.write(f"📦 Verificando database {database} …")
        run_query(f"CREATE DATABASE IF NOT EXISTS {database};", database="default")

        # 2. Listar carpetas de export en S3 y tomar la más reciente
        import boto3
        s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION_PRIMARY", "us-east-1"))
        resp = s3.list_objects_v2(
            Bucket=S3_BUCKET, Prefix="exports/", Delimiter="/"
        )
        prefixes = [cp["Prefix"].rstrip("/").split("/")[-1] for cp in resp.get("CommonPrefixes", [])]
        if not prefixes:
            self.stderr.write(
                self.style.ERROR(
                    "❌ No hay exports en S3. Ejecutá 'python manage.py exportar_datos_s3 --solo-export' primero."
                )
            )
            return

        latest = sorted(prefixes)[-1]
        self.stdout.write(f"   Último export: {latest}")

        # 3. Crear cada tabla externa
        created = 0
        for table_name, meta in _TABLES.items():
            location = f"s3://{S3_BUCKET}/exports/{latest}/{meta['prefix']}"
            ddl = _make_ddl(table_name, meta["columns"], location)

            try:
                result = run_query(ddl, database=database)
                if result.get("error"):
                    self.stderr.write(f"   ⚠ {table_name}: {result['error']}")
                else:
                    created += 1
                    self.stdout.write(f"   ✅ {table_name} → {location}")
            except Exception as exc:
                self.stderr.write(f"   ❌ {table_name}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ {created}/{len(_TABLES)} tablas creadas en {database}. "
                f"Ya podés ejecutar 'exportar_datos_s3 --solo-kpis'."
            )
        )
