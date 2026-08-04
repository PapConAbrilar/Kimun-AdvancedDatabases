# Plan de Implementación de la Migración a DynamoDB

## 1. Propósito

Este documento transforma la propuesta de migración de Kimün en un plan ejecutable,
incremental y reversible. La solución conserva una arquitectura híbrida:

- **PostgreSQL** mantiene los datos relacionales de identidad y catálogo.
- **Amazon DynamoDB** recibe los datos operacionales de mayor concurrencia:
  inscripciones, progreso, evaluaciones publicadas e intentos.
- **Amazon S3, AWS Glue y Amazon Athena** reciben el histórico analítico para
  reportes agregados sin cargar la base operacional.
- **Terraform** aprovisiona la infraestructura y **Ansible** configura las
  instancias que ejecutan Django.

La migración se realizará por dominios y mediante banderas de funcionalidad. No
se eliminarán tablas ni datos relacionales hasta que termine el período de
estabilización.

## 2. Objetivos y criterios globales de éxito

### Objetivos

1. Mover las lecturas y escrituras de alta concurrencia a DynamoDB sin interrumpir
   el servicio.
2. Mantener autenticación, permisos, usuarios, cursos y demás relaciones
   administrativas en PostgreSQL.
3. Sustituir los `JOIN` operacionales por patrones de acceso explícitos y
   consultas por clave.
4. Derivar los reportes globales hacia S3 y Athena.
5. Disponer de infraestructura repetible, monitoreo, respaldo y reversión.

### Criterios de aceptación

La migración se considerará terminada cuando se cumplan simultáneamente estos
criterios:

- 100 % de los registros incluidos en el alcance están migrados y conciliados.
- No existen registros huérfanos ni diferencias en campos críticos.
- Las lecturas en sombra no presentan divergencias durante siete días
  consecutivos.
- La cola de reintentos y la DLQ están vacías antes de cada cambio de fuente.
- La tasa de errores no supera la línea base de la aplicación.
- La latencia `p95` de cada flujo migrado es igual o menor que la línea base
  relacional registrada en la fase inicial.
- Existe una prueba documentada de restauración desde respaldo.
- La reversión mediante banderas de funcionalidad tarda menos de 15 minutos.
- Los reportes operacionales entregan datos actuales y los analíticos cumplen una
  frescura máxima acordada de 24 horas.

## 3. Alcance

### Datos que permanecen en PostgreSQL

| Dominio | Modelos principales | Motivo |
|---|---|---|
| Identidad y autorización | `Usuario`, `AreaCargo`, grupos y permisos | Django Admin y autenticación dependen del modelo relacional |
| Catálogo de cursos | `Categoria`, `Curso`, `Clase`, `Material` | Relaciones administrativas, edición y archivos |
| Operación complementaria | `Certificado`, `Tarea`, `EntregaTarea`, `Anuncio`, `LecturaAnuncio`, `Recordatorio` | No son el primer cuello de botella y conservan relaciones fuertes |
| Calendario | `EventoCalendario` | Tiene claves foráneas a cursos y evaluaciones |
| Autoría de evaluaciones | `BancoPreguntas` y metadatos mínimos de `Evaluacion` | Permite conservar el flujo de creación y la integración con calendario durante la transición |

Los archivos continúan fuera de la base de datos. Antes de producción se debe
unificar el backend de almacenamiento en S3; la configuración actual con Supabase
se mantendrá hasta completar esa tarea específica.

### Datos que se migran a DynamoDB

| Dominio | Origen relacional | Destino |
|---|---|---|
| Inscripciones | `InscripcionCurso` | Ítem de inscripción por usuario y curso |
| Progreso | `ClaseCompletado` | Ítem de progreso por usuario, curso y clase |
| Evaluación publicada | `Evaluacion`, `Pregunta`, `Alternativa` | Documento versionado e inmutable para rendición |
| Intentos | `IntentoEvaluacion` | Ítem por intento, con respuestas y resultado |

