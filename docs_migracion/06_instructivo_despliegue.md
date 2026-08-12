# Guía de Despliegue — Kimün + Big Data (AWS Learner Lab)

> **Examen: 19 agosto 2026** · **Branch: `examen-bigdata`** · **Presupuesto: $50 USD**

---

## 1. Setup inicial (primera vez por máquina)

```bash
git clone https://github.com/PapConAbrilar/Kimun-AdvancedDatabases.git
cd Kimun-AdvancedDatabases
git checkout examen-bigdata
```

---

## 2. Credenciales AWS (cada ~3 horas)

1. AWS Academy → Learner Lab → Start Lab → esperar verde
2. AWS Details → copiar las 3 variables

```bash
export AWS_ACCESS_KEY_ID=ASIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
export AWS_DEFAULT_REGION=us-east-1
aws sts get-caller-identity
```

| Error | Solución |
|-------|----------|
| `ExpiredToken` | Repetir paso 2 desde AWS Details |

---

## 3. Limpieza pre-vuelo (ejecutar SIEMPRE antes de Terraform)

```bash
aws dynamodb delete-table --table-name KimunData-Demo --region us-east-1 2>/dev/null
aws dynamodb delete-table --table-name KimunData-Demo --region us-west-2 2>/dev/null
aws s3 rb s3://kimundata-demo-analytics --force 2>/dev/null
aws glue delete-database --name kimun_bigdata 2>/dev/null
aws athena delete-work-group --work-group kimun-bigdata --recursive-delete-option 2>/dev/null

# VPCs viejas
for vpc in $(aws ec2 describe-vpcs --region us-east-1 --query "Vpcs[?IsDefault==\`false\`].VpcId" --output text 2>/dev/null); do
    aws ec2 delete-vpc --vpc-id $vpc --region us-east-1 2>/dev/null
done

# EC2 huérfana
INSTANCE_ID=$(aws ec2 describe-instances --region us-east-1 \
    --filters "Name=tag:Name,Values=Kimun-Web-Server" "Name=instance-state-name,Values=running,stopped" \
    --query "Reservations[].Instances[].InstanceId" --output text 2>/dev/null)
[ -n "$INSTANCE_ID" ] && [ "$INSTANCE_ID" != "None" ] && aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region us-east-1

# Llave SSH
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
| `VpcLimitExceeded` | Paso 3: borrar VPCs viejas |
| `BucketAlreadyExists` | `aws s3 rb s3://kimundata-demo-analytics --force` |
| `InvalidKeyPair.NotFound` | Paso 3 (regenera llave) |

---

## 5. Ansible

```bash
cd ../ansible/
ssh-keygen -R IP_EC2 2>/dev/null
ansible-playbook -i "IP_EC2," playbook.yml -u ubuntu --private-key ~/.ssh/vockey
```

---

## 6. Post-despliegue

```bash
# Cargar datos demo
ansible-playbook -i "IP_EC2," cargar_datos_demo.yml -u ubuntu --private-key ~/.ssh/vockey

# Resetear admin
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
\" | sudo venv/bin/python3 manage.py shell"
```

**Probar:** `http://IP_EC2/` → login `admin@kimun.cl` / `admin`

---

## 7. Big Data — Pipeline completo (3 pasos)

```bash
# 7.1 Exportar DynamoDB → S3
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "cd /opt/kimun && S3_ANALYTICS_BUCKET=kimundata-demo-analytics sudo -E venv/bin/python3 manage.py exportar_datos_s3 --solo-export"
# Esperado: ✔ Exportación completada: N items en M tipos

# 7.2 Crear tablas externas en Athena
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "cd /opt/kimun && S3_ANALYTICS_BUCKET=kimundata-demo-analytics sudo -E venv/bin/python3 manage.py setup_athena_tables"
# Esperado: ✅ user_profiles, ✅ course_metadata, ✅ enrollments, ✅ evaluations, ✅ eval_attempts, ✅ certificates

# 7.3 Ejecutar KPIs contra Athena (datos REALES)
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "cd /opt/kimun && S3_ANALYTICS_BUCKET=kimundata-demo-analytics sudo -E venv/bin/python3 manage.py exportar_datos_s3 --solo-kpis"
# Esperado: SIN errores TABLE_NOT_FOUND. KPIs cacheados correctamente.

# 7.4 Dashboard
# http://IP_EC2/reportes/bigdata/ → 5 gráficos con datos reales
```

---

## 8. Failover

```bash
# 1. App funcionando normalmente
# 2. Eliminar tabla primaria
aws dynamodb delete-table --table-name KimunData-Demo --region us-east-1
# 3. Refrescar navegador → app sigue funcionando (failover a us-west-2)
# 4. Restaurar
cd terraform/ && terraform apply -auto-approve
```

---

## 9. Destruir (OBLIGATORIO)

```bash
cd terraform/
terraform destroy -auto-approve
```

---

## 10. Errores rápidos

| Error | Solución |
|-------|----------|
| `ExpiredToken` | Paso 2 |
| `Unknown command: setup_athena_tables` | No se redeployó. Ejecutar paso 5 de nuevo |
| `TABLE_NOT_FOUND` en KPIs | Ejecutar paso 7.2 primero |
| Login admin falla | Paso 6 (resetear admin) |
| Dashboard sin gráficos | `ssh ... "sudo rm -f /opt/kimun/bigdata/cache/kpi_cache.json && sudo systemctl restart kimun"` |
| Dashboard sin datos | Ejecutar paso 6 (cargar datos demo) |
