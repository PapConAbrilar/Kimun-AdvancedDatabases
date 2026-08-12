# Guía de Despliegue — Kimün + Big Data (AWS Learner Lab)

> **Examen: 19 agosto 2026** · **Branch: `examen-bigdata`** · **Presupuesto: $50 USD**
>
> **Para agentes IA del equipo:** esta guía es lineal y error-proof. Si un paso
> falla, la tabla de errores al final de cada sección tiene la solución exacta.

---

## 1. Setup inicial (primera vez por máquina)

```bash
git clone https://github.com/PapConAbrilar/Kimun-AdvancedDatabases.git
cd Kimun-AdvancedDatabases
git checkout examen-bigdata
```

---

## 2. Credenciales AWS (cada ~3 horas)

1. AWS Academy → Learner Lab → **Start Lab** → esperar verde
2. **AWS Details** → copiar las 3 variables

```bash
export AWS_ACCESS_KEY_ID=ASIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
export AWS_DEFAULT_REGION=us-east-1
aws sts get-caller-identity
```

| Error | Solución |
|-------|----------|
| `ExpiredToken` | Volver a copiar credenciales de AWS Details |
| `InvalidClientTokenId` | Re-copiar sin espacios extra |

---

## 3. 🧹 Limpieza pre-vuelo (SIEMPRE antes de Terraform)

```bash
# DynamoDB (ambas regiones)
aws dynamodb delete-table --table-name KimunData-Demo --region us-east-1 2>/dev/null
aws dynamodb delete-table --table-name KimunData-Demo --region us-west-2 2>/dev/null

# S3
aws s3 rb s3://kimundata-demo-analytics --force 2>/dev/null

# Glue + Athena
aws glue delete-database --name kimun_bigdata 2>/dev/null
aws athena delete-work-group --work-group kimun-bigdata --recursive-delete-option 2>/dev/null

# VPCs viejas (Learner Lab limita a ~5)
for vpc in $(aws ec2 describe-vpcs --region us-east-1 --query "Vpcs[?IsDefault==\`false\`].VpcId" --output text 2>/dev/null); do
    aws ec2 delete-vpc --vpc-id $vpc --region us-east-1 2>/dev/null
done

# EC2 huérfana
INSTANCE_ID=$(aws ec2 describe-instances --region us-east-1 \
    --filters "Name=tag:Name,Values=Kimun-Web-Server" "Name=instance-state-name,Values=running,stopped" \
    --query "Reservations[].Instances[].InstanceId" --output text 2>/dev/null)
[ -n "$INSTANCE_ID" ] && [ "$INSTANCE_ID" != "None" ] && aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region us-east-1

# Llave SSH (regenerar siempre)
aws ec2 delete-key-pair --key-name vockey --region us-east-1 2>/dev/null
ssh-keygen -t rsa -b 2048 -f ~/.ssh/vockey -N "" 2>/dev/null
aws ec2 import-key-pair --key-name vockey --public-key-material fileb://~/.ssh/vockey.pub --region us-east-1

# Estado local Terraform
rm -f terraform/terraform.tfstate terraform/terraform.tfstate.backup terraform/.terraform.lock.hcl
rm -rf terraform/.terraform/
ssh-keygen -R 0.0.0.0 2>/dev/null

echo "=== LIMPIEZA COMPLETA ==="
```

---

## 4. Terraform

```bash
cd terraform/
terraform init
terraform apply -auto-approve
```

**Anotar:** `ec2_public_ip = "X.X.X.X"`

| Error | Solución |
|-------|----------|
| `VpcLimitExceeded` | Ejecutar paso 3 completo (limpia VPCs viejas) |
| `BucketAlreadyExists` | `aws s3 rb s3://kimundata-demo-analytics --force` |
| `InvalidKeyPair.NotFound` | Paso 3 (regenera e importa llave SSH) |
| `InvalidKeyPair.Duplicate` | `aws ec2 delete-key-pair --key-name vockey --region us-east-1` y re-importar |

---

## 5. Ansible

```bash
cd ../ansible/
ssh-keygen -R IP_EC2 2>/dev/null
ansible-playbook -i "IP_EC2," playbook.yml -u ubuntu --private-key ~/.ssh/vockey
```

**Importante:** la coma después de la IP (`"IP,"`) es obligatoria.

| Error | Solución |
|-------|----------|
| `UNREACHABLE` / `Connection refused` | Esperar 60s (EC2 booteando) y reintentar |
| `Host key verification failed` | `ssh-keygen -R IP_EC2` |
| `Permission denied (publickey)` | Paso 3 (llave SSH no coincide) |
| `git clone` timeout | La EC2 no tiene internet → verificar IGW/route table |

---

## 6. Post-despliegue

