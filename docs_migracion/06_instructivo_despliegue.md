# Guía de Despliegue — Kimün + Big Data (AWS Learner Lab)

> **Examen: Advanced Databases Workshop — 19 agosto 2026**
> **Branch: `examen-bigdata`** · **Presupuesto: $50 USD**

Guía lineal. Cada paso incluye qué esperar y qué hacer si falla.

---

## 1. Setup inicial (una vez por máquina)

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

# Verificar
aws sts get-caller-identity
```

| Error | Qué hacer |
|-------|-----------|
| `ExpiredToken` | Volver a copiar credenciales de "AWS Details" |
| `InvalidClientTokenId` | Ídem — las credenciales expiraron |

---

## 3. Limpieza pre-vuelo (SIEMPRE ejecutar antes de Terraform)

Copia y pega TODO este bloque. Los `2>/dev/null` silencian errores de "no existe".

```bash
# --- DynamoDB (ambas regiones) ---
aws dynamodb delete-table --table-name KimunData-Demo --region us-east-1 2>/dev/null
aws dynamodb delete-table --table-name KimunData-Demo --region us-west-2 2>/dev/null
echo "✓ DynamoDB"

# --- S3 ---
aws s3 rb s3://kimumdata-demo-analytics --force 2>/dev/null
echo "✓ S3"

# --- Glue ---
aws glue delete-database --name kimun_bigdata 2>/dev/null
echo "✓ Glue"

# --- Athena ---
aws athena delete-work-group --work-group kimun-bigdata --recursive-delete-option 2>/dev/null
echo "✓ Athena"

# --- EC2 huérfana ---
INSTANCE_ID=$(aws ec2 describe-instances \
    --region us-east-1 \
    --filters "Name=tag:Name,Values=Kimun-Web-Server" "Name=instance-state-name,Values=running,stopped" \
    --query "Reservations[].Instances[].InstanceId" --output text 2>/dev/null)
if [ -n "$INSTANCE_ID" ] && [ "$INSTANCE_ID" != "None" ]; then
    aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region us-east-1
    echo "✓ EC2 (terminando instancia previa)"
fi

# --- Llave SSH (regenerar) ---
aws ec2 delete-key-pair --key-name vockey --region us-east-1 2>/dev/null
ssh-keygen -t rsa -b 2048 -f ~/.ssh/vockey -N "" 2>/dev/null
aws ec2 import-key-pair --key-name "vockey" \
    --public-key-material fileb://~/.ssh/vockey.pub \
    --region us-east-1
echo "✓ SSH"

# --- Estado local Terraform ---
rm -f terraform/terraform.tfstate terraform/terraform.tfstate.backup
rm -f terraform/.terraform.lock.hcl
rm -rf terraform/.terraform/
echo "✓ Estado Terraform local"

# --- Host key SSH vieja ---
ssh-keygen -R 0.0.0.0 2>/dev/null

echo ""
echo "═══════════════════════════════════"
echo "  LIMPIEZA COMPLETA — Listo para desplegar"
echo "═══════════════════════════════════"
```

---

## 4. Terraform (infraestructura)

```bash
cd terraform/
terraform init
terraform apply -auto-approve
```

**Output esperado:**
```
ec2_public_ip = "X.X.X.X"       ← ¡ANOTALA!
s3_analytics_bucket = "kimumdata-demo-analytics"
```

| Error | Qué hacer |
|-------|-----------|
| `ExpiredToken` | Paso 2 de nuevo |
| `InvalidKeyPair.NotFound` | Paso 3 de nuevo (la limpieza regenera la llave) |
| `BucketAlreadyExists` / `ResourceInUseException` / `AlreadyExistsException` | Paso 3 de nuevo |
| Warning: `Invalid Attribute Combination` (lifecycle) | Ya está arreglado en el código — ignorar si sale |

---

## 5. Ansible (configurar servidor)

```bash
cd ../ansible/

# Limpiar host key de la IP nueva
ssh-keygen -R IP_EC2 2>/dev/null

# Desplegar (IMPORTANTE: la coma después de la IP)
ansible-playbook -i "IP_EC2," playbook.yml \
    -u ubuntu --private-key ~/.ssh/vockey
