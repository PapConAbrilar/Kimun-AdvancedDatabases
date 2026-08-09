# Estado Actual y Traspaso para Big Data

Este documento entrega el estado técnico de Kimün a la persona responsable de
implementar la etapa Big Data. La base de trabajo es la rama `experimental`,
que contiene la migración funcional a DynamoDB, el despliegue reproducible y
las pruebas NoSQL.

## 1. Resumen ejecutivo

La capa operacional está terminada:

- Django persiste los datos funcionales en DynamoDB;
- no existe una conexión SQL activa;
- las sesiones usan cookies firmadas;
- la autenticación recupera usuarios por correo desde DynamoDB;
- la aplicación replica escrituras entre `us-east-1` y `us-west-2`;
- existe failover automático de lectura y escritura principal;
- Terraform y Ansible levantan y configuran el MVP;
- existe una carga demostrativa pequeña e idempotente;
- existen reportes operacionales calculados en Python.

La etapa Big Data todavía no está implementada. Actualmente no existen en
Terraform:

- bucket S3 analítico;
- zona de resultados de Athena;
- base de datos o tablas de Glue Data Catalog;
- crawler de Glue;
- workgroup de Athena;
- exportador batch hacia S3;
- consultas SQL de los cinco KPIs;
- dashboard conectado a Athena.

El dashboard ubicado en `reportes/` no satisface por sí solo el requisito Big
Data: agrega datos operacionales en memoria mediante repositorios DynamoDB.

## 2. Arquitectura operacional disponible

```text
Django en EC2
   |
   +-> Repositorios de dominio
          |
          +-> DynamoDBClient
                 |
                 +-> KimunData-Demo / us-east-1
                 +-> KimunData-Demo / us-west-2
```

Archivos centrales:

| Responsabilidad | Archivo |
|---|---|
| Cliente, failover y escritura dual | `kimun/data_access/dynamodb_client.py` |
| Serialización y repositorio base | `kimun/data_access/base_repository.py` |
| Configuración de regiones y tabla | `kimun/settings.py` |
| Infraestructura AWS | `terraform/main.tf` |
| Configuración EC2 | `ansible/playbook.yml` |
| Carga demostrativa | `usuarios/management/commands/seed_dynamodb.py` |
| Reportes operacionales | `reportes/repository.py` |
| Pruebas NoSQL | `kimun/data_access/tests_nosql.py` |

## 3. Modelo Single-Table real

La tabla usa:

- clave primaria: `PK` y `SK`;
- índice secundario: `GSI1PK` y `GSI1SK`;
- discriminador de entidad: `entity_type`.

Las entidades actuales son:

| `entity_type` | `PK` | `SK` | Uso analítico principal |
|---|---|---|---|
| `USER_PROFILE` | `USER#<correo>` | `PROFILE#<correo>` | dimensión de usuarios y roles |
| `AREA_CARGO` | `AREA#<id>` | `METADATA#<id>` | dimensión organizacional |
| `CATEGORY` | `CATEGORY#<id>` | `METADATA#<id>` | dimensión de categorías |
| `COURSE_METADATA` | `COURSE#<id>` | `METADATA#<id>` | dimensión de cursos |
| `MATERIAL` | `MATERIAL#<id>` | `METADATA#<id>` | contenido por curso |
| `CLASS` | `CLASS#<id>` | `METADATA#<id>` | dimensión de clases |
| `ENROLLMENT` | `USER#<correo>` | `ENROLLMENT#<curso>` | hecho de inscripción y estado |
| `CLASS_PROGRESS` | `USER#<correo>` | `PROGRESS#<clase>` | hecho de progreso académico |
| `QUESTION_BANK` | `BANK#<id>` | `METADATA#<id>` | banco de preguntas |
| `EVALUATION` | `EVALUATION#<id>` | `METADATA#<id>` | dimensión de evaluaciones |
| `QUESTION` | `QUESTION#<id>` | `METADATA#<id>` | preguntas |
| `ALTERNATIVE` | `ALTERNATIVE#<id>` | `METADATA#<id>` | alternativas |
| `EVAL_ATTEMPT` | `USER#<correo>` | `ATTEMPT#<evaluación>#<id>` | hecho principal de rendimiento |
| `TASK` | `TASK#<id>` | `METADATA#<id>` | dimensión de tareas |
| `TASK_SUBMISSION` | `USER#<correo>` | `SUBMISSION#<tarea>` | hecho de entregas y calificaciones |
| `CERTIFICATE` | `CERTIFICATE#<id>` | `METADATA#<id>` | hecho de certificación |
| `CALENDAR_EVENT` | `EVENT#<id>` | `METADATA#<id>` | eventos y vencimientos |
| `ANNOUNCEMENT` | `ANNOUNCEMENT#<id>` | `METADATA#<id>` | comunicaciones |
| `ANNOUNCEMENT_READ` | `USER#<correo>` | `ANNOUNCEMENT_READ#<anuncio>` | interacción con anuncios |
| `REMINDER` | `USER#<correo>` | `REMINDER#<curso>#<tipo>` | recordatorios enviados |