```bash
# 6.1 Seed de datos enriquecido (5 cursos, enrolamientos, certificados, áreas/cargo)
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "sudo /opt/kimun/venv/bin/python3 /opt/kimun/manage.py seed_dynamodb"

# 6.2 Resetear admin (crea si no existe, actualiza si existe)
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "cd /opt/kimun && echo \"
from django.contrib.auth.hashers import make_password
from usuarios.repository import UsuarioRepository
user = UsuarioRepository.get_by_email('admin@kimun.cl')
if user:
    UsuarioRepository.update_user('admin@kimun.cl', {'password_hash': make_password('admin')})
    print('✅ Admin actualizado')
else:
    UsuarioRepository.create_user('admin@kimun.cl', make_password('admin'), rol='admin', nombre='Admin Kimün')
    print('✅ Admin creado')
\" | sudo /opt/kimun/venv/bin/python3 manage.py shell"
```

**Probar:** `http://IP_EC2/` → login `admin@kimun.cl` / `admin`

| Error | Solución |
|-------|----------|
| `sudo: venv/bin/python3: command not found` | Usar ruta completa: `/opt/kimun/venv/bin/python3` |
| `ImproperlyConfigured: settings are not configured` | Usar `manage.py shell` (no `python3 -c`) |
| Login no funciona | 6.2 de nuevo + `sudo systemctl restart kimun` |

---

## 7. Big Data — Pipeline completo

```bash
# 7.1 Exportar DynamoDB → S3
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "cd /opt/kimun && S3_ANALYTICS_BUCKET=kimundata-demo-analytics sudo -E /opt/kimun/venv/bin/python3 manage.py exportar_datos_s3 --solo-export"

# 7.2 Crear tablas Athena (automático, detecta fecha del export)
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "cd /opt/kimun && S3_ANALYTICS_BUCKET=kimundata-demo-analytics sudo -E /opt/kimun/venv/bin/python3 manage.py setup_athena_tables"

# 7.3 Ejecutar KPIs contra Athena
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "cd /opt/kimun && S3_ANALYTICS_BUCKET=kimundata-demo-analytics sudo -E /opt/kimun/venv/bin/python3 manage.py exportar_datos_s3 --solo-kpis"
```

Dashboard: `http://IP_EC2/reportes/bigdata/` (solo admin)

| Error | Solución |
|-------|----------|
| `Unknown command: setup_athena_tables` | No se redeployó. Ejecutar paso 5 (Ansible) de nuevo |
| `Unknown command: exportar_datos_s3` | Rama incorrecta. `git branch --show-current` en EC2 debe decir `examen-bigdata` |
| `NoSuchBucket` | `aws s3 mb s3://kimundata-demo-analytics --region us-east-1` |
| `TABLE_NOT_FOUND` en KPIs | Ejecutar paso 7.2 primero |
| Dashboard 500 error | `sudo rm -f /opt/kimun/bigdata/cache/kpi_cache.json && sudo systemctl restart kimun` |
| Dashboard sin gráficos | Ídem, borrar caché + restart |
| `scp: Permission denied` | Copiar a `/tmp/` primero, luego `sudo mv` al destino |

---

## 8. Failover (prueba del examen)

```bash
# 1. Mostrar app funcionando
# 2. Eliminar tabla primaria
aws dynamodb delete-table --table-name KimunData-Demo --region us-east-1
# 3. Refrescar navegador → app sigue viva (failover a us-west-2)
# 4. Restaurar
cd terraform/ && terraform apply -auto-approve
```

---

## 9. Destruir (OBLIGATORIO al terminar)

```bash
cd terraform/
terraform destroy -auto-approve
```

---

## 10. Resumen rápido post-despliegue

| KPIs | Fuente |
|------|--------|
| KPI 1 — Tasa de Completación | Athena (datos reales) |
| KPI 2 — Rendimiento Promedio | Athena (datos reales) |
| KPI 3 — Tasa de Certificación | Athena (datos reales) |
| KPI 4 — Distribución por Cargo | Athena (datos reales) |
| KPI 5 — Tiempo de Completación | Estático (datos de presentación) |

Para comprobar datos reales en Athena: `SELECT COUNT(*) FROM enrollments;` en la consola AWS.

---

## 11. Errores frecuentes (referencia rápida)

| Error | Sección |
|-------|---------|
| `ExpiredToken` | 2 |
| `VpcLimitExceeded` | 3 |
| `BucketAlreadyExists` / `InvalidKeyPair.*` | 3 (limpieza) |
| `UNREACHABLE` en Ansible | 5 |
| `Unknown command` | 5 (redeploy) o 7 (branch) |
| Login admin falla | 6.2 |
| `Permission denied` en scp | Copiar a `/tmp/` → `sudo mv` |
| Dashboard 500 / sin gráficos | 7 |
| `TABLE_NOT_FOUND` | 7.2 |
