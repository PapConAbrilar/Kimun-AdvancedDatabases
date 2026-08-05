# Plan de Migración a DynamoDB (Versión Académica / AWS Learner Lab)

## 1. Propósito y Contexto Universitario

Este documento adapta la propuesta original de migración de Kimün a un entorno de demostración académica bajo las **estrictas limitaciones de una cuenta AWS Academy Learner Lab ($50 USD de presupuesto y restricciones IAM)**. 

El objetivo es demostrar el dominio de arquitecturas híbridas (PostgreSQL + DynamoDB + Big Data), Infraestructura como Código (Terraform) y Automatización (Ansible) de forma 100% funcional, pero optimizada para estar encendida solo por unas horas durante las pruebas y la presentación final.

## 2. Ajustes Arquitectónicos para "Learner Lab" (FinOps)

Para no agotar los $50 dólares y evitar errores de permisos (Access Denied), se aplicarán los siguientes recortes a la arquitectura ideal:

1. **Un Solo Entorno (Demo):** No existirán entornos de Dev, Staging y Prod en AWS. El desarrollo se hará en los computadores locales (usando SQLite y DynamoDB Local). AWS se usará exclusivamente como entorno final de presentación.
2. **Eliminación del Balanceador (ALB):** No usaremos Application Load Balancers. Terraform asignará una IP Pública (Elastic IP) a la instancia EC2, y el profesor accederá a la plataforma directamente mediante esa IP (ej. `http://54.21.32.11:8000`).
3. **Rol IAM Único (`LabRole`):** AWS Learner Lab prohíbe crear roles. Terraform debe asignar el rol preexistente llamado `LabRole` a la instancia EC2. Este rol ya tiene permisos suficientes para interactuar con DynamoDB, S3 y Athena.
4. **Base de Datos Relacional Eficiente:** Para evitar el costo de un servicio administrado como RDS, **Ansible** instalará PostgreSQL localmente dentro de la misma máquina EC2 que aloja la aplicación Django. Esto consolida el gasto en una sola máquina (`t3.small`).
5. **Cero Endpoints VPC:** Las conexiones a DynamoDB y S3 se harán a través de la salida a internet estándar de la VPC, ahorrando los $7 dólares mensuales por endpoint.

## 3. Arquitectura de Presentación

```text
Usuarios / Profesor (Navegador)
   |
[ Elastic IP Pública ]
   |
[ Instancia EC2 (t3.small) ] <--- Configurada por Ansible
   |-- Nginx + Gunicorn + Django
   |-- PostgreSQL Local (Usuarios, Permisos, Catálogo de Cursos)
   |
   |---- [ AWS DynamoDB ] (On-Demand) <--- Creado por Terraform
   |       Inscripciones, Evaluaciones, Intentos
   |
   |---- [ Amazon S3 ] <--- Creado por Terraform
           Logs exportados en JSON/Parquet
           |
           +-- [ AWS Glue + Athena ] (Costo por TB escaneado: $0.00 en demo)
```

## 4. Guía de Ejecución para la Demostración

Dado que el sistema no estará encendido 24/7, el flujo para el día de la presentación (o días de prueba) será un despliegue "efímero":

### Paso 1: Aprovisionamiento (5 minutos)
En la terminal local, ejecutar:
```bash
terraform init
terraform apply -auto-approve
```
*Esto creará la Red, la máquina EC2, la tabla en DynamoDB y el bucket S3.*

### Paso 2: Configuración (5 minutos)
Pasarle la IP de la máquina EC2 creada a Ansible para que configure el software:
```bash
ansible-playbook -i inventario.ini setup_kimun.yml
```
*Ansible instalará PostgreSQL, Python, clonará este repositorio, hará las migraciones de Django (`python manage.py migrate`) y dejará la web corriendo.*

### Paso 3: Sembrado de Datos y Backfill (2 minutos)
Para que la presentación no esté vacía, se ejecutará un script de Django que cree usuarios y cursos de prueba en PostgreSQL, y luego simule la migración masiva a DynamoDB:
```bash
python manage.py seed_relational_data
python manage.py migrate_to_dynamodb --entity evaluations
```
*Este es el momento clímax de la presentación: demostrar cómo el script mueve los datos pesados a DynamoDB en vivo.*

### Paso 4: Demostración de Big Data (Athena)
En la consola de AWS, el equipo mostrará cómo ejecutar manualmente el **Glue Crawler** sobre el bucket S3. Una vez termine, abrirán Athena y ejecutarán una consulta SQL en vivo sobre el progreso de los alumnos que está respaldado en S3.

### Paso 5: Destrucción (Crucial para salvar los $50)
Apenas el profesor ponga la nota y termine la clase, ejecutar:
```bash
terraform destroy -auto-approve
```
*Todo desaparece y la cuenta de AWS deja de cobrar.*

## 5. Diseño de DynamoDB Simplificado (Single-Table)

La tabla `KimunData-Demo` funcionará exactamente con la misma lógica de patrones de acceso que diseñamos previamente, pero sin la complejidad de streams bidireccionales ni "Dual-Writes" prolongados, ya que es una demostración.

- **PK:** `USER#<id>` o `COURSE#<id>`
- **SK:** `PROFILE#`, `EVAL#`, `ATTEMPT#`
- **GSI1:** Para búsquedas inversas (ej. Alumnos por Curso).

## 6. Conclusión para el Taller

Esta versión alternativa garantiza que el equipo pueda demostrar **todas** las competencias exigidas (IaC, Automatización, NoSQL y Big Data Analytics) en un flujo de trabajo ultra-moderno y profesional, pero protegiendo al 100% las limitaciones de presupuesto y permisos de una cuenta universitaria.
