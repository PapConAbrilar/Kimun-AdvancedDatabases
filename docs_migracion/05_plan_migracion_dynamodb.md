# Plan de Implementación de la Migración a DynamoDB (100% NoSQL)

## 1. Propósito

Este documento transforma la propuesta de migración de la plataforma Kimün en un plan ejecutable, incremental y detallado. A diferencia de enfoques híbridos, esta solución **erradica por completo el uso de bases de datos relacionales**, cumpliendo estrictamente con los requerimientos del "Advanced Databases Workshop":

- **Amazon DynamoDB** asume el 100% de la persistencia (identidad, catálogo y operación) bajo un patrón *Single-Table Design*.
- **DynamoDB Global Tables** proporciona replicación Activo-Activo Multi-Región para resolver el requerimiento de resiliencia ("botar un nodo") en un entorno Serverless.
- **Topología de Red VPC** aísla la base de datos utilizando subredes públicas para los servidores de aplicación y endpoints privados para los datos.
- **Amazon S3, AWS Glue y Amazon Athena** reciben el histórico analítico para reportes agregados y KPIs de negocio sin cargar la base operacional.
- **Terraform** aprovisiona la infraestructura y **Ansible** configura las instancias EC2 (Nginx, Gunicorn, Django).

## 2. Objetivos y Criterios Globales de Éxito

### Objetivos

1. Migrar absolutamente todas las lecturas y escrituras (Identity, Catalog, Operations) hacia DynamoDB.
2. Sustituir los `JOIN` relacionales por patrones de acceso explícitos (Single-Table) e Índices Secundarios Globales (GSI).
3. Demostrar resiliencia arquitectónica simulando la caída de una región geográfica entera sin interrupción del servicio.
4. Derivar los reportes globales y KPIs de negocio hacia S3 y Athena.
5. Operar dentro del límite presupuestario estricto ($50 USD) de las cuentas AWS Academy Learner Lab.

### Criterios de Aceptación

- 100% de los registros relacionales heredados están migrados a DynamoDB y conciliados.
- El modelo de datos es capaz de renderizar el Perfil, los Cursos del usuario y sus Evaluaciones en **una sola consulta a la base de datos**.
- La aplicación sobrevive (Failover automático en menos de 2 segundos) a la eliminación manual de la tabla principal en la región primaria de AWS.
- El despliegue de infraestructura y configuración ocurre mediante comandos de IaC (Terraform y Ansible) sin requerir clics manuales en la consola de AWS (Zero-Click Deployment).
- Los KPIs analíticos se resuelven mediante consultas SQL en Athena con latencia menor a 10 segundos.

## 3. Alcance (100% NoSQL)

Se migrarán todos los dominios de la aplicación desde el motor relacional heredado (SQLite/PostgreSQL) hacia DynamoDB.

| Dominio | Origen Relacional | Destino (DynamoDB Single-Table) |
|---|---|---|
| Identidad y Auth | `Usuario`, `Roles` | Ítem `PROFILE#` con `password_hash` y metadatos. |
| Catálogo | `Categoria`, `Curso`, `Material` | Ítem `METADATA#` para configuración de cursos. |
| Inscripciones | `InscripcionCurso` | Ítem de relación `COURSE#` bajo la partición del usuario. |
| Evaluaciones | `Evaluacion`, `Pregunta`, `Alternativa` | Documento desnormalizado (preguntas embebidas) en `EVAL#`. |
| Progreso | `ClaseCompletada` | Ítem de seguimiento `PROGRESS#`. |
| Intentos | `IntentoEvaluacion` | Ítem transaccional `ATTEMPT#` con respuestas exactas. |

## 4. Arquitectura Objetivo y Topología de Red

El despliegue se realizará sobre una Virtual Private Cloud (VPC) para aislar las cargas de trabajo:

