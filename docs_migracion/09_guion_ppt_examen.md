# 09 — Guion de PPT para el Examen

> **Para cualquier agente IA del equipo:** este documento describe qué
> poner en cada slide de la presentación. No contiene código ejecutable.

---

## Estructura (12 slides, ~12 minutos)

### Slide 1 — Portada
- Título: **Kimün + Big Data: Plataforma de Capacitación para ONG ALUMCO**
- Subtítulo: Advanced Databases Workshop — Examen
- Nombres del equipo, fecha (19 agosto 2026)

### Slide 2 — Índice
Lista numerada de las secciones:
1. Problemática
2. Solución
3. Arquitectura
4. Infraestructura como Código
5. Distribución de Datos (Failover)
6. KPIs Big Data
7. Pipeline Athena
8. Dashboard
9. Costos
10. Conclusiones

### Slide 3 — Problemática
- ONG ALUMCO capacita personal de residencias ELEAM
- Proceso manual: materiales físicos, evaluaciones en papel, certificados a mano
- Escala: múltiples residencias, alta rotación de personal
- Necesidad: trazabilidad, automatización, análisis de datos

### Slide 4 — Solución: Kimün LMS
- Plataforma web con roles (admin, docente, colaborador)
- Cursos con clases, materiales, evaluaciones automáticas, tareas
- Certificados digitales con código de verificación
- 100% cloud en AWS, zero infraestructura física

### Slide 5 — Diagrama de Arquitectura
Insertar el diagrama ASCII de `06_instructivo_despliegue.md` sección 0, o hacer uno visual con:
- Usuario → Internet → VPC → EC2 (Nginx + Gunicorn + Django)
- EC2 → DynamoDB us-east-1 (primario) + DynamoDB us-west-2 (réplica)
- DynamoDB → S3 → Glue → Athena → Dashboard

### Slide 6 — Infraestructura como Código
- **Terraform**: VPC, subredes, EC2, DynamoDB ×2, S3, Glue, Athena Workgroup
- **Ansible**: instalación de dependencias, clon del repo, Gunicorn + Nginx, variables de entorno
- Mostrar fragmentos de `main.tf` y `playbook.yml` (3-5 líneas cada uno)

### Slide 7 — Arquitectura de Distribución (Failover)
- Estrategia: **Dual-Write Multi-Región**
- Escritura simultánea en `us-east-1` y `us-west-2`
- Lectura desde región primaria con failover automático
- Demo: eliminar tabla primaria → la app sigue funcionando desde secundaria
- Mostrar fragmento de `dynamodb_client.py` con la lógica de failover

### Slide 8 — KPIs Big Data (lista)
Tabla con los 5 KPIs:

| # | KPI | Fuente Athena |
|---|-----|---------------|
| 1 | Tasa de Completación de Cursos | `enrollments` |
| 2 | Rendimiento Promedio por Curso | `eval_attempts` + `evaluations` |
| 3 | Tasa de Certificación | `certificates` |
| 4 | Distribución de Usuarios por Cargo | `user_profiles` |
| 5 | Tiempo Promedio de Completación | `enrollments` |

### Slide 9 — Pipeline Big Data
- Flujo: DynamoDB → `export_to_s3.py` → S3 (JSON Lines) → Glue Catalog → Athena → Dashboard
- Mostrar fragmento de `bigdata/queries/kpis_athena.sql` (una query de ejemplo)
- Dashboard accesible en `/reportes/bigdata/` (solo admin)

### Slide 10 — Dashboard
- Screenshot del dashboard con los 5 gráficos
- Explicar cada tipo de visualización (barras, pie, horizontal)
- Mencionar que cada KPI incluye una **decisión de negocio** accionable

### Slide 11 — Factibilidad Económica

Ver documento completo en `docs_migracion/11_factibilidad_economica.md`.

Resumen de las 7 categorías:

**1. RRHH:** 3 integrantes × $1.5M CLP/mes × 4 meses = $18M CLP (hipotético).
Desarrollo real: $0 (taller universitario).

**2. Infraestructura Cloud (Learner Lab):**
| Servicio | Costo/mes |
|----------|-----------|
| EC2 t3.small | ~$12 USD |
| DynamoDB ×2 | ~$2 USD |
| S3 | ~$0.10 USD |
| Athena + Glue | ~$1.50 USD |
| **Total** | **~$15.60 USD** |

Presupuesto Learner Lab: $50 USD. Holgura: $34 USD.

**3. Licencias:** $0. Todo el stack es open source (Django, Nginx, Ubuntu,
Terraform, Ansible, Chart.js).

**4. Operaciones:** ~$160 USD/mes en producción (actualizaciones, bugs,
monitoreo). En modo académico: $0.

**5. Seguridad:** $0 (certificados SSL vía AWS ACM, configuración en Nginx).

**6. Despliegue:** ~3.5 horas one-time (automatizado con Terraform + Ansible).

**7. Contingencia:** 15-20% sobre operativo anual.
Producción real estimada: ~$4,032 USD/año total.

### Slide 12 — Conclusiones
- Arquitectura 100% cloud, 100% NoSQL, zero SQL residual
- Tolerancia a fallos multi-región comprobada
- Big Data integrado con Athena para toma de decisiones
- La ONG ALUMCO puede:
  - Identificar cursos con baja completación → rediseñar
  - Detectar residencias sin capacitación → focalizar recursos
  - Medir tiempos de formación → optimizar carga horaria

---

## Demo en vivo (3 minutos, entre slides 7 y 10)

1. Mostrar `http://IP_EC2/` — login, navegar cursos
2. `aws dynamodb delete-table --table-name KimunData-Demo --region us-east-1`
3. Refrescar navegador — mostrar que la app sigue viva
4. Mostrar `/reportes/bigdata/` con los 5 gráficos
5. `terraform apply -auto-approve` para restaurar

**Video de respaldo:** grabar estos 5 pasos por si la red falla en vivo.

---

## Para el agente IA que genere el PPT

- Usar skill `presentations` si está disponible
- Cada slide debe ser conciso: título + 3-5 bullets máximo
- Incluir screenshots reales de la app, el dashboard, y la consola AWS
- Los fragmentos de código deben ser 3-5 líneas máximo, con syntax highlighting
- La demo en vivo se sale del PPT — solo dejar una slide que diga "DEMO EN VIVO"
