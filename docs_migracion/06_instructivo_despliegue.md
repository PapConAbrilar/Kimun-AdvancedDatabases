# Instructivo de Despliegue en AWS Learner Lab

Este documento es el tutorial paso a paso para que el equipo despliegue la infraestructura de Kimün y configure el servidor automáticamente utilizando Infraestructura como Código (IaC).

**Nota:** Asegúrate de estar ejecutando estos pasos desde la consola temporal que te entrega AWS Academy (CloudShell) o desde tu terminal local con las credenciales temporales de Learner Lab correctamente configuradas en `~/.aws/credentials`.

---

## 1. Preparación de Llaves SSH (Solo la primera vez)

Para que Terraform pueda asignar una llave a la máquina EC2 y luego Ansible pueda conectarse a ella, necesitas generar y subir una llave pública a AWS.

1. Abre tu terminal y genera una llave (presiona Enter a todo):
   ```bash
   ssh-keygen -t rsa -b 2048 -f ~/.ssh/vockey
   ```
2. Si estás en tu PC local (no CloudShell), debes subir la llave pública a AWS. Ejecuta:
   ```bash
   aws ec2 import-key-pair --key-name "vockey" --public-key-material fileb://~/.ssh/vockey.pub --region us-east-1
   ```
*(Nota: Si AWS Learner Lab ya te dio una llave llamada `vockey`, asegúrate de tener el archivo `.pem` y guárdalo en `~/.ssh/vockey` con permisos `chmod 400`).*

---

## 2. Despliegue de Infraestructura con Terraform

Terraform leerá los archivos en la carpeta `terraform/` y creará la VPC, la EC2, y las Tablas Globales de DynamoDB.

1. Entra a la carpeta de Terraform:
   ```bash
   cd terraform/
   ```
2. Inicializa Terraform (descarga los plugins de AWS):
   ```bash
   terraform init
   ```
3. Revisa lo que Terraform va a crear:
   ```bash
   terraform plan
   ```
4. Despliega la infraestructura (y aprueba escribiendo `yes`):
   ```bash
   terraform apply
   ```
5. **¡Guarda la IP!** Cuando termine, la terminal mostrará algo como:
   ```text
   Outputs:
   ec2_public_ip = "54.234.xx.xx"
   dynamodb_table_name = "KimunData-Demo"
   ```
   *Copia esa IP Pública, la usarás en el siguiente paso.*

---

## 3. Configuración del Servidor con Ansible

Ansible se conectará por SSH a esa IP que te dio Terraform, actualizará Ubuntu, e instalará todo lo necesario para que Django funcione.

1. Retrocede a la carpeta principal y entra a `ansible/`:
   ```bash
   cd ../ansible/
   ```
2. Ejecuta el playbook pasando la IP de la máquina (reemplaza `TU_IP_AQUI` por la IP que te dio Terraform). *Atención a la coma al final de la IP, es obligatoria:*
   ```bash
   ansible-playbook -i "TU_IP_AQUI," playbook.yml -u ubuntu --private-key ~/.ssh/vockey
   ```
3. **Espera unos minutos.** Verás cómo Ansible ejecuta tarea por tarea (Instalando Nginx, clonando el repo, instalando Python, configurando Gunicorn).
4. Cuando termine (sin tareas en rojo/Failed), abre tu navegador web y entra a `http://TU_IP_AQUI`. ¡La plataforma Kimün debería estar viva!

---

## 4. Limpieza y FinOps (MUY IMPORTANTE)

Como estamos utilizando **DynamoDB Global Tables** (réplicas entre Estados Unidos y Sudamérica), AWS cobrará por transferencia de datos continuamente. Además, AWS Learner Lab tiene un presupuesto estricto de **$50 USD**.

**NUNCA dejes la infraestructura corriendo si no la estás usando activamente para probar o presentar.**

Para destruir **toda** la infraestructura creada de forma segura:

1. Vuelve a la carpeta de Terraform:
   ```bash
   cd ../terraform/
   ```
2. Ejecuta el comando de destrucción (y aprueba con `yes`):
   ```bash
   terraform destroy
   ```
3. Verifica que la consola te diga `Destroy complete!`. Con eso tus dólares están a salvo para el día siguiente.
