# 10 — Troubleshooting: Errores Comunes y Soluciones

> **Para agentes IA del equipo:** este documento es la referencia canónica de
> errores. Si un comando falla, buscar aquí por el mensaje exacto del error.
> Cada entrada tiene causa + comando de solución listo para copiar y pegar.

---

## Credenciales AWS

| Error | Causa | Solución |
|-------|-------|----------|
| `ExpiredToken` | Las credenciales temporales de Learner Lab expiran cada ~3-4 horas | Volver a AWS Details → copiar las 3 variables → `export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=...` |
| `InvalidClientTokenId` | Token mal copiado (espacios extra, salto de línea) | Re-copiar sin espacios. Verificar con `aws sts get-caller-identity` |
| `AccessDenied: s3:PutBucketPolicy` | Learner Lab bloquea bucket policies públicas | Ya solucionado: `main.tf` no usa `aws_s3_bucket_policy`. Si persiste, verificar que no haya un recurso `aws_s3_bucket_policy` en el código |

---

## Terraform

| Error | Causa | Solución |
|-------|-------|----------|
| `VpcLimitExceeded` | Learner Lab limita a ~5 VPCs. Sesiones anteriores dejaron VPCs huérfanas | `for vpc in $(aws ec2 describe-vpcs --region us-east-1 --query "Vpcs[?IsDefault==\`false\`].VpcId" --output text); do aws ec2 delete-vpc --vpc-id $vpc --region us-east-1; done` |
| `InvalidKeyPair.NotFound` | La llave `vockey` no está registrada en AWS | `aws ec2 delete-key-pair --key-name vockey --region us-east-1 2>/dev/null; ssh-keygen -t rsa -b 2048 -f ~/.ssh/vockey -N ""; aws ec2 import-key-pair --key-name vockey --public-key-material fileb://~/.ssh/vockey.pub --region us-east-1` |
| `InvalidKeyPair.Duplicate` | La llave ya existe pero la clave local cambió | `aws ec2 delete-key-pair --key-name vockey --region us-east-1` y luego re-importar con la nueva clave pública |
| `ResourceInUseException: Table already exists` | Tabla DynamoDB de sesión anterior | `aws dynamodb delete-table --table-name KimunData-Demo --region us-east-1` (y `us-west-2`) |
| `BucketAlreadyExists` | Bucket S3 de sesión anterior | `aws s3 rb s3://kimundata-demo-analytics --force` |
| `AlreadyExistsException: Database already exists` | Base de datos Glue de sesión anterior | `aws glue delete-database --name kimun_bigdata` |
| `InvalidRequestException: WorkGroup is already created` | Workgroup Athena de sesión anterior | `aws athena delete-work-group --work-group kimun-bigdata --recursive-delete-option` |
| `Invalid Attribute Combination` (warning lifecycle) | Provider AWS 5.x requiere `filter {}` explícito en lifecycle rules | Ya solucionado en `main.tf`. Ignorar si sale como warning |

---

## Ansible

| Error | Causa | Solución |
|-------|-------|----------|
| `UNREACHABLE` / `Connection refused` | EC2 está booteando (tarda ~60s después de `terraform apply`) | Esperar 60 segundos y reintentar |
| `Host key verification failed` | IP reutilizada de EC2 anterior con host key diferente | `ssh-keygen -R IP_EC2` |
| `Permission denied (publickey)` | `~/.ssh/vockey` no coincide con la llave importada en AWS | Ejecutar limpieza pre-vuelo completa (sección 3 de la guía de despliegue) |
| `git clone` timeout / falla | EC2 sin acceso a internet o GitHub | Verificar IGW y route table en AWS Console. Alternativa: hacer deploy manual con `scp` de los archivos modificados |
| Rama incorrecta desplegada | Ansible clonó `experimental` en vez de `examen-bigdata` | `ssh ubuntu@IP_EC2 'cd /opt/kimun && git checkout examen-bigdata && sudo systemctl restart kimun'` |

