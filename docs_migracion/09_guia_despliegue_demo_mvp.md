# Guía de Despliegue para Demo MVP

Este documento contiene el procedimiento reproducible para levantar, presentar
y destruir el MVP NoSQL de Kimün en AWS Learner Lab. Complementa el instructivo
general `06_instructivo_despliegue.md` con el flujo exacto validado sobre la
rama `experimental`.

## 1. Alcance de la demostración

La demo presenta:

- infraestructura creada con Terraform;
- configuración automática de EC2 con Ansible;
- aplicación Django ejecutándose detrás de Gunicorn y Nginx;
- persistencia 100 % NoSQL en DynamoDB;
- dos tablas equivalentes en `us-east-1` y `us-west-2`;
- replicación por escritura dual desde la aplicación;
- failover automático hacia la región secundaria;
- autenticación, cursos, evaluaciones, tareas, certificados, calendario,
  anuncios y reportes operacionales.

La demo no incluye todavía el pipeline de Big Data con S3, Glue y Athena. Ese
trabajo se describe en `10_estado_actual_big_data.md`.

## 2. Arquitectura presentada

```text
Navegador
   |
   v
EC2 pública: Nginx -> Gunicorn -> Django
                              |
                              +-> DynamoDB us-east-1 (primaria)
                              |
                              +-> DynamoDB us-west-2 (réplica por software)
```

Terraform crea nueve recursos administrados:

- VPC;
- subred pública;
- Internet Gateway;
- tabla de rutas y asociación;
- Security Group para HTTP y SSH;
- instancia EC2 `t3.small` con `LabInstanceProfile`;
- tabla `KimunData-Demo` en `us-east-1`;
- tabla `KimunData-Demo` en `us-west-2`.

Las tablas usan `PK` y `SK` como clave primaria compuesta y el índice `GSI1`
con `GSI1PK` y `GSI1SK`.

## 3. Preparación previa

Realizar esta lista al menos 30 minutos antes de presentar:

1. Iniciar AWS Learner Lab.
2. Copiar las credenciales temporales nuevas a `~/.aws/credentials`.
3. Confirmar que se está trabajando sobre `experimental`.
4. Confirmar que `vockey` existe localmente y en EC2 Key Pairs de
   `us-east-1`.
5. Comprobar que Terraform, Ansible, AWS CLI y Git están instalados.
6. Revisar el presupuesto disponible del laboratorio.

Comandos de comprobación desde la raíz del repositorio:

```bash
git switch experimental
git pull --ff-only origin experimental
aws sts get-caller-identity
aws ec2 describe-key-pairs --region us-east-1 --key-names vockey
terraform -version
ansible-playbook --version
```

La llave privada debe tener permisos restrictivos:

```bash
chmod 400 ~/.ssh/vockey
```

### Advertencia sobre el estado de Terraform

Antes de aplicar, ejecutar:

```bash
terraform -chdir=terraform state list
aws ec2 describe-instances --region us-east-1
aws dynamodb list-tables --region us-east-1
aws dynamodb list-tables --region us-west-2
```

Si AWS muestra recursos del proyecto, pero Terraform informa que no existe un
estado, no se debe aplicar inmediatamente. Primero hay que importar los
recursos o eliminar el despliegue huérfano para evitar duplicados.

## 4. Despliegue desde cero

### 4.1 Crear la infraestructura

Desde la raíz del repositorio:

```bash
terraform -chdir=terraform init
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
terraform -chdir=terraform plan -out=kimun.tfplan
terraform -chdir=terraform apply kimun.tfplan
```

El plan esperado desde una cuenta vacía debe indicar:

```text
Plan: 9 to add, 0 to change, 0 to destroy.
```

Obtener la IP pública:

```bash
terraform -chdir=terraform output -raw ec2_public_ip
```

Esperar hasta que EC2 aparezca como `running` y pase sus comprobaciones de
estado.

### 4.2 Configurar la EC2

Reemplazar `IP_EC2` por el resultado anterior. La coma del inventario es
obligatoria:

```bash
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook \
  -i "IP_EC2," \
  ansible/playbook.yml \
  -u ubuntu \
  --private-key ~/.ssh/vockey \
  -e app_branch=experimental
```

El playbook:

- clona la rama indicada en `/opt/kimun`;
- crea el entorno virtual;
- instala dependencias;
- recolecta archivos estáticos;
- genera `/etc/kimun.env` con una clave privada persistente;
- configura y reinicia Gunicorn;
- configura y reinicia Nginx.

### 4.3 Cargar datos demostrativos

```bash
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook \
  -i "IP_EC2," \
  ansible/cargar_datos_demo.yml \
  -u ubuntu \
  --private-key ~/.ssh/vockey
```

La carga es idempotente: puede repetirse sin duplicar intentos de evaluación.
El conjunto actual crea:

- 1 administrador;
- 1 docente;
- 5 colaboradores;
- 3 cursos;
- 3 evaluaciones;
- 15 intentos de evaluación.

En una tabla vacía se esperan 28 ítems en cada región.

### 4.4 Verificar el despliegue

```bash
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook \
  -i "IP_EC2," \
  ansible/verificar_despliegue.yml \
  -u ubuntu \
  --private-key ~/.ssh/vockey
```

El resultado correcto informa:

- rama `experimental`;
- versión Git esperada;
- Gunicorn y Nginx activos;
- revisión de Django sin errores;
- HTTP 200 desde la EC2.

Verificar la réplica:

```bash
aws dynamodb scan \
  --region us-east-1 \
  --table-name KimunData-Demo \
  --select COUNT \
  --query Count

aws dynamodb scan \
  --region us-west-2 \
  --table-name KimunData-Demo \
  --select COUNT \
  --query Count
```

