# Justificación de la Elección Estratégica: Amazon DynamoDB

Tras analizar las opciones disponibles frente a los estrictos requisitos del proyecto "Advanced Databases Workshop", el equipo ha decidido seleccionar **Amazon DynamoDB** como la base de datos principal, migrando el **100% de la plataforma Kimün** hacia una arquitectura NoSQL pura.

A continuación, se exponen los argumentos técnicos y operativos que sustentan esta decisión, destacando la sinergia con el ecosistema de AWS y la estrategia avanzada para simular la "caída de nodos" exigida en la rúbrica.

---

## 1. Alta Disponibilidad Activo-Activo (Global Tables)

El requerimiento más desafiante del proyecto es demostrar la resiliencia de la arquitectura simulando la "caída de un nodo". Como DynamoDB es un servicio *Serverless* (AWS abstrae los servidores físicos subyacentes), no es posible apagar un nodo directamente.

Para superar este desafío con un nivel arquitectónico superior, implementaremos **DynamoDB Global Tables** (Tablas Globales).
- Esta característica crea una arquitectura **Activo-Activo Multi-Región**.
- **La Demostración:** El "Nodo 1" de nuestra base de datos estará en EE.UU. (ej. `us-east-1`) y el "Nodo 2" será una réplica exacta en Brasil (ej. `sa-east-1`). Para cumplir con el requerimiento de "botar un nodo", eliminaremos intencionalmente la tabla en la región principal. La aplicación Django estará programada con un failover automático que redirigirá las consultas a la región secundaria en milisegundos, demostrando tolerancia a fallos a escala continental.

## 2. 100% NoSQL y Topología de Red (VPC)

Para cumplir con la prohibición de esquemas híbridos, **todos** los datos de Kimün (usuarios, autenticación, roles, cursos, evaluaciones e intentos) serán almacenados en DynamoDB utilizando el patrón *Single-Table Design*.

Además, la arquitectura se desplegará bajo una estricta topología de red:
- Las instancias EC2 que corren la aplicación (Django) vivirán en **Subredes Públicas** de una VPC.
- El tráfico hacia la base de datos NoSQL se enrutará de forma segura y privada utilizando **VPC Gateway Endpoints** hacia DynamoDB, aislando los datos de la internet pública.

## 3. Integración Nativa para Big Data (AWS Athena)

El proyecto exige integración con herramientas analíticas de Big Data. DynamoDB permite habilitar *Export to S3* de forma nativa sin penalizar el rendimiento (WCU/RCU) de la base de datos operativa. 
Una vez que los datos crudos (ej. todos los intentos históricos de pruebas de los voluntarios) aterrizan en S3 en formato JSON/Parquet, AWS Glue generará el catálogo de datos para que **AWS Athena** (SQL Serverless) pueda consultarlos y alimentar los 5 KPIs del negocio exigidos para el examen.

## 4. Delimitación de Infraestructura y Automatización

- **Terraform (IaC):** Levantará la VPC, los Endpoints, los buckets de S3 y las Global Tables de DynamoDB en múltiples regiones.
- **Ansible (Configuration Management):** Al ser DynamoDB un motor administrado ("NoOps DB"), Ansible enfocará el 100% de su esfuerzo en aprovisionar las instancias EC2: instalar Python, descargar el repositorio, configurar Gunicorn/Nginx y parametrizar la aplicación para el Failover multi-región.

## Conclusión

La elección de **DynamoDB Global Tables** es la estrategia definitiva. Permite migrar todo el modelo relacional a NoSQL de alto rendimiento, se integra directamente con el pipeline de Big Data en S3/Athena, y eleva la prueba de resiliencia del certamen simulando un desastre de proporciones geográficas, garantizando una calificación sobresaliente.