```text
Usuarios / Profesor
   |
[ Internet Gateway ]
   |
   |-- VPC (10.0.0.0/16)
       |
       |-- [ Subred Pública ] (10.0.1.0/24)
       |     |-- Elastic IP
       |     |-- Instancia EC2 (t3.small) [Rol: LabRole]
       |         |-- Nginx (Reverse Proxy) + Gunicorn + Django App
       |
       |-- [ Subred Privada ] (10.0.2.0/24)
             |-- VPC Gateway Endpoint (Enruta tráfico interno hacia DynamoDB)
             |
             |---- [ AWS DynamoDB Global Table ] (Base de Datos Operativa)
             |        - Región Primaria (us-east-1) - "Nodo 1"
             |        - Región Secundaria (sa-east-1) - "Nodo 2"
             |
             |---- [ Amazon S3 ] (Almacenamiento Analítico Histórico)
                      |
                      +-- [ AWS Glue Crawler ] (Catálogo de Datos Parquet/JSON)
                      +-- [ AWS Athena ] (Motor SQL Serverless para Examen)
```

## 5. Diseño Físico de DynamoDB (Single-Table Design)

### Tabla y Capacidad

- Nombre de la tabla: `KimunData-Demo`
- Clave primaria compuesta: `PK` y `SK`, ambas de tipo `String`.
- Capacidad inicial: `PAY_PER_REQUEST` (Evita cobros fijos por hora).
- Replicación: Habilitada hacia una segunda región (Global Tables).
- Cifrado en reposo: Habilitado con AWS Managed Key (por compatibilidad de permisos IAM en Learner Labs).

### Nomenclatura de Ítems

| Tipo de Ítem | `PK` (Partition Key) | `SK` (Sort Key) | Atributos relevantes (JSON) |
|---|---|---|---|
| **Perfil/Auth** | `USER#<usuario_id>` | `PROFILE#<usuario_id>` | `password_hash`, `email`, `role`, `is_active`, `schema_version` |
| **Curso** | `COURSE#<curso_id>` | `METADATA#<curso_id>` | `title`, `description`, `category_id`, `is_published` |
| **Material** | `COURSE#<curso_id>` | `MATERIAL#<material_id>` | `type`, `url`, `order`, `duration_minutes` |
| **Inscripción** | `USER#<usuario_id>` | `COURSE#<curso_id>` | `status`, `assigned_at`, `GSI1PK`, `GSI1SK` |
| **Evaluación** | `COURSE#<curso_id>` | `EVAL#<evaluacion_id>` | `title`, `[array_de_preguntas_y_alternativas]`, `max_attempts` |
| **Intento** | `USER#<usuario_id>` | `ATTEMPT#<eval_id>#<timestamp>` | `score`, `passed`, `answers`, `GSI1PK`, `GSI1SK` |

### Índice Invertido `GSI1`

Como DynamoDB no permite escanear la base de datos de manera eficiente para consultas inversas, se configurará un Índice Secundario Global (GSI).

| Consulta Resuelta | `GSI1PK` (Llave de Partición GSI) | `GSI1SK` (Llave de Ordenación GSI) |
|---|---|---|
| Alumnos inscritos en un Curso específico | `COURSE#<curso_id>` | `USER#<usuario_id>` |
| Intentos históricos por Evaluación | `EVAL#<evaluacion_id>` | `USER#<usuario_id>#<timestamp>` |

## 6. Cambios Requeridos en Django

### 1. Reemplazo del ORM (Capa de Acceso)

Se creará el paquete `kimun/data_access/` que abstraerá las consultas directas a DynamoDB. El ORM de Django (e.g., `Model.objects.filter()`) quedará obsoleto. Las vistas utilizarán servicios de dominio.

### 2. Autenticación IAM Segura (`LabRole`)