```

| Error | Qué hacer |
|-------|-----------|
| `UNREACHABLE` / `Connection refused` | Esperar 60s (EC2 booteando) y reintentar |
| `Host key verification failed` | `ssh-keygen -R IP_EC2` y reintentar |
| `Permission denied (publickey)` | Paso 3 de nuevo |
| `git clone` timeout | EC2 sin internet → revisar si Learner Lab tiene acceso a GitHub |

---

## 6. Post-despliegue (datos + admin + verificaciones)

### 6.1 Cargar datos demo

```bash
ansible-playbook -i "IP_EC2," cargar_datos_demo.yml \
    -u ubuntu --private-key ~/.ssh/vockey
```

### 6.2 Resetear admin (si falla login)

```bash
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
    print('✅ Admin creado desde cero')
print('   Login: admin@kimun.cl / admin')
\" | sudo venv/bin/python3 manage.py shell"
```

### 6.3 Verificar que todo funciona

```bash
ansible-playbook -i "IP_EC2," verificar_despliegue.yml \
    -u ubuntu --private-key ~/.ssh/vockey
```

Acceder a `http://IP_EC2/` y probar:
- Login `admin@kimun.cl` / `admin` → dashboard admin
- Login `alumno1@kimun.cl` / `alumno` → vista colaborador con cursos

---

## 7. Big Data

### 7.1 Exportar datos a S3

```bash
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "cd /opt/kimun && S3_ANALYTICS_BUCKET=kimumdata-demo-analytics sudo -E venv/bin/python3 manage.py exportar_datos_s3"
```

**Output esperado:**
```
✔ Exportación completada: N items en M tipos
```

### 7.2 Ver dashboard

```bash
# Asegurarse que la caché vacía no bloquea los datos simulados
ssh -i ~/.ssh/vockey ubuntu@IP_EC2 \
    "sudo rm -f /opt/kimun/bigdata/cache/kpi_cache.json && sudo systemctl restart kimun"
```

Dashboard en: `http://IP_EC2/reportes/bigdata/` (solo admin)

Debe mostrar **5 tarjetas con gráficos Chart.js + tablas + decisiones de negocio**.

### 7.3 (Opcional) Crear tablas Athena para KPIs reales

1. Consola AWS → Athena → us-east-1 → database `kimun_bigdata`
2. Ejecutar `bigdata/queries/ddl_tablas_externas.sql` (reemplazar placeholders)
3. Re-ejecutar: `ssh ... sudo venv/bin/python3 manage.py exportar_datos_s3 --solo-kpis`
4. Recargar dashboard — ahora con datos reales de Athena

---

## 8. Prueba de failover (requisito examen)

```bash
# 1. App funcionando normalmente
# 2. Eliminar tabla primaria
aws dynamodb delete-table --table-name KimunData-Demo --region us-east-1

# 3. Refrescar navegador → ¡la app sigue funcionando! (failover a us-west-2)

# 4. Restaurar
cd terraform/ && terraform apply -auto-approve
```

---

## 9. Destruir todo (OBLIGATORIO al terminar)

```bash
cd terraform/
terraform destroy -auto-approve
```

---

## 10. Errores comunes y soluciones rápidas

| Error | Solución |
|-------|----------|
| `ExpiredToken` en cualquier paso | Sección 2: renovar credenciales |
| `NoSuchBucket` en export | Sección 3 + 4: limpiar y re-ejecutar Terraform. O crear manual: `aws s3 mb s3://kimumdata-demo-analytics --region us-east-1` |
| Login admin no funciona | Sección 6.2 |
| Dashboard sin gráficos | Sección 7.2 (borrar caché + restart) |
| Dashboard sin datos en tablas | Ejecutar Sección 6.1 (cargar datos demo) |
| `TABLE_NOT_FOUND` en Athena | Normal — las tablas no existen aún. El dashboard usa datos simulados como fallback |
| `UNREACHABLE` en Ansible | Esperar 60s. Si persiste: `ssh -i ~/.ssh/vockey ubuntu@IP_EC2` directo para ver si la EC2 responde |
| EC2 no accesible por SSH | El security group o la llave no coinciden → Sección 3 (limpieza regenera todo) |
| Rama incorrecta en EC2 | SSH y verificar: `git branch --show-current` en `/opt/kimun/`. Debe decir `examen-bigdata` |
