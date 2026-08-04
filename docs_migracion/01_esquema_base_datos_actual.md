# Estructura Actual de la Base de Datos (Relacional)

Este documento describe el esquema relacional actual del proyecto Kimün, extraído directamente de los modelos de Django. Servirá como base para planificar la migración hacia modelos NoSQL.

## Módulo: `Usuarios`

### Tabla: `usuarios_areacargo` (Modelo: `AreaCargo`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `usuarios` | ForeignKey | Null, -> Usuario |
| `id` | BigAutoField | Primary Key, Unique |
| `nombre` | CharField | Unique |

### Tabla: `usuarios_usuario` (Modelo: `Usuario`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `logentry` | ForeignKey | Null, -> LogEntry |
| `recordatorios` | ForeignKey | Null, -> Recordatorio |
| `cursos_creados` | ForeignKey | Null, -> Curso |
| `inscripciones` | ForeignKey | Null, -> InscripcionCurso |
| `clases_completadas` | ForeignKey | Null, -> ClaseCompletado |
| `bancos_creados` | ForeignKey | Null, -> BancoPreguntas |
| `intentos_evaluacion` | ForeignKey | Null, -> IntentoEvaluacion |
| `certificados` | ForeignKey | Null, -> Certificado |
| `certificados_aprobados` | ForeignKey | Null, -> Certificado |
| `eventos_creados` | ForeignKey | Null, -> EventoCalendario |
| `tareas_creadas` | ForeignKey | Null, -> Tarea |
| `entregas` | ForeignKey | Null, -> EntregaTarea |
| `entregas_calificadas` | ForeignKey | Null, -> EntregaTarea |
| `anuncios_creados` | ForeignKey | Null, -> Anuncio |
| `anuncios_leidos` | ForeignKey | Null, -> LecturaAnuncio |
| `id` | BigAutoField | Primary Key, Unique |
| `password` | CharField |  |
| `last_login` | DateTimeField | Null |
| `is_superuser` | BooleanField |  |
| `username` | CharField | Unique |
| `first_name` | CharField |  |
| `last_name` | CharField |  |
| `email` | CharField |  |
| `is_staff` | BooleanField |  |
| `is_active` | BooleanField |  |
| `date_joined` | DateTimeField |  |
| `rut` | CharField | Unique |
| `rol` | CharField |  |
| `cargo` | ForeignKey | Null, -> AreaCargo |
| `groups` | ManyToManyField | -> Group |
| `user_permissions` | ManyToManyField | -> Permission |

### Tabla: `usuarios_recordatorio` (Modelo: `Recordatorio`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `id` | BigAutoField | Primary Key, Unique |
| `usuario` | ForeignKey | -> Usuario |
| `curso` | ForeignKey | -> Curso |
| `tipo` | CharField |  |
| `fecha_envio` | DateTimeField |  |

## Módulo: `Cursos`

### Tabla: `cursos_categoria` (Modelo: `Categoria`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `cursos` | ForeignKey | Null, -> Curso |
| `id` | BigAutoField | Primary Key, Unique |
| `nombre` | CharField | Unique |
| `color` | CharField |  |
| `descripcion` | TextField |  |

### Tabla: `cursos_curso` (Modelo: `Curso`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `recordatorios` | ForeignKey | Null, -> Recordatorio |
| `materiales` | ForeignKey | Null, -> Material |
| `inscripciones` | ForeignKey | Null, -> InscripcionCurso |
| `clases` | ForeignKey | Null, -> Clase |
| `bancos_preguntas` | ForeignKey | Null, -> BancoPreguntas |
| `evaluaciones` | ForeignKey | Null, -> Evaluacion |
| `certificados` | ForeignKey | Null, -> Certificado |
| `eventos_calendario` | ForeignKey | Null, -> EventoCalendario |
| `tareas` | ForeignKey | Null, -> Tarea |
| `anuncios` | ForeignKey | Null, -> Anuncio |
| `id` | BigAutoField | Primary Key, Unique |
| `titulo` | CharField |  |
| `descripcion` | TextField |  |
| `categoria` | ForeignKey | Null, -> Categoria |
| `docente_creador` | ForeignKey | -> Usuario |
| `estado` | CharField |  |
| `fecha_creacion` | DateTimeField |  |
| `fecha_limite` | DateTimeField | Null |