Queda estrictamente prohibido utilizar credenciales `AWS_ACCESS_KEY_ID` quemadas en código o en variables de entorno `.env`. Django, a través de la librería `boto3`, obtendrá automáticamente credenciales temporales utilizando el `Instance Profile` de la máquina EC2 asociado al rol educacional `LabRole`.

### 3. Failover Automático Multi-Región (Prueba de Resiliencia)

Para cumplir la rúbrica de "Botar un Nodo", la capa de datos de Django debe capturar excepciones de conexión (`ClientError` o `ResourceNotFoundException`) e instantáneamente pivotar hacia la región de contingencia:

```python
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

def get_dynamo_table():
    try:
        # Intento de conexión al "Nodo 1" (Región Primaria)
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('KimunData-Demo')
        table.load() # Obliga a verificar existencia física de la tabla
        return table
    except ClientError as e:
        logger.warning(f"Falla en Nodo Primario (us-east-1). Ejecutando Failover. Detalles: {e}")
        # Conexión de contingencia al "Nodo 2" (Región Secundaria)
        dynamodb_replica = boto3.resource('dynamodb', region_name='sa-east-1')
        return dynamodb_replica.Table('KimunData-Demo')
```

## 7. Estrategia de Migración de Datos (Backfill)

Como la base de datos relacional será destruida, el sistema requiere un proceso robusto para inyectar datos de prueba funcionales el día de la presentación.

Se implementará el comando de Django:
```text
python manage.py seed_dynamodb --batch-size 100 --dry-run
```

El comando deberá:
1. Leer un archivo `seed_data.json` o utilizar factorías (Faker) para generar 100 usuarios, 5 cursos y 1000 intentos falsos.
2. Formatear los registros bajo la estructura Single-Table.
3. Utilizar `BatchWriteItem` de `boto3` para inyectar bloques de 25 registros simultáneos.
4. Identificar `UnprocessedItems` para reintentos exponenciales.
5. Inyectar un subset de estos datos crudos en formato JSON Lines al bucket de S3 para análisis de Athena.

## 8. Fases de Ejecución y Estrategia Multicuenta

Dado que el equipo opera bajo tres cuentas AWS Learner Lab separadas ($50 USD c/u), el riesgo se distribuye de la siguiente manera:

- **Cuenta 1 (DevOps):** Pruebas destructivas de los scripts de Terraform (VPC, Redes, Endpoints, Global Tables).
- **Cuenta 2 (SysAdmin):** Pruebas de los playbooks de Ansible (Instalación de Nginx, Gunicorn y dependencias de Django en EC2).
- **Cuenta 3 (Entorno "Golden"):** Cuenta inmaculada. Solo se usarán los $50 USD el día del ensayo general y el día de la presentación oficial.

### Secuencia de Implementación

| Fase | Duración | Actividades Principales | Entregable |
|---|---:|---|---|
| 1. Modelado Data | 2 días | Diseñar mapeo de entidades de SQLite al Single-Table Design. | Documento de diseño validado. |
| 2. Infraestructura | 3 días | Crear `main.tf`. Levantar VPC, Subredes, EC2 (LabRole), Endpoint S3/Dynamo, y Global Tables. | Red funcional y segura en Cuenta 1. |
| 3. Configuración | 3 días | Playbooks Ansible para aprovisionar EC2 sin intervención manual. | EC2 ejecutando Nginx en Cuenta 2. |
| 4. Backend Django | 5 días | Refactor de repositorios NoSQL, inyección `boto3`, y failover. | App web funcional localmente usando LocalStack. |
| 5. Integración Analítica | 2 días | Configurar crawler de Glue y diseñar 5 consultas SQL para Athena. | Dashboard SQL funcional. |
| 6. Ensayo General | 1 día | `terraform apply` -> `ansible-playbook` -> Demostración -> `terraform destroy`. | Cronómetro de tiempos de despliegue y validación de costos. |

## 9. Pruebas y Observabilidad

