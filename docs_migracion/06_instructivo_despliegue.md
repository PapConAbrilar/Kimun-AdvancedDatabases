# Instructivo de Despliegue Completo — Kimün + Big Data

> **Examen: Advanced Databases Workshop**
> **Fecha presentación: 19 de agosto de 2026**
> **Presupuesto máximo: $50 USD (AWS Learner Lab)**

Este documento es la guía definitiva paso a paso para desplegar la
plataforma Kimün en AWS Learner Lab desde cero, incluyendo:

- Infraestructura como Código (Terraform)
- Configuración automatizada (Ansible)
- Base de datos NoSQL 100% DynamoDB con replicación Multi-Región
- Pipeline Big Data (DynamoDB → S3 → Athena → Dashboard)
- Prueba de failover (requisito del examen)
- Limpieza y control de costos

---

## 0. Prerrequisitos

### Credenciales AWS Learner Lab

Cada sesión de Learner Lab entrega credenciales temporales. Debes
configurarlas antes de cada despliegue.

1. Inicia sesión en AWS Academy Learner Lab.
2. Haz clic en "Start Lab" y espera a que el indicador esté verde.
3. Haz clic en "AWS Details" y copia las credenciales.
4. Configura las variables de entorno en tu terminal:

```bash
export AWS_ACCESS_KEY_ID=ASIAXXXXXXXXXXXXXX
export AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export AWS_SESSION_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export AWS_DEFAULT_REGION=us-east-1
```

5. Verifica que las credenciales funcionan:

```bash
aws sts get-caller-identity
# Debe mostrar: Account: 'xxxx', UserId: 'xxxx', Arn: arn:aws:sts::xxxx:assumed-role/LabRole/...
```

### Llave SSH

Genera una llave SSH (solo la primera vez) y súbela a AWS:

```bash
ssh-keygen -t rsa -b 2048 -f ~/.ssh/vockey -N ""
aws ec2 import-key-pair \
    --key-name "vockey" \
    --public-key-material fileb://~/.ssh/vockey.pub \
    --region us-east-1
```

> **Nota:** Si Learner Lab ya incluye una llave llamada `vockey`, descárgala
> como `.pem`, conviértela y dale permisos:
> ```bash
> cp vockey.pem ~/.ssh/vockey
> chmod 400 ~/.ssh/vockey
> ```

### Herramientas necesarias

| Herramienta | Versión mínima | Verificación |
|-------------|---------------|--------------|
| Terraform | 1.5+ | `terraform version` |
| Ansible | 2.14+ | `ansible --version` |
| AWS CLI | 2.0+ | `aws --version` |
| Python | 3.10+ | `python3 --version` |
| Git | 2.30+ | `git --version` |

### Repositorio

Clona el proyecto si no lo tienes:

```bash
git clone https://github.com/PapConAbrilar/Kimun-AdvancedDatabases.git
cd Kimun-AdvancedDatabases
git checkout experimental
```

---

## 1. Arquitectura desplegada

```
                          AWS Learner Lab
  ┌──────────────────────────────────────────────────────────────┐
  │  VPC: 10.0.0.0/16                                            │
  │  ┌──────────────────────────────────────────────────────┐    │
  │  │  Subred pública: 10.0.1.0/24                         │    │
  │  │  ┌─────────────────────────┐                         │    │
  │  │  │  EC2 (t3.small)         │                         │    │
  │  │  │  Nginx :80              │                         │    │
  │  │  │  Gunicorn + Django      │                         │    │
  │  │  │  LabInstanceProfile     │                         │    │
  │  │  └───────────┬─────────────┘                         │    │
  │  └──────────────┼───────────────────────────────────────┘    │
  │                 │                                            │
  │    ┌────────────▼──────────────┐                             │
  │    │  DynamoDB: KimunData-Demo │    ┌──────────────────┐     │
  │    │  us-east-1 (primario)     │◄──▶│  us-west-2       │     │
  │    │  PK, SK, GSI1             │    │  (réplica)       │     │
  │    └────────────┬──────────────┘    └──────────────────┘     │
  │                 │                                            │
  │                 │  export_to_s3.py                           │
  │                 ▼                                            │
  │    ┌────────────────────────────┐                            │
  │    │  S3: kimumdata-demo-       │                            │
  │    │       analytics            │                            │
  │    │  exports/YYYY-MM-DD/       │                            │
  │    │  athena-results/           │                            │
  │    └────────────┬───────────────┘                            │
  │                 │                                            │
  │                 ▼                                            │
  │    ┌────────────────────────────┐                            │
  │    │  Glue Catalog: kimun_      │                            │
  │    │  bigdata                   │                            │
  │    └────────────┬───────────────┘                            │
  │                 │                                            │
  │                 ▼                                            │
  │    ┌────────────────────────────┐                            │
  │    │  Athena: kimun-bigdata     │                            │
  │    │  (5 KPIs SQL)              │                            │
  │    └────────────────────────────┘                            │
  └──────────────────────────────────────────────────────────────┘
```