El GSI se usa para colecciones globales y relaciones inversas, por ejemplo:

- `COURSE#<id>` agrupa materiales, clases, evaluaciones, tareas e
  inscripciones;
- `EVAL#<id>` agrupa intentos;
- `TASK#<id>` agrupa entregas;
- `CLASS#<id>` agrupa progreso de usuarios;
- claves `ENTITY#...` o `CATALOG#...` permiten listar entidades raíz.

No asumir que `04_modelado_dynamodb.md` refleja todos los detalles actuales:
ese documento representa el diseño inicial. Los repositorios son la fuente de
verdad para las claves vigentes.

## 4. Datos demostrativos disponibles

El comando `seed_dynamodb` crea en una tabla vacía:

- 7 perfiles de usuario;
- 3 cursos;
- 3 evaluaciones;
- 15 intentos.

El total esperado es 28 ítems por región. Este volumen sirve para probar la
aplicación y la réplica, pero no es suficiente para una demostración Big Data.

Además, la carga actual no genera inscripciones, progreso de clases, entregas
de tareas ni certificados. Por lo tanto, no permite calcular cinco KPIs
representativos sin completar el generador.

## 5. Arquitectura analítica recomendada

Para AWS Learner Lab se recomienda un pipeline batch simple que reutilice
`LabInstanceProfile` y evite crear roles IAM personalizados:

```text
DynamoDB primaria
      |
      v
Comando batch en EC2
      |
      v
S3 / zona raw en JSON Lines o Parquet
      |
      v
Glue Data Catalog
      |
      v
Athena / vistas SQL de KPIs
      |
      v
Dashboard Big Data en Kimün
```

### Por qué se recomienda este camino

- no carga las vistas web con escaneos analíticos;
- separa el sistema operacional del sistema analítico;
- evita depender de Global Tables nativas;
- permite controlar el volumen y costo de cada exportación;
- Athena cumple el requisito explícito del examen;
- es más viable en Learner Lab que Streams + Lambda, porque esta última opción
  normalmente requiere crear o delegar roles IAM adicionales.

No exportar las dos regiones al mismo conjunto sin deduplicación. La escritura
dual produce copias equivalentes; el pipeline debe leer solo la región primaria
o deduplicar por `PK` + `SK`.

## 6. Estructura sugerida del data lake

```text
s3://<bucket-kimun-analytics>/
  raw/
    entity_type=EVAL_ATTEMPT/fecha_carga=AAAA-MM-DD/*.jsonl
    entity_type=ENROLLMENT/fecha_carga=AAAA-MM-DD/*.jsonl
    entity_type=CLASS_PROGRESS/fecha_carga=AAAA-MM-DD/*.jsonl
    entity_type=TASK_SUBMISSION/fecha_carga=AAAA-MM-DD/*.jsonl
    entity_type=CERTIFICATE/fecha_carga=AAAA-MM-DD/*.jsonl
    entity_type=USER_PROFILE/fecha_carga=AAAA-MM-DD/*.jsonl
    entity_type=COURSE_METADATA/fecha_carga=AAAA-MM-DD/*.jsonl
  curated/
    fact_attempts/
    fact_enrollments/
    fact_progress/
    fact_submissions/
    fact_certificates/
    dim_users/
    dim_courses/
    dim_evaluations/
  athena-results/
```

