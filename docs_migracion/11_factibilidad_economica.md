# 11 — Factibilidad Económica

> **Contexto:** Este proyecto tiene dos fases evaluadas: **Certamen 2**
> (infraestructura NoSQL + failover Multi-Región) y **Examen** (Big Data
> con AWS Athena + KPIs + Dashboard). Ambas fases se despliegan en AWS
> Learner Lab con un presupuesto máximo de $50 USD. Los costos de RRHH y
> licencias son estimaciones hipotéticas para un escenario de producción
> real, no valores incurridos durante el desarrollo académico.

---

## 1. Costos de Recursos Humanos (RRHH)

| Concepto | Estimación | Observación |
|----------|------------|-------------|
| Salarios del equipo (3 integrantes, primer año de egreso) | $1,500,000 CLP/mes c/u → $4,500,000 CLP/mes total | Según mercado TI junior en Chile (2026), ~$1.5M líquidos |
| Duración del proyecto | 4 meses (Certamen 2 + Examen) | Abril – Agosto 2026 |
| **Subtotal RRHH** | **$18,000,000 CLP** | 3 personas × 4 meses |

Nota: En un escenario real, este sería el costo de desarrollar Kimün desde
cero como producto comercializable. Para la ONG ALUMCO, el desarrollo fue
realizado como parte de un taller universitario, por lo que el costo real
incurrido es $0 (mano de obra académica).

---

## 2. Infraestructura (Cloud)

| Servicio | Especificación | Costo mensual | Nota |
|----------|---------------|---------------|------|
| AWS EC2 | t3.small (2 vCPU, 2 GB RAM) | ~$12 USD | Solo encendida durante pruebas y demo (~20 h/mes real) |
| AWS DynamoDB ×2 | KimunData-Demo (us-east-1 + us-west-2), PAY_PER_REQUEST | ~$2 USD | Almacenamiento mínimo (<10 MB) + RCU/WCU ocasionales |
| AWS S3 | kimumdata-demo-analytics | ~$0.10 USD | <5 MB de exports JSON Lines comprimidos |
| AWS Glue Catalog | 1 base de datos | ~$1 USD | Catálogo para Athena |
| AWS Athena | ~10 MB escaneados por query | ~$0.50 USD | 5 queries KPI ejecutadas ocasionalmente |
| **Subtotal infraestructura** | | **~$15.60 USD/mes** | Bien dentro del límite de $50 USD del Learner Lab |

### Desglose por fase

| Fase | Servicios utilizados | Costo incremental |
|------|---------------------|-------------------|
| Certamen 2 (NoSQL + Failover) | EC2 + DynamoDB ×2 | ~$14 USD/mes |
| Examen (Big Data) | EC2 + DynamoDB ×2 + S3 + Glue + Athena | ~$15.60 USD/mes |

### Proyección anual (escenario producción real)

Si Kimün se ofreciera como SaaS a residencias ELEAM (~50 residencias,
~500 usuarios):

| Servicio | Costo mensual estimado |
|----------|------------------------|
| EC2 (2× t3.medium con auto-scaling) | ~$70 USD |
| DynamoDB (PAY_PER_REQUEST, ~50K operaciones/día) | ~$30 USD |
| S3 (materiales de cursos: PDFs, videos) | ~$15 USD |
| Athena + Glue (consultas semanales de KPIs) | ~$5 USD |
| **Total producción** | **~$120 USD/mes** |

---

## 3. Licencias y Software

| Herramienta | Tipo | Costo | Nota |
|-------------|------|-------|------|
| Ubuntu 22.04 LTS | Sistema operativo | $0 | Open source |
| Django 5.0 | Framework web | $0 | Open source (BSD) |
| Nginx | Servidor web | $0 | Open source |
| Gunicorn | WSGI server | $0 | Open source |
| DynamoDB | Base de datos NoSQL | Incluido en infraestructura | Servicio AWS, sin licencia separada |
| Git + GitHub | Control de versiones | $0 | GitHub Free para equipos |
| Visual Studio Code | IDE | $0 | Gratuito |
| Terraform | IaC | $0 | Open source (BSL) |
| Ansible | Configuración | $0 | Open source |
| Chart.js | Visualización | $0 | Open source (MIT) |
| **Subtotal licencias** | | **$0** | Todo el stack es open source o incluido en AWS |