---

## 2. Terraform — Infraestructura

### Recursos que se crean

| Recurso | Descripción | Región |
|---------|-------------|--------|
| VPC + Subnet + IGW | Red aislada | us-east-1 |
| EC2 t3.small | Servidor web (Ubuntu 22.04) | us-east-1 |
| Security Group | Puertos 80 (HTTP) + 22 (SSH) | us-east-1 |
| DynamoDB `KimunData-Demo` | Tabla principal + GSI1 | us-east-1 |
| DynamoDB `KimunData-Demo` | Réplica (dual-write) | us-west-2 |
| S3 `kimumdata-demo-analytics` | Data lake Big Data | us-east-1 |
| S3 Lifecycle Policy | Expira exports > 30 días | us-east-1 |
| Glue DB `kimun_bigdata` | Catálogo Athena | us-east-1 |
| Athena Workgroup | Output a S3 | us-east-1 |

### Ejecución

```bash
cd terraform/

# Inicializar (primera vez)
terraform init

# Validar sintaxis
terraform fmt -check -recursive
terraform validate

# Previsualizar cambios
terraform plan

# Desplegar
terraform apply -auto-approve
```

### Outputs importantes

```
ec2_public_ip       = "X.X.X.X"          # ← ¡Anótala!
dynamodb_table_name = "KimunData-Demo"
s3_analytics_bucket = "kimumdata-demo-analytics"
athena_workgroup    = "kimun-bigdata"
```

### Troubleshooting Terraform

| Error | Causa probable | Solución |
|-------|---------------|----------|
| `InvalidClientTokenId` | Credenciales expiradas | Re-copia credenciales de Learner Lab |
| `UnauthorizedOperation` | LabRole sin permisos | Verifica que usas `LabInstanceProfile` |
| `InvalidKeyPair.NotFound` | Llave SSH no subida | Ejecuta `aws ec2 import-key-pair` |
| `BucketAlreadyExists` | Nombre de bucket S3 duplicado | Cambia `dynamodb_table_name` en `variables.tf` |

---

## 3. Ansible — Configuración del servidor

### Lo que hace el playbook

1. Actualiza paquetes del sistema (`apt update`)
2. Instala Python 3, pip, venv, git, nginx, openssl
3. Clona el repositorio desde GitHub (branch `experimental`)
4. Crea entorno virtual e instala dependencias (`requirements.txt`)
5. Recolecta archivos estáticos (`collectstatic`)
6. Genera clave secreta y crea `/etc/kimun.env`
7. Configura Gunicorn como servicio systemd
8. Configura Nginx como proxy reverso
9. Arranca ambos servicios

### Ejecución

```bash
cd ansible/

# Verificar sintaxis
ansible-playbook --syntax-check playbook.yml

# Desplegar (reemplaza IP_EC2 por la IP que dio Terraform)
ansible-playbook -i "IP_EC2," playbook.yml \
    -u ubuntu \
    --private-key ~/.ssh/vockey
```

> **Importante:** La coma después de la IP (`"IP,"`) es obligatoria para
> que Ansible la interprete como un host inline.

### Verificar despliegue

```bash
ansible-playbook -i "IP_EC2," verificar_despliegue.yml \
    -u ubuntu \
    --private-key ~/.ssh/vockey
```

Esto verifica:
- Rama y commit desplegado
- `django check` sin errores
- Gunicorn y Nginx corriendo
- Respuesta HTTP 200 en `http://127.0.0.1/`

### Troubleshooting Ansible

| Error | Causa probable | Solución |
|-------|---------------|----------|
| `Connection timed out` | Security Group no permite SSH | Revisa `terraform apply` |
| `Permission denied (publickey)` | Llave SSH incorrecta | Verifica `~/.ssh/vockey` |
| `git clone` falla | EC2 sin acceso a internet | Revisa IGW + route table |
| `pip install` falla | Requerimientos conflictivos | SSH a EC2 y revisa `pip install -r requirements.txt` manualmente |