Ambos conteos deben coincidir.

## 5. Credenciales de demostración

Estas cuentas son exclusivamente académicas:

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@kimun.cl` | `mockhash123` |
| Docente | `profesor@kimun.cl` | `mockhash123` |
| Colaborador | `alumno1@kimun.cl` a `alumno5@kimun.cl` | `mockhash123` |

No reutilizar estas contraseñas en un entorno real.

## 6. Guion recomendado para la presentación

### Minuto 0 a 2: problema y solución

1. Explicar el problema de capacitación de ALUMCO.
2. Presentar Kimün como LMS.
3. Explicar por qué se reemplazó SQLite por DynamoDB y Single-Table Design.

### Minuto 2 a 4: infraestructura como código

1. Mostrar `terraform/main.tf`.
2. Mostrar la VPC, EC2 y las dos tablas en la consola AWS.
3. Mostrar `ansible/playbook.yml` y explicar el despliegue reproducible.
4. Ejecutar `terraform plan` para demostrar que no existe deriva.

### Minuto 4 a 7: aplicación NoSQL

1. Abrir `http://IP_EC2`.
2. Iniciar sesión como administrador.
3. Recorrer usuarios, cursos y reportes.
4. Iniciar sesión como docente y mostrar la gestión académica.
5. Iniciar sesión como colaborador y mostrar cursos y evaluaciones.

### Minuto 7 a 9: Single-Table y escritura dual

1. Crear un registro desde la aplicación, por ejemplo un usuario o anuncio.
2. Abrir el explorador de ítems de `KimunData-Demo` en `us-east-1`.
3. Identificar `PK`, `SK`, `GSI1PK`, `GSI1SK` y `entity_type`.
4. Abrir la misma tabla en `us-west-2` y mostrar el mismo registro.
5. Aclarar que Learner Lab impide la configuración usada por Global Tables
   nativas, por lo que la réplica se implementó con escritura dual en Django.

### Minuto 9 a 11: failover

Esta parte es destructiva y debe realizarse solo cuando el equipo esté listo:

1. Confirmar que ambas tablas tienen el mismo conteo.
2. Eliminar únicamente `KimunData-Demo` de `us-east-1`.
3. Esperar a que la tabla desaparezca.
4. Refrescar la aplicación y consultar datos existentes.
5. Explicar que el cliente detecta `ResourceNotFoundException`, descarta la
   tabla primaria en caché y continúa con `us-west-2`.

Durante la caída, las lecturas y escrituras principales pueden continuar en
Oregon. La réplica hacia Virginia registrará advertencias hasta que la tabla se
recree.

Si se necesita seguir trabajando después de la demo, ejecutar un nuevo
`terraform plan` y `terraform apply` para recrear la tabla primaria y volver a
cargar o sincronizar los datos.

### Minuto 11 a 12: cierre

1. Resumir escalabilidad, tolerancia a fallos y automatización.
2. Anunciar el trabajo analítico pendiente con Athena.
3. Recordar la destrucción obligatoria por FinOps.

## 7. Diagnóstico rápido

### AWS CLI informa credenciales inválidas

Las credenciales de Learner Lab expiraron. Reiniciar el laboratorio y copiar
el bloque completo, incluido `aws_session_token`.

### Terraform intenta crear recursos duplicados

Comparar `terraform state list` con la consola AWS. No aplicar hasta resolver
la diferencia.

### Ansible no puede conectarse

Comprobar:

- IP pública actual;
- estado `running` de EC2;
- puerto 22 permitido por el Security Group;
- existencia y permisos de `~/.ssh/vockey`;
- nombre `vockey` asociado a la instancia.

### La EC2 despliega una versión incorrecta

Ejecutar el playbook con:

```bash
-e app_branch=experimental
```

Luego usar `ansible/verificar_despliegue.yml` para consultar rama y commit.

### El sitio no responde

```bash
ssh -i ~/.ssh/vockey ubuntu@IP_EC2
sudo systemctl status kimun
sudo systemctl status nginx
sudo journalctl -u kimun -n 100 --no-pager
sudo tail -n 100 /var/log/nginx/error.log
```

### DynamoDB no muestra datos

1. Ejecutar el playbook de carga demostrativa.
2. Confirmar `LabInstanceProfile` en la EC2.
3. Revisar las regiones `us-east-1` y `us-west-2`.
4. Confirmar el nombre exacto `KimunData-Demo`.

## 8. Limpieza obligatoria

Después de la presentación, desde la raíz del repositorio:

```bash
terraform -chdir=terraform plan -destroy
terraform -chdir=terraform destroy
```

Confirmar escribiendo `yes`. Luego verificar:

```bash
terraform -chdir=terraform state list
aws ec2 describe-instances --region us-east-1 \
  --filters Name=tag:Name,Values=Kimun-Web-Server
aws dynamodb list-tables --region us-east-1
aws dynamodb list-tables --region us-west-2
```

El estado de Terraform debe quedar sin recursos administrados y AWS no debe
mostrar la EC2 ni las tablas del proyecto.

## 9. Limitaciones aceptadas del MVP

- El despliegue académico usa HTTP y no HTTPS.
- La EC2 no usa balanceador ni Auto Scaling para proteger el presupuesto.
- Los archivos locales desaparecen al destruir la EC2 si no se configuró
  Supabase Storage.
- La réplica es administrada por la aplicación y no por Global Tables nativas.
- El dashboard actual es operacional y calcula agregados desde repositorios;
  todavía no consulta Athena.

