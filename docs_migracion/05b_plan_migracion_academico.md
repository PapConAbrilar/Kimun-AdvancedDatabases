# Plan de Implementación a DynamoDB (Versión Académica Detallada)

## 1. Propósito y Contexto Universitario

Este documento transforma la propuesta de migración de la plataforma Kimün en un plan ejecutable altamente detallado, diseñado específicamente para cumplir con las restricciones de un entorno AWS Academy Learner Lab (cuentas con límite de $50 USD y restricciones severas de creación de roles IAM).

La solución conserva la arquitectura híbrida (PostgreSQL + DynamoDB), pero optimiza la topología de red y los servicios de cómputo para garantizar que la presentación académica sea un éxito sin agotar el presupuesto ni enfrentar bloqueos de permisos.

## 2. Estrategia Multicuenta (El Equipo de 3 Personas)

Dado que el equipo cuenta con **tres cuentas de AWS Learner Lab separadas** (cada una con $50, sumando un presupuesto global teórico de $150), la estrategia no será interconectar las cuentas (lo cual está bloqueado por permisos de red en Learner Labs), sino utilizarlas para **aislar las fases del proyecto**:

- **Cuenta 1 (Entorno de Desarrollo y Pruebas IaC):** Se utilizará para probar los scripts de Terraform, levantar las instancias EC2 docenas de veces, equivocarse y borrar todo. Si el presupuesto se gasta aquí, no afecta el resultado final.
- **Cuenta 2 (Entorno de Pruebas de Configuración/Ansible):** Se utilizará para probar que los Playbooks de Ansible logren instalar correctamente Nginx, Gunicorn y PostgreSQL dentro del EC2 y que Django logre conectarse a DynamoDB.
- **Cuenta 3 (El Entorno "Golden" de Presentación):** Se mantendrá intacta y limpia. Solo se usará el día antes de la presentación para correr los scripts ya validados (Terraform + Ansible). Esto garantiza que para el día crítico, los $50 de esta cuenta estarán íntegros.

## 3. Alcance de la Migración

La estrategia de datos será híbrida (*Polyglot Persistence*):

### Datos en PostgreSQL (Servidor Local en EC2)
- **Identidad:** `Usuario`, roles y permisos.
- **Catálogo:** `Categoria`, `Curso`, `Clase`, `Material`.
- **Por qué:** Son datos altamente relacionales, estáticos y que requieren el Django Admin clásico.

### Datos migrados a DynamoDB
- **Operacional Masivo:** `InscripcionCurso`, progreso de clases, `IntentoEvaluacion`.
- **Por qué:** Son los módulos que generan cuellos de botella en lectura/escritura bajo concurrencia masiva (ej. todos los voluntarios dando pruebas al mismo tiempo).

## 4. Arquitectura Objetivo (Optimizada para Costos)

```text
Usuarios / Profesor
   |
[ Elastic IP Pública ] (Sustituye al ALB para ahorrar $16/mes)
   |
[ Instancia EC2 (t3.small) - Rol: LabRole ]
   |
   |---- Nginx + Gunicorn (Servidor Web)
   |---- PostgreSQL (Base de datos local instalada vía Ansible)
   |---- Django App
           |
           |---- [ AWS DynamoDB ] (On-Demand)
           |        (Partición: Inscripciones, Intentos)
           |
           |---- [ Amazon S3 ] (Exportaciones Históricas)
                    |
                    +-- [ AWS Glue Crawler ] (Ejecutado On-Demand)
                    +-- [ AWS Athena ] (Consultas SQL para Big Data)
```

## 5. Diseño Físico de DynamoDB (Single-Table Design)

### Tabla y Capacidad
- **Nombre:** `KimunData-Demo`
- **Modo:** `PAY_PER_REQUEST` (Evita costos fijos por hora).
- **Cifrado:** AWS Managed Key (por defecto, no requiere llaves KMS personalizadas que podrían estar bloqueadas).

### Estructura de Llaves
| Entidad | Partition Key (PK) | Sort Key (SK) | GSI1-PK | GSI1-SK |
|---|---|---|---|---|
| **Inscripción** | `USER#<user_id>` | `COURSE#<curso_id>` | `COURSE#<curso_id>` | `USER#<user_id>` |
| **Intento Eval** | `USER#<user_id>` | `ATTEMPT#<eval_id>#<fecha>` | `EVAL#<eval_id>` | `USER#<user_id>#<fecha>` |

*El GSI1 (Índice Secundario Global Invertido) permite consultar qué usuarios rindieron una prueba o están inscritos en un curso sin escanear toda la tabla.*

## 6. Cambios Requeridos en Django