### Automatizadas y Locales
- Para el desarrollo local sin generar costos en AWS, el backend se desarrollará utilizando el contenedor Docker `amazon/dynamodb-local`.
- Pruebas unitarias evaluarán la correcta generación de claves compuestas (`PK`, `SK`).
- Pruebas de carga evaluarán el comportamiento del script de Failover Multi-Región utilizando la librería `moto` para mockear interrupciones de red.

### Monitoreo en AWS (CloudWatch)
Crear un panel de métricas con:
- `ConsumedReadCapacityUnits` y `ConsumedWriteCapacityUnits` para vigilar que el comando de Backfill no agote el presupuesto.
- Alertas por sobreconsumo en la región primaria y secundaria.

### Nginx Logs
- Ansible configurará la recolección de logs de Gunicorn y Nginx (`/var/log/nginx/error.log`) para depuración rápida de la capa web.

## 10. Seguridad, Permisos y FinOps

### Restricciones Críticas IAM (Learner Lab)
- Está **estrictamente prohibido** el uso del recurso `aws_iam_role` en Terraform.
- Todo servicio (EC2, Glue) debe heredar el ARN del rol educacional preexistente: `arn:aws:iam::<ACCOUNT_ID>:role/LabRole`.

### FinOps (Control de Costos - $50 Límite)
- **Cero Balanceadores:** Se prescindirá del Application Load Balancer (ALB) para ahorrar el costo base de ~$16 USD/mes. El tráfico fluirá directamente a la Elastic IP.
- **Costos de Global Tables:** La replicación de DynamoDB cobra por transferencia inter-región (WRU/RRU). 
- **Destrucción Obligatoria:** Es **mandatorio** ejecutar `terraform destroy` inmediatamente después de cada prueba de integración o ensayo. Bajo ninguna circunstancia la infraestructura debe quedar encendida de un día para otro.

## 11. Guion de Demostración Final (Criterios de Evaluación)

Este es el flujo exacto que el equipo presentará al profesor para garantizar la calificación máxima:

### Parte 1: IaC y Despliegue (Cero Clics)
1. El equipo abre la terminal y ejecuta `terraform apply -auto-approve`. Se explica la topología VPC y cómo se levantan las Global Tables.
2. Se ejecuta `ansible-playbook playbook.yml`. Se explica que la EC2 se configura automáticamente.
3. Se abre el navegador en la IP pública y Kimün está operativo.

### Parte 2: Funcionamiento Operacional (100% NoSQL)
1. Se registra un usuario, se inscribe en un curso y rinde una evaluación en vivo.
2. Se abre la consola de AWS DynamoDB (`us-east-1`) y se muestra al profesor cómo el registro fue insertado eficientemente mediante *Single-Table Design*.

### Parte 3: Prueba de Resiliencia ("Botar el Nodo")
1. **Contexto:** Se explica al profesor que como DynamoDB es *Serverless*, el concepto de "Nodos" se elevó al nivel de "Regiones" (Activo-Activo).
2. **Caos:** En vivo, desde la consola de AWS, el equipo selecciona la tabla `KimunData-Demo` en la región principal y presiona **Eliminar Tabla**.
3. **Validación:** Se refresca la plataforma web de Kimün. Gracias al script `try/except` de Django, el sistema responde instantáneamente extrayendo los datos desde el "Nodo 2" (Región Secundaria en Sudamérica), logrando una demostración impecable de resiliencia ante desastres.

### Parte 4: Big Data Analytics
1. Se ejecuta el Crawler de AWS Glue sobre el bucket S3 (donde se exportaron logs de intentos en JSON).
2. Se abre Amazon Athena.
3. Se ejecutan las consultas SQL analíticas sobre el data lake sin cargar la base de datos operacional.
4. Se presentan los 5 KPIs de negocio resultantes.

### Parte 5: Cierre
1. El equipo ejecuta `terraform destroy` para confirmar la naturaleza efímera del proyecto y control de costos FinOps.