---

## 4. Post-despliegue — Datos de demostración

### Cargar datos demo

```bash
ansible-playbook -i "IP_EC2," cargar_datos_demo.yml \
    -u ubuntu \
    --private-key ~/.ssh/vockey
```

Esto ejecuta `python manage.py seed_dynamodb` que crea:

| Recurso | Cantidad | Detalle |
|---------|----------|---------|
| Admin | 1 | `admin@kimun.cl` / `admin` |
| Docente | 1 | `profesor@kimun.cl` / `profesor` |
| Alumnos | 5 | `alumno1..5@kimun.cl` / `alumno` |
| Cursos | 3 | Con evaluaciones e intentos simulados |

### Acceder a la aplicación

```
http://IP_EC2/
```

### Troubleshooting de datos

| Problema | Solución |
|----------|----------|
| "Usuario o contraseña incorrectos" | Ejecuta `cargar_datos_demo.yml` de nuevo |
| "Curso no encontrado" | El seed solo crea 3 cursos con ID `CURSO-1`, `CURSO-2`, `CURSO-3` |
| Página en blanco | Revisa logs: `ssh ubuntu@IP_EC2 'sudo journalctl -u kimun --no-pager -n 50'` |

---

## 5. Big Data — Pipeline Athena + Dashboard

### 5.1 Exportar DynamoDB a S3

El script `bigdata/export_to_s3.py` escanea DynamoDB, agrupa por
`entity_type` y escribe archivos JSON Lines comprimidos en S3:

```bash
# Desde tu máquina local (necesita credenciales AWS)
python manage.py exportar_datos_s3

# O desde la EC2
ssh ubuntu@IP_EC2 \
    "cd /opt/kimun && sudo venv/bin/python3 manage.py exportar_datos_s3"
```

**Formato de salida en S3:**

```
s3://kimumdata-demo-analytics/
  exports/2026-08-09/
    USER_PROFILE/data.jsonl.gz
    COURSE_METADATA/data.jsonl.gz
    ENROLLMENT/data.jsonl.gz
    EVALUATION/data.jsonl.gz
    EVAL_ATTEMPT/data.jsonl.gz
    CERTIFICATE/data.jsonl.gz
    ...
  athena-results/          # Resultados de queries Athena
```

### 5.2 Crear tablas externas en Athena

Abre la consola de AWS Athena en `us-east-1`, selecciona la base de datos
`kimun_bigdata` y ejecuta el contenido completo de:

```
bigdata/queries/ddl_tablas_externas.sql
```

> **Antes de ejecutar**, reemplaza en el SQL:
> - `S3_ANALYTICS_BUCKET` → `kimumdata-demo-analytics`
> - `YYYY-MM-DD` → la fecha actual (ej. `2026-08-09`)

Verifica con:

```sql
SELECT COUNT(*) FROM user_profiles;
SELECT COUNT(*) FROM enrollments;
```

### 5.3 Ejecutar consultas KPI

Ejecuta el contenido de `bigdata/queries/kpis_athena.sql` en la consola
Athena.

### 5.4 Ver el dashboard

```
http://IP_EC2/reportes/bigdata/
```

> **Solo accesible con rol `admin`**. Login: `admin@kimun.cl` / `admin`

El dashboard:
- Muestra los 5 KPIs con gráficos Chart.js
- Incluye tablas de datos y decisiones de negocio
- Si Athena no está disponible, usa datos simulados (siempre se ve algo)

### 5.5 Actualizar el dashboard

```bash
# Re-ejecutar KPIs y refrescar caché
ssh ubuntu@IP_EC2 \
    "cd /opt/kimun && sudo venv/bin/python3 manage.py exportar_datos_s3 --solo-kpis"
```

---

## 6. Prueba de Failover (Requisito Examen)

La aplicación implementa **dual-write + failover automático**. Si la tabla
de `us-east-1` se cae, el cliente DynamoDB conmuta a `us-west-2`.

### Demostración en vivo

```
1. Mostrar app funcionando en http://IP_EC2 (navegar cursos, login)
2. Ejecutar en consola AWS:
   aws dynamodb delete-table --table-name KimunData-Demo --region us-east-1
3. Refrescar el navegador
4. ¡La app sigue funcionando! (leyendo/escribiendo en us-west-2)
```

> **Nota:** La tabla eliminada se recrea automáticamente al ejecutar
> `terraform apply` de nuevo.

### Video de respaldo

