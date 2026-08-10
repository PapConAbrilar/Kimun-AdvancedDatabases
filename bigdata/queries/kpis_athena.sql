-- =============================================================================
-- Kimün Big Data — KPIs SQL para AWS Athena
-- =============================================================================
-- Cada consulta responde a un KPI definido para la ONG ALUMCO.
-- Los nombres de tabla asumen que se ejecutó el DDL de ddl_tablas_externas.sql.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- KPI 1: Tasa de Completación de Cursos
-- Pregunta: ¿Qué porcentaje del personal termina las capacitaciones asignadas?
-- Decisión:  Cursos con tasa < 50% necesitan rediseño o fechas límite más flexibles.
-- ---------------------------------------------------------------------------
-- QUERY:
SELECT
    e.cursotitulo AS curso,
    COUNT(*) AS total_inscritos,
    COUNT(CASE WHEN e.estado = 'completado' THEN 1 END) AS completados,
    ROUND(
        COUNT(CASE WHEN e.estado = 'completado' THEN 1 END) * 100.0 / COUNT(*), 1
    ) AS tasa_completacion_pct
FROM enrollments e
GROUP BY e.cursotitulo
ORDER BY tasa_completacion_pct DESC
LIMIT 20;


-- ---------------------------------------------------------------------------
-- KPI 2: Rendimiento Promedio por Curso
-- Pregunta: ¿En qué cursos el personal tiene más dificultades?
-- Decisión:  Cursos con promedio < 60% → reforzar instructores o material extra.
-- ---------------------------------------------------------------------------
-- QUERY:
SELECT
    ev.cursotitulo AS curso,
    ev.titulo AS evaluacion,
    COUNT(*) AS intentos,
    ROUND(AVG(CAST(a.puntaje_obtenido AS DOUBLE)), 1) AS promedio_puntaje,
    ROUND(
        COUNT(CASE WHEN a.aprobado = TRUE THEN 1 END) * 100.0 / COUNT(*), 1
    ) AS tasa_aprobacion_pct
FROM eval_attempts a
JOIN evaluations ev ON a.evaluacion_id = ev.id
GROUP BY ev.cursotitulo, ev.titulo
ORDER BY promedio_puntaje ASC
LIMIT 20;


-- ---------------------------------------------------------------------------
-- KPI 3: Tasa de Certificación
-- Pregunta: ¿Cuántos colaboradores obtuvieron su certificado?
-- Decisión:  Identificar cuellos de botella en el flujo de aprobación de certificados.
-- ---------------------------------------------------------------------------
-- QUERY:
SELECT
    estado,
    COUNT(*) AS total,
    COUNT(DISTINCT usuario_id) AS usuarios_unicos
FROM certificates
GROUP BY estado
ORDER BY total DESC;


-- ---------------------------------------------------------------------------
-- KPI 4: Distribución de Usuarios por Cargo/Área
-- Pregunta: ¿Qué áreas tienen más personal capacitado? ¿Dónde hay brechas?
-- Decisión:  Detectar residencias ELEAM con brechas para focalizar recursos.
-- ---------------------------------------------------------------------------
-- QUERY:
SELECT
    COALESCE(u.areacargo_nombre, 'Sin área asignada') AS area_cargo,
    COUNT(*) AS total_usuarios
FROM user_profiles u
WHERE u.rol = 'colaborador'
GROUP BY u.areacargo_nombre
ORDER BY total_usuarios DESC;


-- ---------------------------------------------------------------------------
-- KPI 5: Tiempo Promedio para Completar un Curso
-- Pregunta: ¿Cuánto tarda el personal en completar una capacitación?
-- Decisión:  Cursos con > 60 días promedio → extender plazos o rediseñar módulos.
-- ---------------------------------------------------------------------------
-- QUERY:
SELECT
    e.cursotitulo AS curso,
    COUNT(*) AS completados,
    ROUND(AVG(
        DATE_DIFF('day',
            CAST(e.fecha_asignacion AS TIMESTAMP),
            CAST(e.fecha_completado AS TIMESTAMP)
        )
    ), 1) AS dias_promedio_completacion
FROM enrollments e
WHERE e.estado = 'completado'
  AND e.fecha_asignacion IS NOT NULL
  AND e.fecha_completado IS NOT NULL
GROUP BY e.cursotitulo
ORDER BY dias_promedio_completacion ASC;