---

## Aplicación (Django/Kimün)

| Error | Causa | Solución |
|-------|-------|----------|
| Login `admin@kimun.cl` no funciona | Tabla recreada vacía o contraseña incorrecta | Ejecutar script de reset que crea O actualiza el admin (sección 6.2 de la guía). **Usar `manage.py shell`, NO `python3 -c`** |
| `ImproperlyConfigured: settings are not configured` | Se usó `python3 -c` en vez de `manage.py shell` | Usar `echo "..." | sudo /opt/kimun/venv/bin/python3 manage.py shell` |
| Página en blanco / 500 | Gunicorn caído o error en código | `sudo journalctl -u kimun --no-pager -n 50` y buscar `Traceback` |
| `Unknown command: 'exportar_datos_s3'` | Código no actualizado en EC2 | Rama incorrecta o no se redeployó. `git branch --show-current` debe decir `examen-bigdata` |
| `sudo: venv/bin/python3: command not found` | `sudo` no resuelve rutas relativas | Usar ruta absoluta: `sudo /opt/kimun/venv/bin/python3` |
| `scp: Permission denied` | Usuario `ubuntu` no tiene permisos de escritura en `/opt/kimun/` | Copiar a `/tmp/` primero: `scp archivo ubuntu@IP:/tmp/` y luego `ssh ... "sudo mv /tmp/archivo /opt/kimun/destino/"` |

---

## Big Data

| Error | Causa | Solución |
|-------|-------|----------|
| `NoSuchBucket` en `export_to_s3` | El bucket S3 no existe | `aws s3 mb s3://kimundata-demo-analytics --region us-east-1` |
| `Unknown command: 'setup_athena_tables'` | El archivo `setup_athena_tables.py` no está en la EC2 | Redeployar con Ansible (sección 5) o copiar manual: `scp bigdata/management/commands/setup_athena_tables.py ubuntu@IP_EC2:/tmp/ && ssh ... "sudo mv /tmp/setup_athena_tables.py /opt/kimun/bigdata/management/commands/"` |
| `TABLE_NOT_FOUND` en KPIs | Las tablas externas no existen en Athena | Ejecutar `setup_athena_tables` primero (sección 7.2 de la guía) |
| Dashboard 500: `'NoneType' object is not subscriptable` | Valor `None` de Athena en campo de string → `None[:20]` falla | Ya solucionado en `bigdata_views.py` con `_safe_float`, `_safe_int`, y `(row.get("x") or "")[:20]` |
| Dashboard 500: `float()` / `int()` sobre None | Athena devuelve `None` en campos numéricos | Ya solucionado con funciones `_safe_float()` y `_safe_int()` en `bigdata_views.py` |
| Dashboard sin gráficos (Canvas vacío, datos en tablas) | Chart.js no estaba definido cuando Alpine ejecutó `init()` | Ya solucionado: Chart.js carga sync ANTES del contenido, y el JS usa vanilla `(function(){...})()` sin depender de Alpine para charts |
| Dashboard sin gráficos (x-data quote issue) | JSON con comillas dobles dentro de atributo HTML con comillas dobles | Ya solucionado: se usa `<script>window.KPI_CHARTS = ...</script>` en vez de incrustar JSON en atributo `x-data` |
| Dashboard sin datos (tablas vacías) | a) No hay datos en DynamoDB, o b) caché guardó resultados vacíos de Athena | a) Ejecutar `seed_dynamodb`. b) `sudo rm -f /opt/kimun/bigdata/cache/kpi_cache.json && sudo systemctl restart kimun` |
| Error 403 en dashboard | Solo rol `admin` accede a `/reportes/bigdata/` | Login con `admin@kimun.cl` / `admin` |
| 500 en `/reportes/`: `can't compare offset-naive and offset-aware datetimes` | El seed guarda fechas como strings (`"2026-07-15"`), pero la vista intenta compararlas con datetimes de Django | Ya solucionado en `reportes/views.py` con `_parse_fecha()`. Si persiste, copiar `reportes/views.py` actualizado a la EC2 |
| `scp: stat local "...": No such file or directory` | El comando se ejecutó desde un directorio incorrecto (ej. `ansible/` en vez de la raíz del proyecto) | `cd` a la raíz del proyecto (`Kimun-AdvancedDatabases/`) antes de ejecutar `scp` |
| KPI 4 muestra solo "Sin área asignada" | El seed no guardaba `areacargo_nombre` en el perfil de usuario | Ya solucionado en `seed_dynamodb.py`: actualiza con `UsuarioRepository.update_user(email, {"areacargo_nombre": area, ...})` |
| KPI 5 sin datos | `date_diff()` de Athena tiene sintaxis variable entre versiones | Ya solucionado: KPI 5 usa datos estáticos de presentación en `bigdata_views.py`. Los otros 4 KPIs usan datos reales de Athena |