La evaluación editable continúa en PostgreSQL. Al publicarla se genera una
versión inmutable en DynamoDB. Así se evita que una edición posterior cambie las
preguntas de un intento ya rendido y se conserva la relación que
`EventoCalendario` mantiene con `Evaluacion`.

### Fuera de alcance inicial

- Eliminar PostgreSQL por completo.
- Migrar autenticación o sesiones de Django a DynamoDB.
- Migrar tareas, certificados, anuncios o recordatorios.
- Reemplazar el almacenamiento de archivos en la misma ventana que los datos.
- Construir nuevos indicadores de negocio no existentes.

## 4. Arquitectura objetivo

```text
Usuarios
   |
ALB
   |
Django en EC2
   |---------------- PostgreSQL
   |                  usuarios, permisos, cursos, autoría y calendario
   |
   |---------------- DynamoDB: KimunData-<ambiente>
   |                  inscripciones, progreso, versiones e intentos
   |
   |---------------- S3
                      exportaciones y datos analíticos en Parquet
                           |
                           +-- Glue Data Catalog
                           +-- Athena
```

Los componentes de aplicación no accederán directamente a `boto3` desde las
vistas. Se crearán repositorios por dominio y servicios de aplicación que
permitan cambiar la fuente de lectura o escritura mediante configuración.

## 5. Diseño físico de DynamoDB

### Tabla y capacidad

- Nombre por ambiente: `KimunData-dev`, `KimunData-staging` y
  `KimunData-production`.
- Clave primaria compuesta: `PK` y `SK`, ambas de tipo `String`.
- Capacidad inicial: `PAY_PER_REQUEST`.
- Cifrado en reposo habilitado.
- Point-in-Time Recovery habilitado en `staging` y `production`.
- DynamoDB Streams habilitado con imagen nueva y antigua.
- Time to Live reservado en el atributo `expires_at`; no se aplicará a datos
  académicos mientras no exista una política de retención aprobada.

### Nomenclatura de ítems

| Tipo de ítem | `PK` | `SK` | Atributos relevantes |
|---|---|---|---|
| Inscripción | `USER#<usuario_id>` | `COURSE#<curso_id>` | `entity_type`, `status`, `assigned_at`, `legacy_id`, `GSI1PK`, `GSI1SK`, `version` |
| Progreso de clase | `USER#<usuario_id>` | `PROGRESS#COURSE#<curso_id>#CLASS#<clase_id>` | `completed_at`, `legacy_id`, `GSI1PK`, `GSI1SK`, `version` |
| Resumen de evaluación | `COURSE#<curso_id>` | `EVAL#<evaluacion_id>` | `title`, `pass_percentage`, `max_attempts`, `published_version` |
| Contenido de evaluación | `EVAL#<evaluacion_id>` | `VERSION#<version>` | `questions`, `duration_minutes`, `question_count`, `content_hash` |
| Intento | `USER#<usuario_id>` | `ATTEMPT#EVAL#<evaluacion_id>#<fecha_iso>#<intento_id>` | `score`, `passed`, `answers`, `evaluation_version`, `GSI1PK`, `GSI1SK` |

Todos los ítems deben incluir `schema_version`, `created_at`, `updated_at` y un
identificador idempotente. Las fechas se guardarán en UTC con formato ISO 8601.
Los identificadores relacionales se conservarán para trazabilidad.

### Índice invertido `GSI1`

El índice tendrá `GSI1PK` como clave de partición y `GSI1SK` como clave de
ordenación. Estos atributos deben escribirse explícitamente; DynamoDB no invierte
`PK` y `SK` de manera automática.

| Tipo | `GSI1PK` | `GSI1SK` | Consulta resuelta |
|---|---|---|---|
| Inscripción | `COURSE#<curso_id>` | `USER#<usuario_id>` | Alumnos inscritos en un curso |
| Progreso | `COURSE#<curso_id>` | `USER#<usuario_id>#CLASS#<clase_id>` | Progreso de alumnos de un curso |
| Intento | `EVAL#<evaluacion_id>` | `<fecha_iso>#USER#<usuario_id>` | Intentos de una evaluación |

