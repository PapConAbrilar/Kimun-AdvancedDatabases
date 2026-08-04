# Propuesta del Proyecto: Plataforma Kimün (ONG ALUMCO)


### El Problema
La plataforma Kimün actual utiliza una arquitectura monolítica con una base de datos relacional única (SQLite/PostgreSQL). Con el crecimiento del número de colaboradores y residencias ELEAM a nivel nacional, la entrega de materiales multimedia, la corrección síncrona de evaluaciones y la generación de reportes masivos congestionan el rendimiento del sistema, generando cuellos de botella en la base de datos principal.

### La Solución
Migrar los módulos de mayor volumen y alta concurrencia de lectura/escritura (inscripciones, progreso de estudiantes, intentos de evaluaciones y auditoría) hacia una base de datos NoSQL DynamoDB bajo una estrategia de particionamiento.

Además, se automatiza todo el aprovisionamiento de infraestructura y despliegue usando Terraform y Ansible, garantizando un entorno repetible, seguro y de bajo mantenimiento para la ONG.

### 2. Diseño de Arquitectura y Estrategia NoSQL

[ Usuarios / Navegadores ]
                                 │
                                 ▼
                     [ ALB / Balanceador ]
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
[ Instancia Django (EC2) ]                      [ Instancia Django (EC2) ]
         │                                               │
         ├───────────────────────┬───────────────────────┤
         ▼                       ▼                       ▼
 [ Relacional / PostgreSQL ]  [ AWS DynamoDB ]    [ Amazon S3 ]
  (Usuarios, Roles, Cursos)  (Particionada:       (PDFs, Archivos,
                              Evaluaciones,        Logs de Auditoría)
                              Inscripciones)             │
                                                         ▼
                                                 [ AWS Athena ]
                                              (Examen: Big Data Analytics)


#### Estrategia NoSQL: Particionada (Sharding / Single-Table Design)
Usaremos DynamoDB aplicando particionamiento basado en la clave de partición (PK - Partition Key) y clave de ordenación (SK - Sort Key):

Tabla Principal (Kimun_Data):

PK (Partition Key): USER#<usuario_id> o COURSE#<curso_id>

SK (Sort Key): ATTEMPT#<evaluacion_id> o PROGRESS#<material_id>

Esta clave de partición distribuye automáticamente los datos a través de múltiples nodos físicos de almacenamiento, eliminando bloqueos de tablas ante accesos simultáneos durante evaluaciones masivas.

### 3. Infraestructura como Código (IaC): Terraform + Ansible
#### Role 1: Terraform (Aprovisionamiento de Infraestructura Cloud)
Declaración del estado deseado de los recursos en AWS:

Creación de la tabla DynamoDB en modo PAY_PER_REQUEST (On-Demand).

Creación del bucket S3 para almacenamiento de reportes y almacenamiento para Athena.

Configuración del Workgroup y Base de Datos de Amazon Athena.


#### Role 2: Ansible (Configuración de Servidor y App Django)
Automatiza la preparación del servidor de aplicaciones (EC2 / VM):

Instalación de dependencias del sistema (libcairo2, pango para WeasyPrint, Python 3.10+).

Clonación del repositorio Django, creación de entorno virtual e instalación de requirements.txt (incluyendo boto3 para conectar Django con DynamoDB).

Configuración de variables de entorno y puesta en marcha con Gunicorn/Nginx.

### 4. Estimación de Costos (AWS AWS Pricing Calculator - Estimación Mensual ONG)

| Servicio | Detalle de Uso | Costo Estimado (USD/Mes) |
|----------|----------------|--------------------------|
| AWS DynamoDB | On-Demand (2 millones de lecturas / 500k escrituras) | ~$2.50 |
| Amazon S3 | 20 GB de almacenamiento (PDFs, exportaciones CSV para Big Data) | ~$0.46 |
| AWS EC2 (Django App) | 1x t3.small (Servidor Web de la App Kimün) | ~$15.00 |
| Amazon Athena | Consumido por demanda de consultas SQL ($5.00 por TB escaneado) | ~$1.00 - $3.00 |
| **Total Estimado** | **Costo bajo y sostenible para la ONG** | **~$19.00 - $21.00 USD/mes** |


### Módulo de Big Data con Amazon Athena

Añadimos la arquitectura de análisis masivo sin servidor:

Flujo de Datos: Los eventos de interacciones de usuarios, logs de actividades en evaluaciones y archivos de auditoría generados por Kimün se exportan periódicamente a Amazon S3 en formato JSON/Parquet.

Athena Query Engine: Amazon Athena se conecta directamente al Bucket de S3 mediante AWS Glue Data Catalog.

Caso de Uso Big Data: Permite al equipo directivo de ALUMCO ejecutar consultas SQL analíticas sobre millones de registros históricos de progreso sin impactar la base de datos de producción (DynamoDB/Django).
