# pyright: reportAttributeAccessIssue=false

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
from cursos.models import Curso, InscripcionCurso
from evaluaciones.models import Evaluacion, IntentoEvaluacion
from certificados.models import Certificado
from usuarios.models import Usuario
from usuarios.decorators import admin_required


def get_at_risk_students():
    """Returns list of dicts with user and risk reason."""
    from cursos.models import ClaseCompletado

    at_risk = []
    seven_days_ago = timezone.now() - timedelta(days=7)

    enrollments = InscripcionCurso.objects.filter(
        estado__in=['asignado', 'en_progreso']
    ).select_related('usuario', 'curso')

    for enrollment in enrollments:
        risk_reason = None

        if enrollment.fecha_asignacion < seven_days_ago:
            if not hasattr(enrollment, 'completado') or not enrollment.completado:
                has_progress = ClaseCompletado.objects.filter(
                    usuario=enrollment.usuario,
                    clase__curso=enrollment.curso
                ).exists()
                if not has_progress:
                    risk_reason = "Sin actividad en 7+ días"

        if enrollment.curso.fecha_limite:
            days_to_deadline = (enrollment.curso.fecha_limite - timezone.now()).days
            if days_to_deadline <= 7 and days_to_deadline > 0:
                has_passed = IntentoEvaluacion.objects.filter(
                    usuario=enrollment.usuario,
                    evaluacion__curso=enrollment.curso,
                    aprobado=True
                ).exists()
                if not has_passed:
                    risk_reason = f"Deadline en {days_to_deadline} días sin aprobar evaluaciones"

        failed_all = False
        if IntentoEvaluacion.objects.filter(
            usuario=enrollment.usuario,
            evaluacion__curso=enrollment.curso
        ).exists():
            all_attempts = IntentoEvaluacion.objects.filter(
                usuario=enrollment.usuario,
                evaluacion__curso=enrollment.curso
            )
            if all(attempt.aprobado == False for attempt in all_attempts):
                failed_all = True
                risk_reason = "Ha reprobado todas las evaluaciones"

        if risk_reason:
            ultima_actividad = enrollment.fecha_asignacion
            ultimo_progreso = ClaseCompletado.objects.filter(
                usuario=enrollment.usuario,
                clase__curso=enrollment.curso
            ).order_by('-fecha_completado').first()
            
            if ultimo_progreso and ultimo_progreso.fecha_completado > ultima_actividad:
                ultima_actividad = ultimo_progreso.fecha_completado

            at_risk.append({
                'usuario': enrollment.usuario,
                'estado': enrollment.get_estado_display(),
                'ultima_actividad': ultima_actividad.strftime("%d/%m/%Y %H:%M"),
                'riesgo': risk_reason
            })

    return at_risk


@login_required
@admin_required
def dashboard_reportes(request):
    total_usuarios = Usuario.objects.count()
    total_cursos = Curso.objects.count()
    total_inscripciones = InscripcionCurso.objects.count()
    total_certificados = Certificado.objects.count()
    
    cursos_con_mas_inscritos = Curso.objects.annotate(
        num_inscripciones=Count('inscripciones')
    ).order_by('-num_inscripciones')[:5]
    
    usuarios_por_rol = Usuario.objects.values('rol').annotate(count=Count('id'))
    
    inscripciones_por_estado = InscripcionCurso.objects.values('estado').annotate(count=Count('id'))
    
    evaluaciones_promedio = IntentoEvaluacion.objects.aggregate(promedio=Avg('puntaje_obtenido'))
    
    ultimas_inscripciones = InscripcionCurso.objects.select_related('usuario', 'curso').order_by('-fecha_asignacion')[:10]
    
    context = {
        'total_usuarios': total_usuarios,
        'total_cursos': total_cursos,
        'total_inscripciones': total_inscripciones,
        'total_certificados': total_certificados,
        'cursos_con_mas_inscritos': cursos_con_mas_inscritos,
        'usuarios_por_rol': usuarios_por_rol,
        'inscripciones_por_estado': inscripciones_por_estado,
        'promedio_evaluaciones': evaluaciones_promedio['promedio'] or 0,
        'ultimas_inscripciones': ultimas_inscripciones,
        'estudiantes_en_riesgo': get_at_risk_students(),
    }
    return render(request, 'reportes/dashboard.html', context)