---

## 4. Operaciones y Mantenimiento

| Concepto | Frecuencia | Esfuerzo estimado | Costo mensual |
|----------|-----------|-------------------|---------------|
| Actualizaciones de dependencias (Django, boto3) | Mensual | 2 horas | ~$40 USD (a $20/hora freelance) |
| Corrección de bugs | Según incidencias | 5 horas/mes | ~$100 USD |
| Monitoreo (CloudWatch + logs) | Continuo | 1 hora/mes | ~$20 USD |
| **Subtotal operaciones** | | | **~$160 USD/mes** |

Nota: Durante el desarrollo académico, este costo fue $0 (realizado por el
equipo como parte del taller). En producción real, una ONG como ALUMCO
podría contratar mantenimiento mínimo a un freelance.

---

## 5. Seguridad

| Concepto | Costo | Nota |
|----------|-------|------|
| Certificado SSL/TLS | $0 | AWS Certificate Manager (ACM) — gratuito. No implementado en Learner Lab por restricciones de IAM, pero disponible en producción |
| HTTPS enforcement | $0 | Configuración en Nginx |
| HSTS + cookies seguras | $0 | Configuración en Django (`SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`) |
| **Subtotal seguridad** | **$0** | El costo es solo de configuración, no de licencias |

---

## 6. Despliegue e Implementación

| Concepto | Esfuerzo | Nota |
|----------|----------|------|
| Migración de datos (seed_dynamodb) | 1 hora | Automatizado con management command |
| Configuración inicial (Terraform + Ansible) | 30 minutos | Infraestructura como Código — repetible |
| Capacitación de usuarios (admin + docentes) | 2 horas | Manual de usuario + sesión guiada |
| **Subtotal despliegue** | **~3.5 horas** | Costo único, no recurrente |

---

## 7. Contingencia (Imprevistos)

Se recomienda un fondo de **15-20%** sobre el costo total operativo anual.

### Cálculo para escenario académico

| Rubro | Costo mensual |
|-------|---------------|
| Infraestructura (Learner Lab) | $15.60 USD |
| 15% de contingencia | $2.34 USD |
| **Total con contingencia** | **$17.94 USD/mes** |

→ Holgura de $32 USD frente al límite de $50 USD del Learner Lab.

### Cálculo para escenario producción real

| Rubro | Costo anual |
|-------|-------------|
| Infraestructura cloud | $1,440 USD |
| RRHH (1 freelance mantenimiento) | $1,920 USD |
| Licencias | $0 |
| Subtotal operativo | $3,360 USD/año |
| Contingencia (20%) | $672 USD |
| **Total anual producción** | **~$4,032 USD/año** |

Para una ONG como ALUMCO, este costo es mínimo comparado con el costo de
capacitación presencial tradicional (instructores, materiales físicos,
desplazamiento a residencias ELEAM).

---

## Resumen ejecutivo

| Categoría | Costo académico (Learner Lab) | Costo producción real (anual) |
|-----------|------------------------------|------------------------------|
| RRHH | $0 (taller universitario) | ~$1,920 USD (freelance) |
| Infraestructura | ~$15.60/mes (~$62.40 total taller) | ~$1,440 USD |
| Licencias | $0 | $0 |
| Operaciones | $0 | ~$1,920 USD |
| Seguridad | $0 | $0 |
| Despliegue | $0 (automatizado) | ~$70 USD (one-time) |
| Contingencia (15-20%) | ~$12 USD | ~$672 USD |
| **Total** | **~$74 USD** (4 meses) | **~$4,032 USD/año** |