Para el MVP analítico, JSON Lines es suficiente y fácil de inspeccionar. Si el
volumen crece, convertir la zona curada a Parquet para reducir datos escaneados
y costo de Athena.

Cada ejecución debe escribir un manifiesto con:

- fecha y hora UTC;
- región de origen;
- nombre de tabla;
- cantidad de ítems leídos y escritos;
- conteo por `entity_type`;
- archivos generados;
- errores y reintentos;
- identificador único de la exportación.

## 7. Cambios de datos recomendados

Antes de generar grandes volúmenes, agregar campos analíticos denormalizados a
los hechos nuevos:

- `curso_id` dentro de `EVAL_ATTEMPT`;
- `curso_id` dentro de `TASK_SUBMISSION`;
- `categoria_id` y datos temporales relevantes en hechos si se requieren para
  segmentación;
- `fecha_actualizacion` consistente;
- versión de esquema, por ejemplo `schema_version: 1`.

Actualmente un intento contiene `evaluacion_id`, pero no `curso_id`. El
exportador tendría que resolver la evaluación para conocer su curso. Esto
produce lecturas adicionales y dificulta un backfill grande.

Todas las fechas deben exportarse en ISO 8601 UTC. Los valores `Decimal` de
DynamoDB deben transformarse explícitamente antes de serializar JSON.

## 8. Generación de volumen de prueba

No ampliar el comando de demo pequeño hasta millones de escrituras
secuenciales. Crear un comando separado, por ejemplo:

```text
python manage.py generar_dataset_big_data \
  --usuarios 100 \
  --cursos 5 \
  --intentos 1000 \
  --seed 2026
```

Requisitos del generador:

- resultados reproducibles mediante `--seed`;
- relaciones válidas entre usuarios, cursos, evaluaciones y clases;
- fechas distribuidas en varios meses;
- estudiantes activos, inactivos, aprobados y reprobados;
- inscripciones en todos los estados;
- entregas a tiempo y atrasadas;
- certificados aprobados, pendientes y rechazados;
- escritura batch de máximo 25 ítems;
- reintento exponencial de `UnprocessedItems`;
- modo `--dry-run`;
- límite configurable para proteger el presupuesto;
- réplica controlada en ambas regiones o carga en primaria seguida de un
  proceso explícito de copia.

## 9. Cinco KPIs propuestos

| KPI | Cálculo | Decisión de negocio |
|---|---|---|
| Tasa de aprobación por curso | intentos aprobados / estudiantes evaluados | reforzar cursos con baja aprobación |
| Puntaje promedio por curso y mes | promedio de `puntaje_obtenido` | detectar mejoras o deterioro temporal |
| Tasa de finalización | inscripciones completadas / inscripciones totales | priorizar acompañamiento y rediseño curricular |
| Riesgo por inactividad | estudiantes sin progreso durante N días | activar recordatorios o contacto directo |
| Conversión a certificación | certificados aprobados / cursos completados | identificar cuellos de botella administrativos |

KPI alternativo si se desarrolla el módulo de tareas:

- porcentaje de entregas atrasadas por curso y cohorte.

Las consultas deben contar estudiantes o entidades únicas cuando corresponda,
no filas duplicadas por múltiples intentos.

## 10. Plan de implementación sugerido

### Fase 1: infraestructura analítica

Agregar a Terraform:

- bucket S3 con bloqueo de acceso público;
- prefijos `raw`, `curated` y `athena-results`;
- cifrado administrado por S3;
- reglas de expiración para resultados temporales;
- base de datos Glue;
- workgroup de Athena con ubicación de resultados y límite de bytes
  escaneados.