### Límite de tamaño

DynamoDB admite un máximo de 400 KB por ítem. El publicador debe calcular el
tamaño serializado antes de escribir:

- Hasta 300 KB, el contenido de la evaluación se guarda como un documento.
- Sobre 300 KB, se guarda un ítem `VERSION#<version>` con metadatos y un ítem
  `QUESTION#<version>#<pregunta_id>` por pregunta bajo la misma partición
  `EVAL#<evaluacion_id>`.
- Archivos y contenido binario nunca se almacenan en DynamoDB.

El margen de 100 KB permite agregar atributos, índices y futuras versiones sin
alcanzar el límite del servicio.

## 6. Cambios requeridos en Django

### Capa de acceso

Crear el paquete `kimun/data_access/` con estas interfaces:

- `EnrollmentRepository`
- `ProgressRepository`
- `PublishedEvaluationRepository`
- `AttemptRepository`

Cada interfaz tendrá una implementación SQL y otra DynamoDB. Las vistas,
formularios, señales, comandos y reportes deberán utilizar servicios de dominio,
no llamadas directas a `Model.objects` para los datos migrados.

### Configuración

Definir variables por dominio, nunca una única bandera global:

```text
ENROLLMENT_READ_SOURCE=sql|dynamodb
PROGRESS_READ_SOURCE=sql|dynamodb
EVALUATION_READ_SOURCE=sql|dynamodb
ATTEMPT_READ_SOURCE=sql|dynamodb
MIGRATION_DUAL_WRITE=true|false
MIGRATION_SHADOW_READ=true|false
AWS_REGION=<region>
DYNAMODB_TABLE_NAME=<tabla>
```

Los valores predeterminados deben mantener SQL para desarrollo local. Los
secretos no se guardarán en el repositorio; EC2 accederá a AWS mediante un rol
IAM.

### Consistencia e idempotencia

Durante la primera etapa, PostgreSQL será la fuente de escritura y una tabla
`migration_outbox` registrará, dentro de la misma transacción, el evento que debe
replicarse a DynamoDB. Un worker procesará los eventos con reintentos
exponenciales y una clave idempotente.

Antes del corte definitivo de escritura:

1. La aplicación escribirá el dato en DynamoDB mediante `TransactWriteItems`.
2. La misma transacción creará un ítem de evento para el stream.
3. Un consumidor idempotente mantendrá actualizada la copia SQL durante 14 días.
4. Los eventos fallidos irán a SQS con DLQ y alarmas.

Las actualizaciones usarán `version` y expresiones condicionales para impedir que
un reintento antiguo sobrescriba datos más recientes.

### Dependencias detectadas

Antes de cambiar cada fuente se deben adaptar, como mínimo:

- `usuarios.views`: inicio, inscripción individual y masiva, mis cursos y perfil.
- `cursos.views`: detalle, finalización de clases y cálculo de progreso.
- `evaluaciones.views`: listado, publicación, rendición, límite de intentos y
  resultados.
- `reportes.views`: dashboard, reportes por curso/usuario y mapa de progreso.
- `calendario.views`: filtrado de eventos según las inscripciones.
- `usuarios.utils`: recordatorios y notificaciones asociados a inscripciones.
- Django Admin y comandos de gestión que consultan o eliminan modelos migrados.

Los reportes que actualmente usan `Count`, `Avg`, `select_related` o filtros a
través de varias relaciones no deben traducirse a `Scan`. Los reportes de un
usuario o curso usarán consultas por clave; los agregados globales pasarán a
Athena.

## 7. Estrategia de migración de datos

### Precondiciones

- Si producción aún usa SQLite, migrarla primero a PostgreSQL. SQLite no es
  apropiada para el patrón de outbox y la concurrencia del despliegue objetivo.
- Disponer de un respaldo restaurable de la base relacional.
- Congelar cambios de esquema en los modelos incluidos durante el backfill.
- Definir zona AWS, cuentas, ambientes y responsables operacionales.
- Documentar volumen de registros, tamaño promedio y crecimiento por dominio.