Graba la pantalla mientras ejecutas los 4 pasos anteriores. En caso de
falla durante la demo en vivo, tienes el video como evidencia.

---

## 7. Guion de presentación (PPT + Demo)

### Estructura PPT (máximo 12 slides)

| Slide | Contenido | Tiempo |
|-------|-----------|--------|
| 1 | Portada: Kimün + Big Data para ONG ALUMCO | 30s |
| 2 | Índice | 20s |
| 3 | Problemática: capacitación manual de personal ELEAM | 1min |
| 4 | Solución: LMS con DynamoDB + Athena | 1min |
| 5 | Diagrama de arquitectura (el de la sección 1) | 1min |
| 6 | Terraform + Ansible (código destacado) | 1min |
| 7 | Arquitectura de distribución: Dual-Write Multi-Región | 1min |
| 8 | KPIs Big Data (lista de 5) | 1min |
| 9 | Pipeline Big Data: DynamoDB → S3 → Athena → Dashboard | 1min |
| 10 | Demo en vivo: app funcionando + failover + dashboard | 3min |
| 11 | Costos (breakdown de servicios AWS) | 30s |
| 12 | Conclusión + decisiones de negocio | 1min |

### Costos estimados (Learner Lab)

| Servicio | Costo/mes | Nota |
|----------|-----------|------|
| EC2 t3.small | ~$12 USD | Solo encendida durante pruebas |
| DynamoDB (2 regiones) | ~$2 USD | PAY_PER_REQUEST, pocos datos |
| S3 | ~$0.10 USD | Pocos MB de exports |
| Athena | ~$0.50 USD | ~10 MB escaneados por query |
| Glue Catalog | ~$1 USD | Por base de datos |
| **Total** | **~$15 USD** | Bien dentro del límite de $50 |

---

## 8. Limpieza y FinOps (¡OBLIGATORIO!)

**NUNCA dejes la infraestructura corriendo después de probar.** Los $50
de Learner Lab se agotan rápido si dejas la EC2 encendida.

### Destruir todo

```bash
cd terraform/
terraform destroy -auto-approve
```

### Verificar destrucción

```bash
# No debe mostrar la EC2
aws ec2 describe-instances --region us-east-1 \
    --filters "Name=tag:Name,Values=Kimun-Web-Server" \
    --query "Reservations[].Instances[].State.Name"

# No debe mostrar la tabla
aws dynamodb describe-table --table-name KimunData-Demo --region us-east-1

# No debe mostrar el bucket
aws s3 ls s3://kimumdata-demo-analytics/
```

---

## 9. Checklist pre-examen

- [ ] Credenciales Learner Lab renovadas y funcionando
- [ ] Llave SSH (`~/.ssh/vockey`) presente y con permisos 400
- [ ] `terraform apply` exitoso sin errores
- [ ] `ansible-playbook playbook.yml` exitoso sin tareas rojas
- [ ] Datos demo cargados (`seed_dynamodb`)
- [ ] Login funcional: `admin@kimun.cl` / `admin`
- [ ] Login funcional: `alumno1@kimun.cl` / `alumno`
- [ ] Navegación: cursos, evaluaciones, tareas, calendario
- [ ] Dashboard Big Data: `http://IP_EC2/reportes/bigdata/` muestra KPIs
- [ ] Prueba de failover: eliminar tabla us-east-1, app sigue viva
- [ ] Video de respaldo grabado (por si falla la demo en vivo)
- [ ] `terraform destroy` ejecutado (para preservar presupuesto)
- [ ] PPT subido al LMS al menos 1 día antes (18 de agosto)
- [ ] URL de la app funcionando anotada
- [ ] `main.tf` listo para entregar

---

## 10. Comandos de emergencia

```bash
# Ver logs de Django en EC2
ssh ubuntu@IP_EC2 'sudo journalctl -u kimun --no-pager -n 100'

# Ver logs de Nginx
ssh ubuntu@IP_EC2 'sudo tail -50 /var/log/nginx/error.log'

# Reiniciar servicios
ssh ubuntu@IP_EC2 'sudo systemctl restart kimun nginx'

# Re-desplegar Ansible después de cambios en código
cd ansible/
ansible-playbook -i "IP_EC2," playbook.yml -u ubuntu --private-key ~/.ssh/vockey

# Regenerar tabla DynamoDB us-east-1 si se eliminó en failover
cd terraform/
terraform apply -auto-approve -replace="aws_dynamodb_table.kimun_data"
```