---

## Git

| Error | Causa | Solución |
|-------|-------|----------|
| `rejected ... (fetch first)` | Alguien más pusheó a la misma rama | `git stash && git pull origin examen-bigdata --rebase && git stash pop && git push` |
| `unmerged files` / `Committing is not possible` | Conflicto en `terraform/.terraform.lock.hcl` (archivo en `.gitignore` pero trackeado) | `git rm --cached terraform/.terraform.lock.hcl && git reset HEAD terraform/.terraform.lock.hcl` |
| `cannot pull with rebase: You have unstaged changes` | Hay cambios sin commitear | `git stash && git pull --rebase && git stash pop` |
| Rama incorrecta | Se trabajó en `experimental` u otra rama | `git checkout examen-bigdata` |

---

## Failover

| Error | Causa | Solución |
|-------|-------|----------|
| Timeout / conexión caída al refrescar tras `delete-table` | DynamoDB tarda ~5-10s en propagar la eliminación. Las operaciones contra el endpoint muerto se cuelgan | `sleep 10` después del delete antes de refrescar. El código en `dynamodb_client.py` ya maneja `ConnectTimeoutError` y `ReadTimeoutError` como triggers de failover |
| App no funciona tras eliminar tabla primaria | La tabla de `us-west-2` también fue eliminada o nunca recibió datos (dual-write no funcionó) | Verificar dual-write: crear un curso desde la app, verificar que aparece en ambas regiones con `aws dynamodb scan` |
| `terraform destroy` no elimina todo | Recursos creados fuera de Terraform (manuales o de sesiones anteriores) | Ejecutar limpieza pre-vuelo completa (sección 3 de la guía) |
| IP de EC2 cambió y Ansible/SSH no conecta | Cada `terraform apply` asigna una IP pública nueva | Verificar con: `aws ec2 describe-instances --region us-east-1 --filters "Name=tag:Name,Values=Kimun-Web-Server" --query "Reservations[].Instances[].PublicIpAddress" --output text` |

---

## Comandos de diagnóstico

```bash
# EC2 viva
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'echo OK'

# Estado de servicios
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'sudo systemctl status kimun nginx'

# Branch + último commit
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'cd /opt/kimun && git branch --show-current && git log --oneline -1'

# Variables de entorno
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'sudo cat /etc/kimun.env'

# Datos en DynamoDB
aws dynamodb scan --table-name KimunData-Demo --region us-east-1 --max-items 3

# Bucket S3
aws s3 ls s3://kimundata-demo-analytics/exports/

# Logs de Django (últimas 50 líneas)
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'sudo journalctl -u kimun --no-pager -n 50'

# Limpiar caché de KPIs
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "sudo rm -f /opt/kimun/bigdata/cache/kpi_cache.json && sudo systemctl restart kimun"
```
