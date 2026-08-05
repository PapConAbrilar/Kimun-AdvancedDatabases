# Plan Maestro de Migración a DynamoDB (100% NoSQL)

## 1. Propósito y Contexto del Proyecto

Este documento detalla el plan ejecutable de migración de la plataforma Kimün. 
Cumpliendo estrictamente con los requerimientos del "Advanced Databases Workshop" (Certamen II y Examen):
1. **Erradicación Relacional:** El sistema migrará de forma absoluta (100%) a una arquitectura NoSQL (Amazon DynamoDB).
2. **Topología de Red:** Implementación de una arquitectura Cloud formal mediante VPC, subredes públicas y privadas.
3. **Resiliencia (Botar un Nodo):** Uso de **DynamoDB Global Tables** (Replicación Activo-Activo Multi-Región) para simular la caída de un nodo geográfico completo sin afectar el servicio.
4. **Big Data:** Exportación de logs históricos hacia Amazon S3 y consumo analítico mediante AWS Athena.

## 2. Estrategia Multicuenta (Equipo de 3 Personas)

Dado que el equipo opera bajo tres cuentas AWS Academy Learner Lab separadas ($50 USD de límite c/u y restricción severa de roles IAM), el riesgo se aislará de la siguiente manera:

- **Cuenta 1 (DevOps/IaC):** Destinada al ensayo y error de los scripts de Terraform. Si se agota el presupuesto por levantar múltiples recursos de red o Global Tables defectuosas, no afecta al equipo.
- **Cuenta 2 (SysAdmin/Configuración):** Destinada al despliegue de Ansible sobre las EC2 para automatizar la instalación de Nginx, Gunicorn y el código de Django.
- **Cuenta 3 (El Entorno "Golden"):** Cuenta inmaculada que solo ejecutará los scripts ya testeados (Terraform + Ansible) el día previo al ensayo general y el día de la presentación. Sus $50 USD aseguran el éxito de la demo.

## 3. Arquitectura Objetivo

```text
Usuarios / Profesor
   |
[ Internet Gateway ]
   |
   |-- VPC (Virtual Private Cloud)
       |
       |-- [ Subred Pública ]
       |     |-- Elastic IP
       |     |-- Instancia EC2 (t3.small) [Asignada con LabRole preexistente]
       |         |-- Nginx + Gunicorn + Django App
       |
       |-- [ Subred Privada ]
             |-- VPC Gateway Endpoint (Enruta tráfico interno hacia DynamoDB)
             |
             |---- [ AWS DynamoDB Global Table ] (Base de Datos Operativa)
             |        - Región Primaria (Ej. us-east-1) - "Nodo 1"
             |        - Región Secundaria (Ej. sa-east-1) - "Nodo 2"
             |
             |---- [ Amazon S3 ] (Almacenamiento Analítico)
                      |
                      +-- [ AWS Glue Crawler ] (Catálogo de Datos)
                      +-- [ AWS Athena ] (Motor SQL Serverless para Examen)
```

## 4. Diseño Físico de DynamoDB (Single-Table Design)

Todo el modelo de datos existirá en una única tabla para maximizar la eficiencia y reducir costos.

- **Nombre de Tabla:** `KimunData`
- **Modo de Facturación:** `PAY_PER_REQUEST`
- **Cifrado:** AWS Managed Key.
- **Índice Global (GSI1):** Necesario para búsquedas inversas (Ej. Alumnos por curso).

### Nomenclatura de Ítems
| Entidad | Partition Key (PK) | Sort Key (SK) | GSI1-PK | GSI1-SK |
|---|---|---|---|---|
| **Perfil/Auth** | `USER#<user_id>` | `PROFILE#<user_id>` | - | - |
| **Curso/Catálogo** | `COURSE#<curso_id>` | `METADATA#<curso_id>` | - | - |
| **Inscripción** | `USER#<user_id>` | `COURSE#<curso_id>` | `COURSE#<curso_id>` | `USER#<user_id>` |
| **Intento Eval** | `USER#<user_id>` | `ATTEMPT#<eval_id>#<timestamp>` | `EVAL#<eval_id>` | `USER#<user_id>#<timestamp>` |

## 5. Cambios Requeridos en Django

### 1. Capa de Repositorios
La aplicación dejará de usar el ORM de Django tradicional. Se creará un módulo `kimun/data_access/` que interactuará directamente con `boto3`.

### 2. Autenticación AWS (IAM Segura)
Prohibido usar Access Keys/Secret Keys en código. Django heredará mágicamente los permisos del **Instance Profile (`LabRole`)** que Terraform asigne a la máquina EC2.

### 3. Script de Failover Multi-Región (Para "Botar el Nodo")
El corazón de la presentación será la tolerancia a fallos. Django debe programarse para capturar caídas de la región principal:

```python
import boto3
from botocore.exceptions import ClientError

def get_dynamo_table():
    try:
        # Intenta conectar al "Nodo 1" (Región Principal)
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('KimunData')
        table.load() # Obliga a verificar existencia
        return table
    except ClientError:
        # Si la tabla no existe (Nodo botado), hace failover al "Nodo 2"
        dynamodb_replica = boto3.resource('dynamodb', region_name='sa-east-1')
        return dynamodb_replica.Table('KimunData')
```

## 6. Estrategia de Migración y Sembrado (Seed)

Dado que no se mantendrá una base relacional híbrida, el día de la presentación se realizará un **Sembrado Crudo** (Backfill simulado) para alimentar DynamoDB rápidamente.

1. Un script de Python (`python manage.py seed_dynamodb`) leerá un archivo JSON local con usuarios, cursos y notas falsas generadas previamente.
2. Inyectará estos datos masivamente a DynamoDB utilizando `BatchWriteItem`.
3. Inyectará una porción de datos históricos hacia S3 para alimentar a Athena.

## 7. Fases de Ejecución

| Fase | Tareas Principales | Salida / Entregable |
|---|---|---|
| **1. IaC (Terraform)** | Redactar `main.tf`. Levantar VPC, EC2, Endpoint, S3 y Global Tables. | Infraestructura efímera capaz de ser creada/destruida en 5 mins. |
| **2. Automatización (Ansible)** | Redactar playbooks para instalar Nginx, Gunicorn, clonar repo y configurar dependencias de Python en EC2. | Despliegue sin intervención humana (Cero clics SSH). |
| **3. Backend (Django)** | Programar repositorios NoSQL, script de Failover e inyección de datos. | App web funcionando 100% sobre DynamoDB (LocalStack). |
| **4. Integración Big Data** | Definir los 5 KPIs del negocio. Ejecutar AWS Glue sobre S3 y guardar consultas SQL en Athena. | Consultas preparadas para el Dashboard. |
| **5. Ensayo General** | Correr el pipeline completo (Terraform -> Ansible -> Seed) en la **Cuenta 3**. | Validación de tiempos de despliegue y consumo de USD. |

## 8. Pruebas y Observabilidad

- **Pruebas Locales:** Para no gastar capacidad AWS, el equipo desarrollará usando *DynamoDB Local* (Docker) o `moto` para mockear `boto3`.
- **CloudWatch:** Se configurarán paneles (Dashboard) en AWS para visualizar el consumo de `ConsumedReadCapacityUnits`, garantizando que la inyección de datos no sature la tabla ni genere costos excesivos.
- **Nginx Logs:** Disponibles en `/var/log/nginx/` vía Ansible para monitorear errores de la aplicación web.

## 9. FinOps y Seguridad (Restricciones Learner Lab)

1. **Permisos IAM:** Queda prohibido usar `aws_iam_role` en Terraform. Todos los permisos deben apuntar obligatoriamente al ARN del rol educacional provisto por AWS: `arn:aws:iam::<ACCOUNT_ID>:role/LabRole`.
2. **Cero Balanceadores:** No se usará Application Load Balancer (ALB) para evitar su costo fijo (~$16 USD). El tráfico web fluirá directo a la Elastic IP de la EC2.
3. **Cero Endpoints Costosos:** Solo se usará *Gateway Endpoint* para DynamoDB, el cual es gratuito, evitando los *Interface Endpoints* pagados.
4. **Terraform Destroy:** Al estar usando Global Tables, se cobran transferencias inter-región constantes. **Es obligatorio ejecutar `terraform destroy` inmediatamente finalizada la clase o prueba de integración.**

## 10. Guion de Demostración Final (Criterios de Éxito)

1. **Cero Clics Iniciales:** Ejecutar Terraform y Ansible frente al profesor, demostrando IaC y Configuration Management puro. Mostrar la web en línea.
2. **NoSQL en Vivo:** Hacer login y rendir una evaluación, demostrando que los datos caen en el `us-east-1` de DynamoDB.
3. **Botar el Nodo:** 
   - Abrir consola AWS y *borrar* intencionalmente la tabla en la Región Primaria.
   - Refrescar el LMS.
   - Demostrar que el script `try/except` redirigió el tráfico hacia la Región Secundaria en Sudamérica y los datos siguen ahí.
4. **Dashboard Big Data:** 
   - Ejecutar el Crawler de AWS Glue frente al profesor.
   - Mostrar el Dashboard de Athena consumiendo la data de S3 para responder a los 5 KPIs.
5. **Cierre FinOps:** Ejecutar `terraform destroy` para confirmar la naturaleza efímera y control de costos de la solución.