### 1. Capa de Repositorios (Data Access)
Se creará un módulo `kimun/data_access/` que abstraerá las consultas. En lugar de hacer `IntentoEvaluacion.objects.create(...)`, se usará `AttemptRepository.save_attempt(...)`. Esto permite que Django decida por configuración si escribir en SQLite (desarrollo local) o en DynamoDB (producción AWS).

### 2. Autenticación AWS (Uso de `LabRole`)
En un entorno AWS normal, se crean usuarios IAM con llaves (Access Keys). En Learner Lab, Django debe usar `boto3` obteniendo automáticamente las credenciales del **Instance Profile (`LabRole`)** asignado a la máquina EC2 por Terraform. No se deben quemar contraseñas en el código.

## 7. Estrategia de Migración y Demostración en Vivo

Para la presentación, se ejecutará una migración "en caliente" (Backfill) simulada:

1. **Sembrado (Seed):** Un comando `python manage.py seed_data` creará 500 usuarios, 20 cursos y 1000 intentos falsos en PostgreSQL.
2. **Corte a DynamoDB:** Se ejecutará `python manage.py migrate_to_dynamodb`.
   - El script leerá en lotes (batch) desde PostgreSQL.
   - Usará `BatchWriteItem` para inyectar bloques de 25 registros en DynamoDB.
   - Mostrará una barra de progreso en la terminal.
3. **Exportación Big Data:** Se correrá un script que vuelque un resumen de los intentos desde PostgreSQL a un archivo JSON en Amazon S3, listo para ser consumido por Athena.

## 8. Fases de Ejecución (Repartidas entre 3 integrantes)

| Fase | Integrante Recomendado | Tareas Principales |
|---|---|---|
| **1. Infraestructura Cloud** | DevOps (Integrante 1) | Crear `main.tf` de Terraform. Levantar EC2 (asignando `LabRole`), DynamoDB, S3 y Athena. Trabaja en **Cuenta 1**. |
| **2. Config. de Servidores** | SysAdmin (Integrante 2) | Escribir los playbooks de Ansible. Conectarse vía SSH a la EC2 e instalar Nginx, PostgreSQL, Python, clonar repo. Trabaja en **Cuenta 2**. |
| **3. Adaptación Django** | Backend (Integrante 3) | Instalar `boto3`. Programar los repositorios, cambiar las vistas (`views.py`) para que escriban en DynamoDB. Programar los scripts de migración. Trabaja en local. |
| **4. Integración y Ensayo** | Los 3 integrantes | Correr todo el proceso en la **Cuenta 3** limpia. Medir tiempos de despliegue. |
| **5. Presentación** | Los 3 integrantes | `terraform apply`, demostración web funcional, migración a S3, consultas de Athena, y finalmente `terraform destroy`. |

## 9. Pruebas y Observabilidad

### Pruebas Locales (Evitar gastar de más)
El Integrante 3 no necesita AWS para programar. Debe utilizar **DynamoDB Local** (descargable como contenedor Docker) o usar la base de datos temporal en memoria (mock) mediante la librería `moto` para Python, garantizando que el código funciona antes de subirlo a AWS.

### Observabilidad Básica
- CloudWatch: Monitorear que los "ConsumedReadCapacityUnits" no se disparen durante el comando de migración masiva.
- Nginx Logs: Serán vitales para depurar si Ansible falló al levantar Gunicorn (`/var/log/nginx/error.log`).

## 10. Seguridad, Permisos y FinOps

### Restricción Crítica: IAM
Está estrictamente prohibido incluir recursos como `aws_iam_role` en Terraform. Todo recurso que exija un rol debe apuntar al ARN preexistente del `LabRole` entregado por AWS Academy: `arn:aws:iam::<ACCOUNT_ID>:role/LabRole`.

### FinOps (Control de Costos)
- **Bloqueo del ALB:** Evitado, ahorro de ~$16 USD.
- **RDS Administrado:** Evitado (usando PostgreSQL en el mismo EC2), ahorro de ~$15 USD.
- **VPC Endpoints:** Evitados, ahorro de ~$7 USD.
- **DPU de AWS Glue:** El Crawler se ejecutará solo bajo demanda manual. **NUNCA** dejar encendido un Crawler o un job en Glue.
- **Terraform Destroy:** Mandatorio después de cada prueba.

## 11. Criterios de Éxito de la Presentación

1. **Despliegue Cero Clicks:** Que `terraform apply` + `ansible-playbook` levanten el LMS completo sin tener que abrir la consola de AWS.
2. **Hibridación Comprobada:** Crear un usuario nuevo (y comprobar que quedó en PostgreSQL) e inscribirlo a un curso (y comprobar en la consola web de AWS que el registro cayó en DynamoDB).
3. **Analítica Directa:** Ejecutar exitosamente un comando SQL complejo en AWS Athena demostrando la extracción de valor sobre los logs guardados en S3.
