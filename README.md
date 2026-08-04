## Proyecto: Advanced Databases Workshop

Esta sección documenta los requisitos para la asignatura "Advanced databases workshop", abarcando tanto el contexto del proyecto original como su futura migración hacia bases de datos no tradicionales y arquitecturas Big Data.

### 1. Propuesta de Proyecto

**Contexto del Proyecto Original (Kimün):**
- **Problema:** La ONG ALUMCO necesitaba capacitar de forma eficiente y estandarizada al personal y voluntarios que trabajan con adultos mayores en residencias ELEAM, enfrentando dificultades para gestionar materiales, evaluar aprendizajes y emitir certificados de forma manual.
- **Solución:** Se desarrolló Kimün, un sistema LMS (Learning Management System) que permite administrar roles, subir cursos, realizar evaluaciones automáticas y generar diplomas, centralizando toda la gestión educativa.

**Contexto de la Migración:**
- **Problema de la Arquitectura Actual:** El sistema actual utiliza bases de datos relacionales (SQLite/PostgreSQL). A medida que crezcan los usuarios, el volumen de registros (evaluaciones, logs de actividad) y la necesidad de análisis masivo, la arquitectura relacional centralizada podría enfrentar cuellos de botella en escalabilidad y rendimiento.
- **Solución Propuesta:** Migrar hacia un modelo de bases de datos no relacionales (NoSQL) que permita alta disponibilidad, escalabilidad horizontal y procesamiento de grandes volúmenes de datos.
- **Diseño/Arquitectura:** Modelado de la nueva infraestructura distribuida, definiendo los flujos de datos e integración de servicios Cloud.
- **Costos:** Estimación y proyección del presupuesto operativo para el uso de las bases de datos NoSQL, servicios cloud e infraestructura.

### 2. Elección de Estrategia
Se debe seleccionar y justificar la estrategia de distribución de datos a utilizar:
- **Particionada** (Sharding / Partitioning)
- **Réplica** (Replication)
- **Federada** (Federated Databases)

### 3. Restricciones Técnicas
- **Uso de NoSQL:** Es obligatorio migrar la persistencia de datos utilizando **DynamoDB**, **MongoDB** o **Cassandra**.
- **Infraestructura como Código (IaC):**
  - **Terraform:** Para levantar y aprovisionar las instancias y servicios en la nube.
  - **Ansible, Chef o Puppet:** Para la configuración y automatización del software dentro de los servidores.
- **Big Data:** Integración de análisis y procesamiento de datos masivos utilizando **AWS Athena** o **Hadoop**.