No agregar `aws_iam_role`: Learner Lab exige reutilizar `LabRole` o
`LabInstanceProfile`.

### Fase 2: exportador

Crear un módulo separado, por ejemplo:

```text
big_data/
  exporter.py
  schemas.py
  athena_service.py
  management/commands/exportar_big_data.py
```

El exportador debe paginar el `scan`, filtrar por `entity_type`, normalizar
datos, escribir particiones y publicar el manifiesto.

### Fase 3: catálogo y SQL

1. Crear tablas externas o ejecutar un Glue Crawler.
2. Crear vistas curadas para hechos y dimensiones.
3. Versionar las cinco consultas SQL dentro del repositorio.
4. Validar los resultados contra un dataset pequeño calculado manualmente.

### Fase 4: dashboard

Agregar una capa `AthenaService` que:

- inicie consultas con `boto3`;
- consulte su estado de forma acotada;
- lea resultados paginados;
- convierta valores a tipos Python;
- maneje errores y consultas canceladas;
- evite ejecutar cinco consultas nuevas en cada recarga de página.

El dashboard debe indicar la fecha de actualización del dataset y diferenciar
claramente datos analíticos batch de datos operacionales en tiempo real.

### Fase 5: pruebas y demostración

- probar exportación paginada;
- probar serialización de fechas y `Decimal`;
- comprobar deduplicación por `PK` + `SK`;
- validar conteos por entidad;
- ejecutar las cinco consultas en Athena;
- documentar bytes escaneados y costo estimado;
- ensayar decisiones de negocio derivadas de cada KPI.

## 11. Criterios de aceptación

La implementación Big Data se considera completa cuando:

1. Terraform crea S3, Glue y Athena sin roles IAM personalizados.
2. Una ejecución reproducible exporta datos desde DynamoDB hacia S3.
3. El catálogo reconoce las particiones y esquemas.
4. Athena ejecuta cinco consultas KPI versionadas.
5. El dashboard muestra los cinco resultados y su fecha de actualización.
6. Cada KPI incluye una decisión posible para ALUMCO.
7. La aplicación operacional sigue funcionando durante el proceso analítico.
8. El despliegue y la destrucción dejan Terraform sin deriva.
9. La documentación permite repetir la demo desde una cuenta Learner Lab
   vacía.

## 12. Riesgos y precauciones

- Las credenciales de Learner Lab expiran y no deben guardarse en Git.
- El estado de Terraform es local e ignorado; no crear recursos manuales sin
  importarlos.
- Un `scan` completo en cada solicitud web es incorrecto y costoso.
- No mezclar datos de ambas regiones sin deduplicar.
- La carga sintética debe tener límites de costo.
- Athena cobra por bytes escaneados; particionar y usar Parquet cuando aumente
  el volumen.
- El dataset demo actual usa puntajes aleatorios; un dataset KPI debe usar una
  semilla fija.
- El Security Group del MVP permite SSH desde Internet por motivos académicos;
  no copiar esa decisión a producción.
- Los modelos y pruebas ORM históricos no representan el flujo operacional
  vigente.

## 13. Flujo recomendado para comenzar

```bash
git switch experimental
git pull --ff-only origin experimental
git switch -c feature/big-data
python manage.py test kimun.data_access.tests_nosql
terraform -chdir=terraform validate
```

Leer, en este orden:

1. `08_migracion_nosql_completada.md`;
2. `09_guia_despliegue_demo_mvp.md`;
3. `kimun/data_access/dynamodb_client.py`;
4. los archivos `repository.py` de cada módulo;
5. `reportes/repository.py`;
6. `terraform/main.tf`.

La infraestructura de demostración es efímera. No asumir que existe una EC2 o
una tabla activa al comenzar; ejecutar primero las comprobaciones de AWS y el
plan de Terraform descritos en el documento 09.
