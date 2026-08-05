# Modelado de Datos en DynamoDB (Single-Table Design)

Migrar desde una base de datos relacional (como PostgreSQL/SQLite) hacia DynamoDB requiere un cambio de paradigma profundo. En DynamoDB no existen los `JOINs`, por lo tanto, el diseño de la base de datos no se hace según las entidades abstractas (Normalización), sino que **se diseña exclusivamente basándose en los patrones de acceso** (Consultas).

Para el proyecto Kimün, utilizaremos el estándar de la industria para DynamoDB: **Single-Table Design** (Diseño de Tabla Única). Esto significa que Usuarios, Cursos, Evaluaciones e Inscripciones vivirán en la misma tabla física, diferenciados por sus llaves.

---

## 1. Patrones de Acceso a Resolver

Antes de diseñar, debemos listar qué consultas hace frecuentemente la aplicación Kimün:
1. Obtener el perfil de un Usuario.
2. Obtener todos los cursos en los que está inscrito un Usuario.
3. Obtener el contenido (Materiales y Evaluaciones) de un Curso específico.
4. Obtener todos los alumnos inscritos en un Curso específico (Consulta inversa).
5. Registrar y consultar los intentos de evaluación de un Usuario.

## 2. Estructura Base de la Tabla (Llaves)

Toda tabla en DynamoDB necesita una llave primaria compuesta por:
- **Partition Key (PK):** Determina en qué servidor físico de AWS se guarda el dato.
- **Sort Key (SK):** Permite ordenar y agrupar múltiples registros que comparten la misma PK.

### Nomenclatura Estándar
Para poder meter distintas entidades en la misma tabla, usaremos prefijos (ej. `USER#` o `COURSE#`).

## 3. Diseño de Entidades (The Single Table)

| Entidad | Partition Key (PK) | Sort Key (SK) | Atributos (Data JSON) |
|---------|-------------------|---------------|-----------------------|
| **Perfil/Auth** | `USER#<user_id>` | `PROFILE#<user_id>` | `nombre, email, password_hash, rol, area_cargo, is_active` |
| **Metadatos Curso** | `COURSE#<course_id>`| `METADATA#<course_id>` | `titulo, descripcion, categoria_id` |
| **Material de Curso** | `COURSE#<course_id>`| `MATERIAL#<material_id>`| `tipo (pdf/video), url, orden` |
| **Evaluación** | `COURSE#<course_id>`| `EVAL#<eval_id>` | `titulo, [array_de_preguntas_y_alternativas]` |
| **Inscripción** | `USER#<user_id>` | `COURSE#<course_id>` | `estado (Asignado/Completado), fecha_inscripcion` |
| **Intento Evaluación**| `USER#<user_id>` | `ATTEMPT#<eval_id>#<timestamp>` | `puntaje_obtenido, respuestas_json` |

### ¿Cómo resuelve esto los patrones de acceso?
- **Patrón 1 y 2 (Perfil y Cursos del Usuario):** Si hacemos una consulta a DynamoDB diciendo `Obtén todo donde PK == 'USER#123'`, Dynamo nos devolverá en una sola consulta el perfil del usuario (SK=`PROFILE#123`), todas sus inscripciones (SK=`COURSE#...`) y todos sus exámenes rendidos (SK=`ATTEMPT#...`). ¡Hicimos el equivalente a 3 `JOINs` masivos en milisegundos!
- **Patrón 3 (Contenido del Curso):** Si consultamos `PK == 'COURSE#456'`, obtendremos instantáneamente los metadatos del curso, todos sus PDFs/Videos y todas sus pruebas, listos para pintar en el frontend.

---

## 4. Índices Secundarios Globales (GSI)

El diseño anterior es perfecto, excepto por una cosa: **El Patrón 4 (Obtener todos los alumnos de un curso)**. 
Como las inscripciones tienen `PK=USER` y `SK=COURSE`, buscar por curso requeriría escanear toda la base de datos (muy costoso).

Para solucionar esto, crearemos un **Inverted Index (GSI1)**. Un Índice Secundario Global es básicamente una tabla copia que AWS mantiene sincronizada automáticamente, pero con las llaves invertidas.

**Configuración del GSI1:**
- **GSI1-PK:** Será la `SK` de la tabla principal.
- **GSI1-SK:** Será la `PK` de la tabla principal.

### ¿Cómo funciona el Inverted Index?
Si buscamos en el GSI1 donde `GSI1-PK == 'COURSE#456'`, DynamoDB nos devolverá automáticamente todos los `USER#<id>` (alumnos) que tienen el estado de "Inscripción" asociado a ese curso. Problema resuelto sin impacto de rendimiento.

---

## 5. Justificación frente al Taller de Advanced Databases

Este modelo demuestra un dominio avanzado de bases de datos NoSQL por las siguientes razones:
1. **Erradicación del Modelo Híbrido:** Al modelar la autenticación (Auth) y los perfiles dentro de la misma tabla operativa, se cumple el requerimiento del profesor de una arquitectura 100% NoSQL pura.
2. **Evita la Normalización Relacional:** Demuestra que el equipo entiende que en NoSQL el almacenamiento es barato pero el procesamiento es caro.
3. **Eficiencia de Costos (RCU/WCU):** Al usar *Single-Table Design*, se maximiza la cantidad de datos que se obtienen en una sola lectura.
4. **Resiliencia Multi-Región Nativa:** Al tener todo el estado de la aplicación en una sola tabla, configurar **Global Tables** para replicar los datos hacia una región secundaria ("Nodo 2") es trivial, garantizando que el *Failover* de la demostración funcione a la perfección sin pérdida de integridad referencial.
5. **Denormalización de Evaluaciones:** Al guardar el `array_de_preguntas` dentro del mismo ítem de la `EVAL#`, se elimina la necesidad de tener tablas separadas para Preguntas y Alternativas.
