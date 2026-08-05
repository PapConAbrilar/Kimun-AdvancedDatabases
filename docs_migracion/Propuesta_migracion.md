# Propuesta del Proyecto: Plataforma Kimün (ONG ALUMCO)


### El Problema
La plataforma Kimün actual utiliza una arquitectura monolítica con una base de datos relacional única (SQLite/PostgreSQL). Con el crecimiento del número de colaboradores y residencias ELEAM a nivel nacional, la entrega de materiales multimedia, la corrección síncrona de evaluaciones y la generación de reportes masivos congestionan el rendimiento del sistema, generando cuellos de botella en la base de datos principal.

### La Solución
Migrar el **100% de la plataforma** hacia una base de datos NoSQL DynamoDB bajo una estrategia de particionamiento con **Tablas Globales (Multi-Región)**. Esto asegura una altísima disponibilidad y resiliencia ante desastres geográficos.

Además, se automatiza todo el aprovisionamiento de infraestructura de red y servidores usando Terraform y Ansible, garantizando un entorno repetible, seguro y de bajo mantenimiento para la ONG.

### 2. Diseño de Arquitectura y Estrategia NoSQL

```text
[ Usuarios / Navegadores ]
             │
             ▼
      [ Internet Gateway ]
             │
             ▼
[ VPC - Subred Pública ]
    [ Elastic IP ]
             │
             ▼
[ Instancia Django (EC2) ]
             │
             ├─────────────────────────────────────────────────┐
             ▼                                                 ▼
[ VPC Gateway Endpoint ] (Subred Privada)               [ Amazon S3 ]
             │                                        (Exportaciones Históricas)
             ▼                                                 │
[ AWS DynamoDB Global Tables ]                                 ▼
   (100% NoSQL: Usuarios,                                [ AWS Glue Crawler ]
    Cursos, Evaluaciones)                                      │
             │                                                 ▼
             ├─ Nodo 1 (Región: us-east-1)               [ AWS Athena ]
             └─ Nodo 2 (Región: sa-east-1)         (Examen: Big Data Analytics)
```

#### Estrategia NoSQL: Particionada y Replicada (Global Tables)
Usaremos DynamoDB aplicando particionamiento basado en la clave de partición (PK) y ordenación (SK) bajo un diseño **Single-Table**:

- PK (Partition Key): `USER#<usuario_id>` o `COURSE#<curso_id>`
- SK (Sort Key): `PROFILE#`, `ATTEMPT#<evaluacion_id>` o `PROGRESS#<material_id>`

**Resiliencia (Botar un Nodo):** La arquitectura despliega la tabla en dos regiones distintas. El backend de Django intentará conectarse a la Región 1. Para probar la resiliencia, **se eliminará la tabla en la Región 1 en vivo**. El sistema detectará la caída y redirigirá el tráfico automáticamente a la Región 2, manteniendo Kimün 100% operativo sin pérdida de datos.

### 3. Infraestructura como Código (IaC): Terraform + Ansible
#### Role 1: Terraform (Aprovisionamiento de Infraestructura Cloud)
Declaración del estado deseado de los recursos en AWS:

- Creación de VPC, Subred Pública, Gateway Endpoint e Internet Gateway.
- Creación de la instancia EC2 con `LabRole`.
- Creación de DynamoDB Global Tables en modo PAY_PER_REQUEST.
- Creación del bucket S3, catálogo Glue y base de datos de Amazon Athena.

#### Role 2: Ansible (Configuración de Servidor y App Django)
Automatiza la preparación del servidor web (EC2):

- Instalación de dependencias del sistema.
- Clonación del repositorio Django, creación de entorno virtual e instalación de requirements (incluyendo `boto3`).
- Configuración del script de Failover Multi-Región en Django y puesta en marcha con Gunicorn/Nginx.

### 4. Estimación de Costos (AWS Learner Lab - Entorno Efímero)

| Servicio | Detalle de Uso | Costo Estimado (Demostración) |
|----------|----------------|--------------------------|
| AWS DynamoDB | On-Demand (Global Tables y Transferencia inter-región) | ~$0.50 |
| Amazon S3 | 1 GB de almacenamiento de logs para Big Data | ~$0.02 |
| AWS EC2 | 1x t3.small (Servidor Web) | ~$0.02 por hora |
| Amazon Athena | Consumido por demanda de consultas SQL | ~$0.00 |
| **Total Estimado** | **100% compatible con presupuesto Learner Lab** | **Menos de $1.00 USD por día de uso** |


### Módulo de Big Data con Amazon Athena

Añadimos la arquitectura de análisis masivo sin servidor:

- Flujo de Datos: Los datos operacionales de DynamoDB se exportan a Amazon S3 en formato JSON/Parquet.
- Athena Query Engine: Amazon Athena se conecta directamente al Bucket de S3 mediante AWS Glue Data Catalog.
- Caso de Uso Big Data: Permite al equipo directivo de ALUMCO ejecutar consultas SQL analíticas (5 KPIs) sobre millones de registros históricos de progreso sin impactar la base de datos operativa.
