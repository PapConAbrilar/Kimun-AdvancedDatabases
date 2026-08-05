# Plan de Implementación a DynamoDB (Versión Académica - 100% NoSQL)

## 1. Propósito y Contexto Universitario

Este documento detalla la migración **100% a NoSQL (Amazon DynamoDB)** de la plataforma Kimün. 
Cumpliendo estrictamente con los requisitos del "Advanced Databases Workshop":
1. Erradica cualquier uso de bases de datos relacionales o arquitecturas híbridas.
2. Implementa una topología formal de red (VPC, Subred Pública y Privada).
3. Resuelve el requerimiento de "botar un nodo para probar resiliencia" utilizando la característica avanzada de **DynamoDB Global Tables** (Replicación Multi-Región Activo-Activo).

## 2. Estrategia Multicuenta (El Equipo de 3 Personas)

Dado que cuentan con tres cuentas de AWS Learner Lab separadas ($50 USD c/u), aislarán el riesgo de la siguiente manera:
- **Cuenta 1 (DevOps):** Pruebas destructivas de los scripts de Terraform (Redes y DynamoDB).
- **Cuenta 2 (SysAdmin):** Pruebas de los playbooks de Ansible (Instalación de Nginx/Django en EC2).
- **Cuenta 3 (Entorno "Golden"):** Intacta hasta el ensayo general. Aquí correrán los scripts perfectos garantizando que los $50 de esta cuenta llegarán íntegros a la presentación final.

## 3. Alcance de la Migración: 100% NoSQL

Todo el modelo de datos existirá en **DynamoDB** bajo un patrón *Single-Table Design*:
- Autenticación, perfiles y roles.
- Catálogo de categorías, cursos y materiales.
- Progreso, evaluaciones e inscripciones de alumnos.
*(Se elimina por completo el uso de PostgreSQL o SQLite en producción).*

## 4. Arquitectura Objetivo y Topología VPC

```text
Usuarios / Profesor
   |
[ Internet Gateway ]
   |
   |-- VPC (Virtual Private Cloud)
       |
       |-- [ Subred Pública ]
       |     |-- Elastic IP
       |     |-- Instancia EC2 (t3.small) [Rol: LabRole]
       |         |-- Nginx + Gunicorn + Django
       |
       |-- [ Subred Privada ]
             |-- VPC Gateway Endpoint (Enruta tráfico interno hacia DynamoDB)
             |
             |---- [ AWS DynamoDB Global Table ] (On-Demand)
             |        - Región Primaria (ej. us-east-1)
             |        - Región Secundaria (ej. sa-east-1)
             |
             |---- [ Amazon S3 ] (Exportaciones Históricas)
                      |
                      +-- [ AWS Glue Crawler ] (Ejecutado On-Demand)
                      +-- [ AWS Athena ] (Consultas SQL para Big Data)
```

## 5. Diseño Físico de DynamoDB (Single-Table Design)

- **Nombre de Tabla:** `KimunData-Demo`
- **Modo de Facturación:** `PAY_PER_REQUEST`
- **Resiliencia:** Configurada como *Global Table* replicando hacia una segunda región.

### Estructura de Llaves
| Entidad | Partition Key (PK) | Sort Key (SK) | GSI1-PK | GSI1-SK |
|---|---|---|---|---|
| **Perfil/Auth** | `USER#<id>` | `PROFILE#<id>` | - | - |
| **Curso** | `COURSE#<id>` | `METADATA#<id>` | - | - |
| **Inscripción** | `USER#<id>` | `COURSE#<id>` | `COURSE#<id>` | `USER#<id>` |
| **Intento Eval** | `USER#<id>` | `ATTEMPT#<eval_id>#<fecha>` | `EVAL#<eval_id>` | `USER#<id>#<fecha>` |

## 6. Cambios Requeridos en Django (Failover Multi-Región)

El backend debe programarse para soportar la caída de una región. En las vistas de Django, el cliente de `boto3` debe envolverse en un bloque `try/except`:

```python
import boto3
from botocore.exceptions import ClientError

def get_dynamo_table():
    try:
        # Intenta conectar al "Nodo 1" (Región Principal)
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('KimunData-Demo')
        table.load() # Verifica si existe
        return table
    except ClientError:
        # Si falla (el nodo fue botado), hace failover automático al "Nodo 2"
        dynamodb_replica = boto3.resource('dynamodb', region_name='sa-east-1')
        return dynamodb_replica.Table('KimunData-Demo')
```

## 7. Fases de Ejecución

| Fase | Integrante Recomendado | Tareas Principales |
|---|---|---|
| **1. Infraestructura Cloud** | DevOps (Integrante 1) | Crear `main.tf` para levantar VPC, Subredes, EC2, S3, Athena y las **Global Tables de DynamoDB**. |
| **2. Config. de Servidores** | SysAdmin (Integrante 2) | Escribir playbooks de Ansible para EC2 (Instalar Nginx, clonar repo). *No se instala ninguna base de datos local*. |
| **3. Adaptación Django** | Backend (Integrante 3) | Instalar `boto3`. Refactorizar 100% de los modelos de Django a NoSQL. Programar el script de Failover (Arriba). |
| **4. Integración y Ensayo** | Los 3 integrantes | Correr todo en la **Cuenta 3**. Sembrar datos de prueba directamente a DynamoDB. |
| **5. Presentación** | Los 3 integrantes | `terraform apply`, demostración de failover, flujo Big Data (S3->Athena), y finalmente `terraform destroy`. |

## 8. Guion para la Demostración en Vivo

### Parte 1: Funcionamiento Normal (100% NoSQL)
- El profesor ingresa a la IP de la instancia EC2.
- Se demuestra el registro de un usuario, inscripción a curso y rendición de evaluación, todo persistiendo en la tabla principal de DynamoDB (`us-east-1`).

### Parte 2: Prueba de Resiliencia (Botar el Nodo)
1. **Explicación:** Se le explica al profesor que DynamoDB no expone servidores físicos, por lo que la arquitectura distribuida se llevó al extremo de usar *Regiones como Nodos* (Activo-Activo).
2. **Acción Destructiva:** Frente al profesor, abren la consola de AWS y **eliminan la tabla `KimunData-Demo` de la región principal (us-east-1)**.
3. **Comprobación:** Refrescan la aplicación web de Kimün. Gracias al script de Failover en Django, la aplicación sigue funcionando instantáneamente, leyendo ahora desde el "Nodo 2" (la réplica en `sa-east-1`) sin pérdida de datos.

### Parte 3: Integración Big Data
1. Exportar en vivo la tabla desde DynamoDB hacia el bucket S3 (formato JSON).
2. Ejecutar el Crawler de AWS Glue.
3. Abrir AWS Athena y ejecutar la consulta SQL que alimenta los 5 KPIs del negocio.

## 9. FinOps (Control de Costos para el Learner Lab)

- **Sin ALB ni RDS:** Al usar una sola EC2 en subred pública (Elastic IP) y base de datos Serverless, el costo por hora es mínimo (~$0.02 USD).
- **Costo de Global Tables:** Replicar datos entre regiones tiene un costo de transferencia. **Por esto es obligatorio ejecutar `terraform destroy` apenas termine la clase**, evitando que los $50 USD se agoten.
- **Roles IAM:** Solo se usará el `LabRole` preexistente para evitar bloqueos de permisos.
