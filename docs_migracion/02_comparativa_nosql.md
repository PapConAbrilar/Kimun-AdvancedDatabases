# Comparativa de Bases de Datos NoSQL para Kimün

Este documento analiza las ventajas y desventajas de utilizar **MongoDB**, **DynamoDB** o **Cassandra** para la migración del sistema LMS Kimün. El análisis se realiza considerando la estructura actual (usuarios, cursos, evaluaciones y reportes) y los requisitos del proyecto "Advanced Databases Workshop".

---

## 1. MongoDB (Orientada a Documentos)

**Tipo de estrategia ideal:** Particionada (Sharding) o Réplica.

MongoDB almacena datos en formato tipo JSON (BSON). Dado que Kimün es una plataforma educativa, muchas entidades pueden modelarse de forma natural como documentos jerárquicos.

### Ventajas (Pros)
- **Modelado Natural para el LMS:** Las `Evaluaciones` y sus `Preguntas` con `Alternativas` pueden guardarse en un solo documento anidado. Cuando el usuario abre una evaluación, se trae todo el documento de una vez, reduciendo la latencia de hacer múltiples *JOINs* (como ocurre actualmente en SQL).
- **Flexibilidad de Esquema:** Si a futuro la ONG ALUMCO decide agregar nuevos tipos de materiales o preguntas (ej. respuestas abiertas, audios), el esquema de MongoDB se adapta sin necesidad de migraciones pesadas.
- **Transición más suave desde Django:** Existen integraciones como *Djongo* o *MongoEngine* que facilitan conectar el backend actual de Django con MongoDB sin reescribir toda la lógica de la aplicación desde cero.

### Desventajas (Contras)
- **Manejo de Relaciones Complejas:** Kimün tiene modelos altamente relacionales (ej. `InscripcionCurso` vincula a un `Usuario` con un `Curso`). En MongoDB, esto implica tener referencias cruzadas o duplicar datos. Si se duplican, actualizar el nombre de un curso requeriría actualizar múltiples documentos de inscripción.
- **Complejidad de Sharding:** Configurar un clúster particionado (Sharding) en MongoDB requiere servidores de configuración y enrutadores (mongos), lo que aumenta la complejidad de la infraestructura automatizada mediante Ansible/Terraform.

---

## 2. Amazon DynamoDB (Clave-Valor / Wide-Column)

**Tipo de estrategia ideal:** Particionada (Particiones gestionadas automáticamente por AWS).

DynamoDB es un servicio totalmente administrado por AWS, diseñado para escalabilidad a cualquier nivel con latencias de milisegundos de un solo dígito.

### Ventajas (Pros)
- **Operación "Serverless":** Cumple con los requisitos Cloud. DynamoDB no requiere gestionar servidores.
  - *Nota sobre Ansible:* Al ser administrado, **no usas Ansible para la base de datos**. Sin embargo, puedes usar Terraform para crear las tablas de DynamoDB y las instancias EC2 del backend, y usar **Ansible** para configurar esas instancias EC2 (instalar Python, Django, Nginx), cumpliendo perfectamente con el requisito del ramo.
- **Resiliencia Multi-Región (Global Tables):** Permite cumplir con el requisito de "botar un nodo" simulando la caída de una región entera (ej. EE.UU) y demostrando el *Failover* automático hacia una tabla réplica en otra región (ej. Brasil) sin pérdida de servicio.
- **Alta Disponibilidad y Escalado:** Ideal para picos de tráfico. Si muchos voluntarios entran a dar una evaluación al mismo tiempo, DynamoDB escala los RCU/WCU (Read/Write Capacity Units) automáticamente sin degradar el rendimiento.
- **Single-Table Design:** Obliga a diseñar la base de datos basada en los patrones de acceso. Con un diseño de tabla única, se pueden obtener perfiles de usuarios, sus cursos y sus notas en una sola consulta muy eficiente.

### Desventajas (Contras)
- **Curva de Aprendizaje del Modelado:** Modelar un LMS en DynamoDB es complejo. Requiere conocer *todas* las consultas de la aplicación por adelantado (ej. "Obtener todos los cursos de un usuario", "Obtener los alumnos de un curso"). 
- **Consultas Ad-Hoc limitadas:** Si el administrador necesita reportes nuevos o filtros complejos, DynamoDB no es bueno para eso a menos que se usen Índices Secundarios Globales (GSI), lo cual duplica costos, o se exporten los datos a **AWS Athena** (lo cual, irónicamente, es un requisito del proyecto, por lo que podría ser una excelente justificación arquitectónica).

---

## 3. Apache Cassandra (Wide-Column Store)

**Tipo de estrategia ideal:** Federada (Multi-Datacenter) o Particionada (Peer-to-Peer).

Cassandra es una base de datos distribuida masivamente escalable diseñada para manejar grandes cantidades de datos en muchos servidores sin puntos únicos de falla.

### Ventajas (Pros)
- **Escalabilidad y Escrituras Ultra Rápidas:** Cassandra está optimizada para la escritura. Si Kimün planea guardar logs detallados de interacción de los adultos mayores en la plataforma (telemetría, clicks, tiempo por página para análisis de usabilidad), Cassandra puede ingerir esos datos masivos sin problema.
- **Estrategia Federada Natural:** Si ALUMCO se expande a nivel nacional o internacional, Cassandra permite replicar datos a través de múltiples Data Centers geográficos de forma nativa.
- **Integración con Hadoop:** Cassandra se integra maravillosamente con **Hadoop/Spark** (requisito de Big Data del proyecto) para correr procesos analíticos pesados sobre los logs de estudiantes en batch sin afectar el rendimiento de la aplicación en tiempo real.

### Desventajas (Contras)
- **Sobredimensionado (Overkill):** Para la escala actual de Kimün (un LMS interno para una ONG), Cassandra es excesivamente complejo y requiere un clúster de al menos 3 nodos para que tenga sentido.
- **Mantenimiento (Ansible/Puppet):** Cassandra requiere mantenimiento manual (reparaciones de nodos, compactación, manejo de *tombstones*). Obligaría a un uso intensivo de Ansible/Chef, lo cual cumple el requisito del ramo, pero aumenta radicalmente el trabajo del equipo.
- **Rigidez Total en Consultas:** Las tablas en Cassandra se modelan estrictamente según la consulta (Query-First Design). No hay JOINs y no hay búsquedas secundarias flexibles sin penalizar fuertemente el rendimiento.

---

## Conclusión y Elección Definitiva

Tras analizar los requerimientos estrictos del "Advanced Databases Workshop" (100% NoSQL, topología VPC, análisis S3/Athena y la capacidad de "apagar un nodo" para probar resiliencia), **Amazon DynamoDB** es la elección oficial del proyecto. 

Para satisfacer la prueba de caída de nodos (siendo DynamoDB *Serverless*), se utilizarán **DynamoDB Global Tables** (Tablas Globales Multi-Región). Esto permitirá demostrar la tolerancia a fallos eliminando la base de datos en una región en tiempo real, validando que el sistema redirige el tráfico hacia la réplica geográfica sin interrupción del servicio, demostrando un dominio arquitectónico de nivel superior.