### Backfill

Se implementará el comando idempotente:

```text
python manage.py migrate_to_dynamodb \
  --entity <enrollments|progress|evaluations|attempts> \
  --batch-size 100 \
  --resume-from <checkpoint> \
  --dry-run
```

El comando deberá:

1. Leer registros ordenados por clave primaria y en lotes.
2. Transformar fechas a UTC y normalizar estados.
3. Preservar `legacy_id` y generar `content_hash`.
4. Usar `BatchWriteItem`, reintentando `UnprocessedItems`.
5. No sobrescribir una versión más reciente.
6. Guardar el último checkpoint completado.
7. Emitir contadores de leídos, escritos, omitidos y fallidos.
8. Producir un manifiesto de ejecución sin incluir respuestas ni datos personales.

### Conciliación

Se implementará un segundo comando:

```text
python manage.py verify_dynamodb_migration \
  --entity <entidad> \
  --full
```

La verificación comparará:

- Conteo total por entidad y estado.
- Claves de negocio únicas.
- Hash de los campos críticos.
- Referencias a usuarios, cursos, clases y evaluaciones existentes.
- Número de intentos por usuario y evaluación.
- Puntajes, estado de aprobación y versión de evaluación.

La conciliación completa debe terminar sin diferencias antes de habilitar
lecturas desde DynamoDB.

## 8. Fases de ejecución

Las duraciones son estimaciones para un equipo pequeño y deben ajustarse después
de medir el volumen real.

| Fase | Duración | Actividades principales | Entregable / criterio de salida |
|---|---:|---|---|
| 0. Descubrimiento y línea base | 2 días | Inventariar consultas, volumen, latencia, errores y dependencias; confirmar PostgreSQL | Matriz de accesos y línea base aprobadas |
| 1. Infraestructura | 3 días | Crear módulos Terraform, roles IAM, tabla, índices, streams, S3, Glue, Athena, SQS, DLQ y alarmas; configurar EC2 con Ansible | `dev` y `staging` reproducibles y validados |
| 2. Capa de acceso | 4 días | Implementar repositorios SQL/DynamoDB, servicios, banderas, outbox, consumidor y pruebas | Aplicación funciona con SQL detrás de las nuevas interfaces |
| 3. Progreso | 2 días | Doble escritura, backfill, conciliación, sombra y corte de `ClaseCompletado` | Progreso leído desde DynamoDB |
| 4. Intentos y evaluación publicada | 4 días | Versionar evaluaciones, migrar contenido e intentos, adaptar rendición y límites | Rendición e intentos operan en DynamoDB |
| 5. Inscripciones | 3 días | Migrar inscripción individual/masiva, listados y permisos dependientes | Inscripciones operan en DynamoDB |
| 6. Reportes y analítica | 3 días | Reescribir reportes operacionales; exportar a Parquet, catalogar y crear consultas Athena | Dashboard validado y consultas analíticas disponibles |
| 7. Corte y estabilización | 14 días calendario | Activar escritura primaria en DynamoDB por dominio, mantener espejo SQL, observar y probar reversión | Siete días sin divergencias ni eventos pendientes |
| 8. Cierre | 1 día | Desactivar espejo, archivar evidencias y decidir retiro de tablas | Acta técnica y backlog de limpieza aprobados |

### Orden de corte por dominio

El orden será progreso, intentos, evaluación publicada e inscripciones. Progreso
es el dominio de menor impacto relacional y permite validar el mecanismo. Las
inscripciones se dejan al final porque participan en permisos, dashboards,
recordatorios, calendario y múltiples reportes.

Para cada dominio se aplicará el mismo ciclo:

1. Desplegar la implementación sin cambiar el comportamiento.
2. Activar doble escritura.
3. Ejecutar backfill.
4. Conciliar el 100 %.
5. Activar lecturas en sombra y comparar resultados.
6. Cambiar la fuente de lectura en `staging`, ejecutar pruebas y luego repetir en
   producción.
7. Cambiar la fuente de escritura.
8. Mantener el espejo SQL y observar durante el período acordado.

