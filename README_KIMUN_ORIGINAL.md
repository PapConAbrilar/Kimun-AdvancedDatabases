# Kimün - Plataforma de Capacitación ALUMCO

Plataforma de capacitación interna para la ONG ALUMCO, dedicada a trabajar con adultos mayores en residencias ELEAM.

## Características

- **Gestión de usuarios** con 3 roles: Administrador, Docente, Colaborador
- **Gestión de cursos** con materiales (PDF) y videos
- **Evaluaciones** con corrección automática
- **Certificados** en PDF con código de verificación
- **Categorías** para organizar cursos
- **Fechas límite** con recordatorios automáticos
- **Diseño responsivo** compatible con móviles
- **Modo oscuro** integrado

## Requisitos

- Python 3.10+
- Django 4.2+
- Node.js (opcional, para compilar Tailwind CSS)

## Instalación Rápida

### 1. Clonar y Entrar al proyecto
```bash
cd /home/sebacc/Documents/UDD/Ingeniería\ de\ Software/Proyecto-Kimün
```

### 2. Activar entorno virtual
```bash
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install django weasyprint pillow
```

### 4. Configurar base de datos
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Ejecutar
```bash
python manage.py runserver
```

### 6. Acceder
Abre tu navegador en: `http://127.0.0.1:8000`

## Credenciales de Acceso

| Usuario | Contraseña | Rol |
|--------|-----------|-----|
| admin | admin123 | Administrador |
| (crear nuevo) | - | Docente / Colaborador |

## Roles de Usuario

### Administrador
- Gestionar usuarios (crear, editar, eliminar)
- Gestionar categorías de cursos
- Inscribir usuarios a cursos
- Emitir certificados
- Ver reportes de cumplimiento
- Acceso completo a todas las funciones

### Docente
- Crear y editar cursos propios
- Agregar materiales (PDF, videos)
- Crear evaluaciones
- Ver características de sus cursos
- No puede gestionar usuarios ni ver reportes

### Colaborador
- Ver cursos asignados
- Completar materiales
- Tomar evaluaciones
- Obtener certificados al aprobar
- Descargar certificados
- Ver progreso personal

## Estructura del Proyecto

```
kimun/
├── cursos/           # Gestión de cursos y categorías
├── usuarios/         # Usuarios y autenticación
├── evaluaciones/     # Evaluaciones y preguntas
├── certificados/     # Generación de certificados PDF
├── reportes/        # Reportes y estadísticas
├── templates/        # Plantillas HTML
├── static/          # CSS, JS, imágenes
└── kimun/           # Configuración Django
```

## Modelos Principales

| Modelo | Descripción |
|--------|-------------|
| Usuario | Usuarios del sistema (extiende AbstractUser) |
| Curso | Cursos de capacitación |
| Material | Archivos PDF o videos por curso |
| Evaluacion | Pruebas con preguntas y alternativas |
| InscripcionCurso | Relación usuario-curso con estado |
| Certificado | Certificados generados con código único |
| Categoria | Categorías para organizar cursos |
| Recordatorio | Control de recordatorios enviados |

## Estados de Inscripción

- **Asignado**: Usuario recibió el curso
- **En Progreso**: Usuario comenzó el curso
- **Completado**: Usuario apruebó todas las evaluaciones

## Configuración de Correo

Por defecto, los correos se muestran en la consola. Para configurar SMTP:

```python
# kimun/settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tu-email@gmail.com'
EMAIL_HOST_PASSWORD = 'tu-password'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
```

## Solución de Problemas

### No aparecen los estilos
```bash
# Verificar que Tailwind esté compilado
ls static/css/
```

### Error de base de datos
```bash
# Recrear base de datos
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Error al generar PDF (WeasyPrint)
```bash
# Instalar dependencias del sistema
# Ubuntu/Debian:
sudo apt-get install libcairo2 libpango-1.0-0 libgobject-2.0-0

# Mac:
brew install cairo pango libgobject
```

## Tecnologías Usadas

- **Backend**: Django 4.2+
- **Frontend**: Django Templates + Tailwind CSS
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **PDFs**: WeasyPrint + Pillow
- **Icons**: Bootstrap Icons

## Licencia

MIT License - Proyecto desarrollado para ONG ALUMCO

## Equipo

Desarrollado por equipo universitario para el ramo Ingeniería de Software

---

¿Necesitas ayuda? Revisa el código o contacta al equipo de desarrollo.

## Arquitectura

### Estructura del Proyecto
El sistema se organiza en 8 aplicaciones Django principales:
- `usuarios` — Gestión de usuarios, perfiles y autenticación (3 roles).
- `cursos` — Gestión de cursos, categorías y materiales de estudio.
- `evaluaciones` — Sistema de evaluaciones con corrección automática.
- `tareas` — Gestión de entregas y retroalimentación de tareas.
- `certificados` — Generación dinámica de certificados en formato PDF.
- `reportes` — Dashboard de estadísticas y reportes de cumplimiento.
- `calendario` — Sistema de calendario para eventos y fechas límite.
- `anuncios` — Sistema de anuncios globales y notificaciones.

### Tecnologías
- **Core**: Django 4.2+, Python 3.10+
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Frontend**: Tailwind CSS, Alpine.js, Bootstrap Icons
- **Visualización**: Chart.js (en reportes)
- **PDF**: WeasyPrint

### Sistema de Diseño
El proyecto utiliza un sistema de diseño basado en variables CSS centralizadas en `base.html`, soportando modo oscuro nativo mediante el atributo `data-theme="dark"`.

Variables principales:
- `--color-bg`: Color de fondo principal.
- `--color-surface`: Fondo de tarjetas y elementos de superficie.
- `--color-primary`: Color de marca principal.
- `--color-secondary`: Color secundario.
- `--color-accent`: Color de acento (naranjo).
- `--color-success`, `--color-warning`, `--color-danger`: Colores semánticos.
- `--color-text`, `--color-text-muted`: Colores para tipografía.

Adicionalmente, se cuenta con una librería de componentes en `static/css/kimun.css`.

### Ramas (Git Flow)
- `main`: Rama de producción y despliegue final.
- `stable`: Rama utilizada para demostraciones y QA.
- `development`: Rama principal de integración para nuevas características.

### Scripts de Herramientas
El directorio `tools/` contiene scripts temporales de debugging y utilidades de desarrollo que no deben utilizarse en entornos de producción.
