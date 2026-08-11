# 10 — Troubleshooting: Errores Comunes y Soluciones

> **Para cualquier agente IA del equipo:** este documento cubre todos los
> errores encontrados durante el despliegue real en AWS Learner Lab. Si un
> paso falla, buscar aquí primero.

---

## Errores de credenciales AWS

| Error | Causa | Solución |
|-------|-------|----------|
| `ExpiredToken` | Credenciales temporales expiran cada ~3-4 horas | Ir a Learner Lab → AWS Details → copiar nuevas credenciales → re-ejecutar `export AWS_...` |
| `InvalidClientTokenId` | Token inválido o mal copiado | Re-copiar las 3 variables sin espacios extra |
| `AccessDenied` en S3 | Learner Lab bloquea políticas públicas de bucket | Ya está solucionado en `main.tf` (no usa bucket policy). Si persiste, ejecutar sección 3 de la guía de despliegue |

---

## Errores de Terraform

| Error | Causa | Solución |
|-------|-------|----------|
| `InvalidKeyPair.NotFound` | La llave SSH `vockey` no existe en AWS | Ejecutar el script de limpieza pre-vuelo (sección 3 de la guía) que regenera e importa la llave |
| `ResourceInUseException: Table already exists` | La tabla DynamoDB quedó de una sesión anterior | `aws dynamodb delete-table --table-name KimunData-Demo --region us-east-1` y mismo para `us-west-2` |
| `BucketAlreadyExists` | El bucket S3 ya existe de otra sesión | `aws s3 rb s3://kimumdata-demo-analytics --force` |
| `AlreadyExistsException: Database already exists` | La base de datos Glue ya existe | `aws glue delete-database --name kimun_bigdata` |
| `InvalidRequestException: WorkGroup is already created` | El workgroup de Athena ya existe | `aws athena delete-work-group --work-group kimun-bigdata --recursive-delete-option` |
| Warning: `Invalid Attribute Combination` en lifecycle | El provider AWS pide `filter {}` explícito | Ya está solucionado. Si aparece, verificar que `main.tf` tiene `filter {}` dentro de la rule del lifecycle |

---

## Errores de Ansible

| Error | Causa | Solución |
|-------|-------|----------|
| `UNREACHABLE` / `Connection refused` | La EC2 está booteando | Esperar 60 segundos y reintentar |
| `Host key verification failed` | La IP reutiliza una EC2 anterior con host key distinta | `ssh-keygen -R IP_EC2` |
| `Permission denied (publickey)` | La llave `~/.ssh/vockey` no coincide con la importada en AWS | Re-ejecutar el script de limpieza pre-vuelo (regenera la llave) |
| `git clone` timeout / falla | La EC2 no tiene acceso a internet o GitHub | Verificar que el Learner Lab tenga acceso a GitHub. Si no, hacer deploy manual con `scp` |
| Rama incorrecta desplegada | El playbook clonó la rama equivocada | SSH a EC2: `cd /opt/kimun && git checkout examen-bigdata && sudo systemctl restart kimun` |

---

## Errores de la aplicación

| Error | Causa | Solución |
|-------|-------|----------|
| Login `admin@kimun.cl` no funciona | La tabla DynamoDB se recreó vacía y el admin no existe, o la contraseña no coincide | Ejecutar el script de reset de admin (sección 6.2 de la guía de despliegue). Crea el usuario si no existe, actualiza si ya existe |
| Página en blanco después de login | Gunicorn no está corriendo o hay error 500 | `ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'sudo journalctl -u kimun --no-pager -n 50'` |
| `Unknown command: 'exportar_datos_s3'` | El código en la EC2 no tiene el módulo `bigdata` | La rama desplegada no es `examen-bigdata`. Verificar con `git branch --show-current` en `/opt/kimun/` |

---

## Errores de Big Data

| Error | Causa | Solución |
|-------|-------|----------|
| `NoSuchBucket` en `export_to_s3` | El bucket S3 no existe o el nombre no coincide | `aws s3 mb s3://kimumdata-demo-analytics --region us-east-1`. También verificar que `S3_ANALYTICS_BUCKET` esté en `/etc/kimun.env` |
| `TABLE_NOT_FOUND` en Athena | Las tablas externas no se han creado aún en Athena | Es normal. Ejecutar `bigdata/queries/ddl_tablas_externas.sql` en la consola Athena. Mientras tanto, el dashboard usa datos simulados |
| Dashboard sin gráficos | Chart.js no cargó antes de que el JS intentara crear los charts | Ya está solucionado (Chart.js carga sync antes del HTML). Si persiste: `ssh ... 'sudo systemctl restart kimun'` y recargar con Ctrl+Shift+R |
| Dashboard sin datos | El caché guardó resultados vacíos de una ejecución fallida de Athena | `ssh ... "sudo rm -f /opt/kimun/bigdata/cache/kpi_cache.json && sudo systemctl restart kimun"` |
| Error 403 en dashboard | Solo el rol `admin` puede acceder a `/reportes/bigdata/` | Login con `admin@kimun.cl` / `admin`. Otros roles no tienen permiso |

---

## Errores de Git

| Error | Causa | Solución |
|-------|-------|----------|
| `rejected ... (fetch first)` | Alguien más pusheó a la misma rama | `git stash && git pull origin examen-bigdata --rebase && git stash pop && git push` |
| `unmerged files` / conflicto | Conflicto en `terraform/.terraform.lock.hcl` | `git rm --cached terraform/.terraform.lock.hcl && git reset HEAD terraform/.terraform.lock.hcl` |
| Rama incorrecta | Se trabajó en `experimental` en vez de `examen-bigdata` | `git checkout examen-bigdata && git merge experimental` |

---

## Errores de Failover

| Error | Causa | Solución |
|-------|-------|----------|
| La app no funciona después de eliminar la tabla | La tabla de `us-west-2` también fue eliminada o nunca tuvo datos | Verificar que el dual-write funciona: crear un curso, verificar que aparece en ambas regiones |
| `terraform destroy` no elimina todo | Recursos creados manualmente fuera de Terraform | Usar el script de limpieza pre-vuelo para eliminarlos manualmente |

---

## Comandos de diagnóstico rápido

```bash
# ¿La EC2 responde?
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'echo OK'

# ¿Django está corriendo?
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'sudo systemctl status kimun'

# ¿Nginx está corriendo?
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'sudo systemctl status nginx'

# ¿Qué branch está desplegado?
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'cd /opt/kimun && git branch --show-current && git log --oneline -1'

# ¿Las variables de entorno están correctas?
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 'sudo cat /etc/kimun.env'

# ¿DynamoDB tiene datos?
aws dynamodb scan --table-name KimunData-Demo --region us-east-1 --max-items 5

# ¿El bucket S3 existe?
aws s3 ls s3://kimumdata-demo-analytics/

# Limpiar TODO y empezar de cero
# (ejecutar sección 3 completa de 06_instructivo_despliegue.md)
```