## 9. Pruebas

### Automatizadas

- Pruebas unitarias de serialización, claves y repositorios.
- Pruebas de contrato para ejecutar los mismos casos contra SQL y DynamoDB.
- Pruebas de idempotencia, reintentos y control de versión.
- Pruebas de ítems cercanos a 300 KB y de partición de preguntas.
- Pruebas de permisos para administrador, docente y colaborador.
- Pruebas de regresión de las vistas y reportes afectados.
- Pruebas de infraestructura con `terraform fmt`, `terraform validate` y un plan
  revisado.

Para desarrollo se usará DynamoDB Local o LocalStack. La validación de Streams,
IAM, PITR y exportaciones se realizará en una cuenta AWS de `staging`.

### Funcionales críticas

1. Inscribir un usuario de forma individual y masiva sin duplicados.
2. Listar los cursos de un usuario y los alumnos de un curso.
3. Completar una clase dos veces sin crear progreso duplicado.
4. Publicar una evaluación y conservar una versión inmutable.
5. Rendir una evaluación respetando duración y máximo de intentos.
6. Consultar resultados aun después de editar la evaluación original.
7. Calcular progreso y estado de curso.
8. Generar reportes por usuario, curso y evaluación.
9. Recuperar un evento fallido desde la DLQ.
10. Cambiar cada bandera nuevamente a SQL sin reiniciar la base de datos.

### Rendimiento

Ejecutar cargas con un conjunto anonimizado que represente el volumen esperado.
Medir latencia `p50`, `p95`, errores, throttling y consumo por patrón de acceso.
No se aprobará una consulta que dependa de `Scan` en producción.

## 10. Observabilidad y operación

Crear un panel de CloudWatch con:

- Latencia y errores de la aplicación por repositorio.
- `ConsumedReadCapacityUnits` y `ConsumedWriteCapacityUnits`.
- `ThrottledRequests`, `SystemErrors` y errores condicionales.
- Edad y cantidad de eventos pendientes.
- Mensajes visibles y acumulados en SQS/DLQ.
- Divergencias de lecturas en sombra.
- Duración y resultado de los backfills.

Configurar alarmas para errores, throttling sostenido, DLQ con mensajes,
replicación atrasada y ausencia inesperada de procesamiento. Los logs deben
incluir un identificador de correlación, nunca contraseñas, respuestas completas
de evaluación ni datos personales innecesarios.

## 11. Seguridad, respaldo y costos

### Seguridad

- Roles IAM separados para aplicación, migrador, consumidor y analítica.
- Políticas limitadas a la tabla, prefijos S3 y acciones requeridas.
- S3 con bloqueo de acceso público, cifrado y versionado.
- Tráfico hacia AWS mediante HTTPS; usar endpoints VPC si el presupuesto lo
  permite.
- Datos de analítica anonimizados o seudonimizados.
- CloudTrail habilitado para cambios administrativos.

### Respaldo y recuperación

- PITR de DynamoDB y respaldos bajo demanda antes de cada corte.
- Respaldo y prueba de restauración de PostgreSQL.
- Versionado y ciclo de vida en S3.
- Runbook para restaurar una tabla con un nombre alternativo y cambiar la
  configuración de la aplicación.

### Control de costos

- Etiquetar recursos con `project=kimun`, `environment` y `owner`.
- Crear AWS Budget y alarmas de costo antes de producción.
- Revisar mensualmente consumo de DynamoDB, almacenamiento, exportaciones y bytes
  escaneados por Athena.
- Particionar los datos de S3 por fecha y escribir Parquet comprimido para reducir
  el costo de Athena.
- Confirmar con AWS Pricing Calculator los supuestos de la propuesta antes del
  aprovisionamiento; los valores documentados son estimaciones, no un presupuesto
  garantizado.

## 12. Reversión

### Condiciones que activan reversión

- Diferencias en datos críticos.
- Errores o latencia por sobre el umbral acordado durante 15 minutos.
- Throttling sostenido.
- Acumulación de eventos que comprometa el objetivo de recuperación.
- Fallas funcionales en inscripción, progreso o rendición.

