# Migración NoSQL Completada

Este documento registra la continuación del trabajo pendiente descrito en
`07_estado_actual.md`. El documento 07 se conserva sin modificaciones como
registro del estado anterior.

## 1. Resultado

Kimün ejecuta sus flujos funcionales sobre DynamoDB y ya no necesita una base
de datos SQL. La configuración de SQLite fue reemplazada por el backend
ficticio de Django, que evita conexiones relacionales accidentales. Las
sesiones se mantienen en cookies firmadas y la identidad de cada usuario se
recupera desde DynamoDB mediante su correo electrónico.

Se confirmó además que el archivo `db.sqlite3` no está presente en el
repositorio de trabajo.

## 2. Trabajo realizado

### 2.1 Acceso a DynamoDB

- Se consolidaron las operaciones comunes en un repositorio base para el
  diseño Single-Table.
- El cliente centralizado admite lectura, escritura, eliminación, consultas
  por partición y consultas mediante `GSI1`.
- Las consultas recorren todas las páginas entregadas por DynamoDB.
- Las escrituras y eliminaciones se replican en las regiones primaria y
  secundaria.
- El cliente conmuta automáticamente desde `us-east-1` hacia `us-west-2`
  cuando detecta una falla recuperable en la región primaria.

### 2.2 Repositorios funcionales

Se implementaron o ampliaron repositorios NoSQL para:

- usuarios y áreas/cargos;
- categorías, cursos, materiales, clases, inscripciones y progreso;
- bancos de preguntas, evaluaciones, preguntas, alternativas e intentos;
- tareas y entregas;
- certificados;
- calendario;
- anuncios y lecturas;
- reportes y agregaciones.

Las entidades usan identificadores de texto compatibles con UUID y claves
compuestas del diseño Single-Table.

### 2.3 Autenticación y sesiones

- Se completó `DynamoDBAuthBackend` y el adaptador `DynamoDBUser`.
- Se agregó un middleware de autenticación que conserva el correo como
  identificador de sesión, sin intentar convertirlo a una clave SQL numérica.
- Se verifica el hash de sesión contra el hash de contraseña almacenado en
  DynamoDB.
- El inicio de sesión, el cierre de sesión y el cambio de contraseña ya no
  dependen del ORM.

### 2.4 Vistas, formularios, rutas y plantillas

- Todas las vistas funcionales de usuarios, cursos, evaluaciones, tareas,
  certificados, reportes, calendario y anuncios consumen repositorios NoSQL.
- Los `ModelForm` fueron reemplazados por formularios basados en diccionarios.
- Las rutas aceptan identificadores DynamoDB de texto.
- Se corrigió el orden de las rutas estáticas para evitar colisiones con los
  identificadores dinámicos.
- Las plantillas dejaron de utilizar métodos de `QuerySet`, relaciones ORM y
  propiedades de archivos de modelos.
- Se adaptaron los contextos de progreso, clases, evaluaciones, categorías,
  tareas, certificados y reportes.

### 2.5 Sincronización de calendario

Las señales del ORM fueron reemplazadas por sincronización explícita desde la
capa NoSQL. La creación, edición o eliminación de cursos, tareas, evaluaciones
y anuncios mantiene sus eventos de calendario asociados.

También se migró el comando `generar_eventos_calendario` para reconstruir
eventos desde DynamoDB cuando sea necesario.

### 2.6 Comandos de administración

Se migraron los comandos para:

- cargar datos demostrativos en DynamoDB;
- reconstruir eventos del calendario;
- identificar estudiantes en riesgo;
- enviar anuncios por correo;
- limpiar datos funcionales y recrear cargos.

El comando de limpieza exige el argumento explícito `--confirmar`.

### 2.7 Configuración y despliegue

- SQLite fue reemplazado por `django.db.backends.dummy`.
- Se retiraron la ruta y la aplicación de administración relacional.
- Se eliminó `psycopg2-binary` de las dependencias y se aseguró la instalación
  de `boto3`.
- `.env.example` contiene únicamente la configuración de Django, DynamoDB y
  almacenamiento de archivos.
- El almacenamiento usa Supabase Storage cuando existen sus credenciales y
  almacenamiento local en caso contrario.
- Ansible ya no ejecuta migraciones SQL.
- Ansible genera y conserva una clave secreta privada en `/etc/kimun.env` y
  configura Gunicorn con las regiones de DynamoDB.
- Nginx sirve archivos estáticos y archivos multimedia locales.
- Terraform usa `us-west-2` como región secundaria, conserva el archivo de
  bloqueo del proveedor e ignora estado y caché locales.

## 3. Validaciones ejecutadas

Las siguientes validaciones terminaron correctamente:

```bash
python manage.py check
python manage.py test kimun.data_access.tests_nosql
python -m compileall kimun usuarios cursos evaluaciones tareas certificados reportes calendario anuncios
terraform fmt -check -recursive
terraform -chdir=terraform validate
ansible-playbook --syntax-check ansible/playbook.yml
git diff --check
```

Resultados principales:

- 6 pruebas NoSQL aprobadas;
- autenticación real mediante correo y contraseña validada;
- navegación de colaborador y administración validada sin base de datos SQL;
- 58 plantillas compiladas correctamente;
- Django no intentó preparar una base de datos durante las pruebas;
- configuración de Terraform válida;
- sintaxis del playbook de Ansible válida.

Las pruebas usan una implementación DynamoDB en memoria y no consumen recursos
ni presupuesto de AWS Learner Lab.

## 4. Próximos pasos

La deuda técnica señalada en el documento 07 quedó resuelta. Antes de la
presentación corresponde realizar únicamente la verificación del entorno real:

1. Renovar las credenciales temporales de AWS Learner Lab.
2. Ejecutar `terraform plan` y revisar los recursos antes de aplicar cambios.
3. Desplegar con Terraform y Ansible siguiendo
   `06_instructivo_despliegue.md`.
4. Ejecutar `python manage.py seed_dynamodb` en la EC2 si se necesitan datos de
   demostración.
5. Probar inicio de sesión, escritura, réplica y failover con ambas tablas
   reales.
6. Destruir la infraestructura al finalizar la prueba para proteger el
   presupuesto del laboratorio.

Como limpieza opcional posterior a la evaluación, se pueden retirar los
archivos históricos de modelos, migraciones y pruebas relacionales. Estos
archivos se conservaron para mantener trazabilidad del sistema original, pero
no participan en el flujo de ejecución NoSQL validado en este documento.

Si la aplicación se publica fuera del entorno académico HTTP, también será
necesario habilitar HTTPS, cookies seguras y HSTS.
