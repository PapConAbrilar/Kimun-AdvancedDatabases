-- =============================================================================
-- Kimün Big Data — Athena DDL: Creación de tablas externas
-- =============================================================================
-- Este script crea las tablas externas en Athena que leen directamente los
-- archivos JSON Lines exportados por bigdata/export_to_s3.py desde S3.
--
-- Ejecutar después de que el export se haya completado:
--   aws athena start-query-execution \
--     --query-string "$(cat bigdata/queries/ddl_tablas_externas.sql)" \
--     --query-execution-context Database=kimun_bigdata \
--     --result-configuration OutputLocation=s3://kimun-analytics/athena-results/
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS user_profiles (
    PK STRING,
    SK STRING,
    GSI1PK STRING,
    GSI1SK STRING,
    id STRING,
    pk STRING,
    entity_type STRING,
    email STRING,
    username STRING,
    rol STRING,
    nombre STRING,
    first_name STRING,
    last_name STRING,
    rut STRING,
    cargo_id STRING,
    areacargo_nombre STRING,
    is_active BOOLEAN,
    date_joined STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://S3_ANALYTICS_BUCKET/exports/YYYY-MM-DD/USER_PROFILE/';


CREATE EXTERNAL TABLE IF NOT EXISTS course_metadata (
    PK STRING,
    SK STRING,
    GSI1PK STRING,
    GSI1SK STRING,
    id STRING,
    pk STRING,
    entity_type STRING,
    titulo STRING,
    descripcion STRING,
    docente_creador_id STRING,
    categoria_id STRING,
    estado STRING,
    fecha_limite STRING,
    fecha_creacion STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://S3_ANALYTICS_BUCKET/exports/YYYY-MM-DD/COURSE_METADATA/';


CREATE EXTERNAL TABLE IF NOT EXISTS enrollments (
    PK STRING,
    SK STRING,
    GSI1PK STRING,
    GSI1SK STRING,
    id STRING,
    pk STRING,
    entity_type STRING,
    usuario_id STRING,
    curso_id STRING,
    cursotitulo STRING,
    estado STRING,
    fecha_asignacion STRING,
    fecha_completado STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://S3_ANALYTICS_BUCKET/exports/YYYY-MM-DD/ENROLLMENT/';


CREATE EXTERNAL TABLE IF NOT EXISTS evaluations (
    PK STRING,
    SK STRING,
    GSI1PK STRING,
    GSI1SK STRING,
    id STRING,
    pk STRING,
    entity_type STRING,
    titulo STRING,
    curso_id STRING,
    cursotitulo STRING,
    porcentaje_aprobacion INT,
    max_intentos INT,
    duracion_minutos INT,
    preguntas_por_intento INT,
    creado_por_id STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://S3_ANALYTICS_BUCKET/exports/YYYY-MM-DD/EVALUATION/';


CREATE EXTERNAL TABLE IF NOT EXISTS eval_attempts (
    PK STRING,
    SK STRING,
    GSI1PK STRING,
    GSI1SK STRING,
    id STRING,
    pk STRING,
    entity_type STRING,
    usuario_id STRING,
    evaluacion_id STRING,
    puntaje_obtenido INT,
    aprobado BOOLEAN,
    fecha_intento STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://S3_ANALYTICS_BUCKET/exports/YYYY-MM-DD/EVAL_ATTEMPT/';


CREATE EXTERNAL TABLE IF NOT EXISTS certificates (
    PK STRING,
    SK STRING,
    GSI1PK STRING,
    GSI1SK STRING,
    id STRING,
    pk STRING,
    entity_type STRING,
    usuario_id STRING,
    curso_id STRING,
    codigo_verificacion STRING,
    fecha_emision STRING,
    fecha_aprobacion STRING,
    estado STRING,
    aprobado_por_id STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://S3_ANALYTICS_BUCKET/exports/YYYY-MM-DD/CERTIFICATE/';


CREATE EXTERNAL TABLE IF NOT EXISTS tasks (
    PK STRING,
    SK STRING,
    GSI1PK STRING,
    GSI1SK STRING,
    id STRING,
    pk STRING,
    entity_type STRING,
    titulo STRING,
    descripcion STRING,
    curso_id STRING,
    fecha_limite STRING,
    puntaje_maximo INT,
    creado_por_id STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://S3_ANALYTICS_BUCKET/exports/YYYY-MM-DD/TASK/';


CREATE EXTERNAL TABLE IF NOT EXISTS task_submissions (
    PK STRING,
    SK STRING,
    GSI1PK STRING,
    GSI1SK STRING,
    id STRING,
    pk STRING,
    entity_type STRING,
    tarea_id STRING,
    estudiante_id STRING,
    puntaje_obtenido INT,
    estado STRING,
    fecha_entrega STRING,
    fecha_calificacion STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://S3_ANALYTICS_BUCKET/exports/YYYY-MM-DD/TASK_SUBMISSION/';


CREATE EXTERNAL TABLE IF NOT EXISTS calendar_events (
    PK STRING,
    SK STRING,
    GSI1PK STRING,
    GSI1SK STRING,
    id STRING,
    pk STRING,
    entity_type STRING,
    titulo STRING,
    descripcion STRING,
    tipo STRING,
    fecha_inicio STRING,
    fecha_fin STRING,
    curso_id STRING,
    evaluacion_id STRING,
    creado_por_id STRING,
    color STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://S3_ANALYTICS_BUCKET/exports/YYYY-MM-DD/CALENDAR_EVENT/';


CREATE EXTERNAL TABLE IF NOT EXISTS announcements (
    PK STRING,
    SK STRING,
    GSI1PK STRING,
    GSI1SK STRING,
    id STRING,
    pk STRING,
    entity_type STRING,
    titulo STRING,
    contenido STRING,
    prioridad STRING,
    curso_id STRING,
    publicado BOOLEAN,
    fecha_publicacion STRING,
    fecha_expiracion STRING,
    creado_por_id STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://S3_ANALYTICS_BUCKET/exports/YYYY-MM-DD/ANNOUNCEMENT/';
