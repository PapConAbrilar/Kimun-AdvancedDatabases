# Justificación de la Elección Estratégica: Amazon DynamoDB

Tras analizar las opciones disponibles (MongoDB, DynamoDB y Cassandra) frente a los requisitos del proyecto "Advanced Databases Workshop" y la naturaleza de la plataforma Kimün, el equipo ha decidido seleccionar **Amazon DynamoDB** como la base de datos principal para la migración.

A continuación, se exponen los argumentos técnicos y operativos que sustentan esta decisión, destacando la sinergia con el ecosistema de AWS.

---

## 1. Integración Nativa y Centralización en el Ecosistema AWS

La mayor ventaja de seleccionar DynamoDB radica en la consolidación de toda la arquitectura bajo un mismo ecosistema (Amazon Web Services), lo que simplifica radicalmente las integraciones requeridas por el proyecto:

- **Cumplimiento directo de Big Data (AWS Athena):** El proyecto exige integración con herramientas analíticas como Athena o Hadoop. DynamoDB permite habilitar *Export to S3* de forma nativa sin afectar el rendimiento de la base de datos. Una vez que los datos de Kimün (por ejemplo, resultados de evaluaciones o logs de uso) están en S3, pueden ser catalogados por AWS Glue y consultados de inmediato usando **AWS Athena** (SQL estándar). Configurar esto con MongoDB o Cassandra requeriría construir pipelines ETL complejos.
- **Gestión Unificada de IAM:** El control de accesos entre el backend Django (corriendo en instancias EC2) y la base de datos se gestionará de manera segura mediante roles de IAM (Identity and Access Management), evitando tener credenciales hardcodeadas en los archivos de configuración.

## 2. Infraestructura como Código (IaC) Eficiente

La restricción del proyecto exige el uso de **Terraform** para levantar las instancias y provisión inicial.
- Terraform cuenta con el *AWS Provider*, considerado uno de los más maduros y robustos del mercado. 
- En un solo script de Terraform (`main.tf`), el equipo puede levantar: la red (VPC), las instancias de cómputo (EC2), los buckets analíticos (S3) y las tablas particionadas de DynamoDB, manteniendo la infraestructura 100% como código.

## 3. Delimitación Clara de Responsabilidades (Serverless vs Instancias)

El proyecto exige el uso de **Ansible, Chef o Puppet** para la configuración y mantención. Al elegir una base de datos administrada como DynamoDB:
- **Reducción de carga operativa (NoOps DB):** No necesitamos usar Ansible para mantener la base de datos (actualizar el sistema operativo, parchar seguridad de la DB o arreglar clústeres caídos), ya que AWS se encarga de esto.
- **Foco de Ansible en el Backend:** Ansible se utilizará exclusivamente en su entorno natural: configurar las máquinas virtuales EC2. Automatizará la instalación de Python, dependencias (Django), configuración de Gunicorn/Nginx, y la conexión hacia DynamoDB. Esto cumple el requisito del ramo pero orientándolo a entregar valor en la capa de aplicación, no en el mantenimiento tedioso de un motor de base de datos.

## 4. Estrategia de Distribución: Partición Administrada

La estrategia elegida para esta migración es la **Particionada (Partitioning/Sharding)**. 
- En MongoDB o Cassandra, diseñar e implementar una arquitectura particionada requiere un esfuerzo enorme (servidores de enrutamiento, configuración manual de llaves de partición, balanceo de clústeres).
- DynamoDB gestiona las particiones (sharding) "por debajo" de manera completamente automática basándose en la *Partition Key* (PK) definida (ej. `USER#<id>`). A medida que Kimün escale en volumen de voluntarios y evaluaciones, AWS distribuye la carga en distintos servidores físicos sin ninguna intervención humana, garantizando latencias consistentes de un solo dígito (milisegundos).

## Conclusión

La elección de **DynamoDB** no solo obedece a su altísimo rendimiento y escalabilidad, sino que **minimiza el roce arquitectónico**. Al centralizar el backend, la base de datos (DynamoDB) y la capa analítica (Athena + S3) dentro de AWS gestionado por Terraform, el equipo puede enfocar el 100% de su tiempo en el modelado de datos tipo *Single-Table Design* y en programar las integraciones en Django, en lugar de perder semanas intentando estabilizar clústeres autogestionados.