### Tabla: `cursos_material` (Modelo: `Material`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `id` | BigAutoField | Primary Key, Unique |
| `curso` | ForeignKey | -> Curso |
| `titulo` | CharField |  |
| `tipo` | CharField |  |
| `archivo` | FileField | Null |
| `url` | CharField | Null |

### Tabla: `cursos_inscripcioncurso` (Modelo: `InscripcionCurso`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `id` | BigAutoField | Primary Key, Unique |
| `usuario` | ForeignKey | -> Usuario |
| `curso` | ForeignKey | -> Curso |
| `estado` | CharField |  |
| `fecha_asignacion` | DateTimeField |  |

### Tabla: `cursos_clase` (Modelo: `Clase`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `completados` | ForeignKey | Null, -> ClaseCompletado |
| `id` | BigAutoField | Primary Key, Unique |
| `curso` | ForeignKey | -> Curso |
| `titulo` | CharField |  |
| `contenido` | TextField |  |
| `orden` | PositiveIntegerField |  |
| `fecha_creacion` | DateTimeField |  |
| `fecha_actualizacion` | DateTimeField |  |

### Tabla: `cursos_clasecompletado` (Modelo: `ClaseCompletado`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `id` | BigAutoField | Primary Key, Unique |
| `usuario` | ForeignKey | -> Usuario |
| `clase` | ForeignKey | -> Clase |
| `fecha_completado` | DateTimeField |  |

## Módulo: `Evaluaciones`

### Tabla: `evaluaciones_bancopreguntas` (Modelo: `BancoPreguntas`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `preguntas` | ForeignKey | Null, -> Pregunta |
| `id` | BigAutoField | Primary Key, Unique |
| `nombre` | CharField |  |
| `descripcion` | TextField |  |
| `curso` | ForeignKey | Null, -> Curso |
| `creado_por` | ForeignKey | -> Usuario |
| `es_publico` | BooleanField |  |
| `fecha_creacion` | DateTimeField |  |

### Tabla: `evaluaciones_evaluacion` (Modelo: `Evaluacion`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `preguntas` | ForeignKey | Null, -> Pregunta |
| `intentos` | ForeignKey | Null, -> IntentoEvaluacion |
| `eventos_calendario` | ForeignKey | Null, -> EventoCalendario |
| `id` | BigAutoField | Primary Key, Unique |
| `curso` | ForeignKey | -> Curso |
| `titulo` | CharField |  |
| `porcentaje_aprobacion` | IntegerField |  |
| `max_intentos` | IntegerField |  |
| `duracion_minutos` | IntegerField | Null |
| `preguntas_por_intento` | IntegerField | Null |

### Tabla: `evaluaciones_pregunta` (Modelo: `Pregunta`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `alternativas` | ForeignKey | Null, -> Alternativa |
| `id` | BigAutoField | Primary Key, Unique |
| `evaluacion` | ForeignKey | Null, -> Evaluacion |
| `banco` | ForeignKey | Null, -> BancoPreguntas |
| `texto` | TextField |  |

### Tabla: `evaluaciones_alternativa` (Modelo: `Alternativa`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `id` | BigAutoField | Primary Key, Unique |
| `pregunta` | ForeignKey | -> Pregunta |
| `texto` | CharField |  |
| `es_correcta` | BooleanField |  |