### Procedimiento

1. Detener el cambio del siguiente dominio.
2. Mantener los workers activos para vaciar eventos pendientes.
3. Cambiar la bandera de lectura del dominio afectado a `sql`.
4. Si DynamoDB ya era fuente de escritura, verificar que el espejo SQL esté al
   día; si no lo está, reproducir la cola antes de habilitar escrituras SQL.
5. Cambiar la fuente de escritura a SQL.
6. Conciliar los registros creados durante la ventana afectada.
7. Registrar el incidente y conservar los datos DynamoDB para diagnóstico.

La reversión no elimina recursos ni datos. Las tablas SQL solo podrán retirarse
mediante una decisión posterior y un respaldo verificado.

## 13. Responsables y aprobaciones

| Rol | Responsabilidad |
|---|---|
| Líder de migración | Secuencia, riesgos, criterios de avance y coordinación del corte |
| Backend | Repositorios, servicios, comandos, outbox y adaptación de vistas |
| Infraestructura | Terraform, Ansible, IAM, redes, respaldo y observabilidad |
| Datos/analítica | Conciliación, exportación, Glue y consultas Athena |
| QA | Casos funcionales, regresión, carga y evidencias |
| Responsable del producto | Validación de flujos y autorización de cada corte |

Cada fase requiere evidencia de pruebas y aprobación del líder de migración. Los
cambios de lectura o escritura en producción requieren además la aprobación del
responsable del producto.

## 14. Lista de entregables

- [ ] Inventario de patrones de acceso y línea base.
- [ ] Decisión registrada sobre región, ambientes y retención.
- [ ] Módulos Terraform y playbooks Ansible.
- [ ] Tabla DynamoDB, `GSI1`, Streams, SQS, DLQ y alarmas.
- [ ] Buckets S3, catálogo Glue, workgroup y consultas Athena.
- [ ] Repositorios SQL/DynamoDB y servicios por dominio.
- [ ] Outbox, consumidor y banderas de funcionalidad.
- [ ] Comandos de backfill y conciliación.
- [ ] Pruebas automatizadas, funcionales, seguridad y carga.
- [ ] Paneles, alarmas y runbooks de operación/reversión.
- [ ] Evidencias del corte y período de estabilización.
- [ ] Decisión formal sobre el retiro de tablas relacionales duplicadas.

## 15. Riesgos principales

| Riesgo | Mitigación |
|---|---|
| Consultas relacionales no identificadas | Inventario con búsqueda de ORM, pruebas de regresión y lecturas en sombra |
| Inconsistencia entre bases | Outbox, idempotencia, control de versión, conciliación y DLQ |
| Evaluación supera 400 KB | Umbral preventivo de 300 KB y partición por pregunta |
| Reportes causan escaneos costosos | Consultas por clave para operación y Athena para agregados |
| Partición caliente | Pruebas de carga, monitoreo y revisión de claves antes de producción |
| Pérdida de relación con calendario | Mantener metadatos relacionales de `Evaluacion` |
| Dependencia de AWS durante desarrollo | Repositorios desacoplados y DynamoDB Local/LocalStack |
| Costos no previstos | Modo On-Demand inicial, presupuestos, alarmas y revisión mensual |
| Reversión con SQL desactualizado | Espejo SQL, cola durable y ventana de estabilización de 14 días |

## 16. Primer incremento recomendado

El primer incremento implementable debe limitarse a `ClaseCompletado`:

1. Crear la infraestructura de `dev`.
2. Introducir `ProgressRepository` sin cambiar las vistas.
3. Agregar outbox y doble escritura.
4. Migrar el histórico de progreso.
5. Ejecutar conciliación y lecturas en sombra.
6. Cambiar solo la lectura de progreso a DynamoDB.
7. Probar reversión.

Este incremento valida la infraestructura, el modelo de claves, la replicación y
la operación con un dominio pequeño antes de intervenir intentos, evaluaciones e
inscripciones.