@login_required
@admin_required
def reporte_curso(request, curso_pk):
    curso = get_object_or_404(Curso, pk=curso_pk)
    inscripciones = InscripcionCurso.objects.filter(curso=curso).select_related('usuario')
    
    evaluaciones = curso.evaluaciones.all()
    
    for inscripcion in inscripciones:
        inscripcion.intentos_count = 0
        inscripcion.aprobado = True
        for evaluacion in evaluaciones:
            ultimo = evaluacion.intentos.filter(usuario=inscripcion.usuario).order_by('-fecha_intento').first()
            if ultimo:
                inscripcion.intentos_count += 1
                if not ultimo.aprobado:
                    inscripcion.aprobado = False
    
    context = {
        'curso': curso,
        'inscripciones': inscripciones,
        'evaluaciones': evaluaciones,
    }
    return render(request, 'reportes/reporte_curso.html', context)


@login_required
@admin_required
def reporte_usuario(request, usuario_pk):
    usuario = get_object_or_404(Usuario, pk=usuario_pk)
    inscripciones = InscripcionCurso.objects.filter(usuario=usuario).select_related('curso')
    intentos = IntentoEvaluacion.objects.filter(usuario=usuario).select_related('evaluacion')
    certificados = Certificado.objects.filter(usuario=usuario).select_related('curso')
    
    context = {
        'usuario': usuario,
        'inscripciones': inscripciones,
        'intentos': intentos,
        'certificados': certificados,
    }
    return render(request, 'reportes/reporte_usuario.html', context)


@login_required
@admin_required
def progreso_heatmap(request):
    from cursos.models import Curso, InscripcionCurso, Clase, ClaseCompletado
    from evaluaciones.models import Evaluacion, IntentoEvaluacion
    
    curso_id = request.GET.get('curso')
    cursos = Curso.objects.all()
    
    heatmap_data = []
    
    if curso_id:
        curso = get_object_or_404(Curso, pk=curso_id)
        enrollments = InscripcionCurso.objects.filter(curso=curso).select_related('usuario')
        
        clases = list(curso.clases.all())
        evaluaciones = list(curso.evaluaciones.all())
        
        for enrollment in enrollments:
            student_data = {
                'usuario': enrollment.usuario,
                'estado': enrollment.estado,
                'items': []
            }
            
            for clase in clases:
                completado = ClaseCompletado.objects.filter(
                    usuario=enrollment.usuario,
                    clase=clase
                ).exists()
                student_data['items'].append({
                    'tipo': 'clase',
                    'titulo': clase.titulo,
                    'completado': completado
                })
            
            for evaluacion in evaluaciones:
                ultimo_intento = IntentoEvaluacion.objects.filter(
                    usuario=enrollment.usuario,
                    evaluacion=evaluacion
                ).order_by('-fecha_intento').first()
                
                student_data['items'].append({
                    'tipo': 'evaluacion',
                    'titulo': evaluacion.titulo,
                    'completado': ultimo_intento.aprobado if ultimo_intento else False,
                    'intentos': IntentoEvaluacion.objects.filter(
                        usuario=enrollment.usuario,
                        evaluacion=evaluacion
                    ).count()
                })
            
            heatmap_data.append(student_data)
    
    context = {
        'cursos': cursos,
        'curso_id': int(curso_id) if curso_id else None,
        'heatmap_data': heatmap_data,
    }
    return render(request, 'reportes/progreso_heatmap.html', context)