### Tabla: `evaluaciones_intentoevaluacion` (Modelo: `IntentoEvaluacion`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `id` | BigAutoField | Primary Key, Unique |
| `usuario` | ForeignKey | -> Usuario |
| `evaluacion` | ForeignKey | -> Evaluacion |
| `puntaje_obtenido` | IntegerField |  |
| `aprobado` | BooleanField |  |
| `fecha_intento` | DateTimeField |  |
| `hora_inicio` | DateTimeField | Null |
| `respuestas` | JSONField |  |

## Módulo: `Certificados`

### Tabla: `certificados_certificado` (Modelo: `Certificado`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `id` | BigAutoField | Primary Key, Unique |
| `usuario` | ForeignKey | -> Usuario |
| `curso` | ForeignKey | -> Curso |
| `codigo_verificacion` | UUIDField | Unique |
| `fecha_emision` | DateTimeField |  |
| `archivo_pdf` | FileField | Null |
| `estado` | CharField |  |
| `fecha_aprobacion` | DateTimeField | Null |
| `aprobado_por` | ForeignKey | Null, -> Usuario |

## Módulo: `Calendario`

### Tabla: `calendario_eventocalendario` (Modelo: `EventoCalendario`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `id` | BigAutoField | Primary Key, Unique |
| `titulo` | CharField |  |
| `descripcion` | TextField |  |
| `tipo` | CharField |  |
| `fecha_inicio` | DateTimeField |  |
| `fecha_fin` | DateTimeField |  |
| `curso` | ForeignKey | Null, -> Curso |
| `evaluacion` | ForeignKey | Null, -> Evaluacion |
| `creado_por` | ForeignKey | -> Usuario |
| `color` | CharField |  |

## Módulo: `Tareas`

### Tabla: `tareas_tarea` (Modelo: `Tarea`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `entregas` | ForeignKey | Null, -> EntregaTarea |
| `id` | BigAutoField | Primary Key, Unique |
| `curso` | ForeignKey | -> Curso |
| `titulo` | CharField |  |
| `descripcion` | TextField |  |
| `fecha_limite` | DateTimeField |  |
| `puntaje_maximo` | IntegerField |  |
| `creado_por` | ForeignKey | -> Usuario |
| `fecha_creacion` | DateTimeField |  |

### Tabla: `tareas_entregatarea` (Modelo: `EntregaTarea`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `id` | BigAutoField | Primary Key, Unique |
| `tarea` | ForeignKey | -> Tarea |
| `estudiante` | ForeignKey | -> Usuario |
| `archivo` | FileField |  |
| `comentario` | TextField |  |
| `fecha_entrega` | DateTimeField |  |
| `estado` | CharField |  |
| `puntaje_obtenido` | IntegerField | Null |
| `retroalimentacion` | TextField |  |
| `calificado_por` | ForeignKey | Null, -> Usuario |
| `fecha_calificacion` | DateTimeField | Null |

## Módulo: `Anuncios`

### Tabla: `anuncios_anuncio` (Modelo: `Anuncio`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `lecturas` | ForeignKey | Null, -> LecturaAnuncio |
| `id` | BigAutoField | Primary Key, Unique |
| `titulo` | CharField |  |
| `contenido` | TextField |  |
| `prioridad` | CharField |  |
| `curso` | ForeignKey | Null, -> Curso |
| `creado_por` | ForeignKey | -> Usuario |
| `publicado` | BooleanField |  |
| `fecha_publicacion` | DateTimeField | Null |
| `fecha_expiracion` | DateTimeField | Null |
| `fecha_creacion` | DateTimeField |  |

### Tabla: `anuncios_lecturaanuncio` (Modelo: `LecturaAnuncio`)
| Campo | Tipo de Dato | Relación / Detalles |
|-------|--------------|---------------------|
| `id` | BigAutoField | Primary Key, Unique |
| `anuncio` | ForeignKey | -> Anuncio |
| `usuario` | ForeignKey | -> Usuario |
| `fecha_lectura` | DateTimeField |  |

