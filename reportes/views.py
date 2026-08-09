from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from cursos.repository import InscripcionRepository, ProgresoClaseRepository
from evaluaciones.repository import EvaluacionRepository
from reportes.repository import ReporteRepository
from usuarios.decorators import admin_required
from usuarios.repository import UsuarioRepository


def get_at_risk_students():
    at_risk = []
    now = timezone.now()
    for user in UsuarioRepository.list_all(role="colaborador"):
        for enrollment in InscripcionRepository.list_by_user(
            user["email"], states={"asignado", "en_progreso"}
        ):
            reason = None
            progress = ProgresoClaseRepository.list_by_user(user["email"])
            if enrollment["fecha_asignacion"] < now - timedelta(days=7) and not progress:
                reason = "Sin actividad en 7+ días"
            deadline = enrollment["curso"].get("fecha_limite")
            attempts = [
                attempt
                for evaluation in EvaluacionRepository.list_by_course(enrollment["curso_id"])
                for attempt in EvaluacionRepository.get_intentos_por_usuario(
                    user["email"], evaluation["id"]
                )
            ]
            if deadline and 0 < (deadline - now).days <= 7 and not any(
                item.get("aprobado") for item in attempts
            ):
                reason = f"Fecha límite en {(deadline - now).days} días sin aprobar evaluaciones"
            if attempts and not any(item.get("aprobado") for item in attempts):
                reason = "Ha reprobado todas las evaluaciones"
            if reason:
                latest = max(
                    [enrollment["fecha_asignacion"]]
                    + [item["fecha_completado"] for item in progress],
                )
                at_risk.append(
                    {
                        "usuario": user,
                        "estado": enrollment["get_estado_display"],
                        "ultima_actividad": latest.strftime("%d/%m/%Y %H:%M"),
                        "riesgo": reason,
                    }
                )
    return at_risk


@login_required
@admin_required
def dashboard_reportes(request):
    context = ReporteRepository.dashboard()
    context["promedio_evaluaciones"] = context.pop("evaluaciones_promedio")
    context["estudiantes_en_riesgo"] = get_at_risk_students()
    return render(request, "reportes/dashboard.html", context)


@login_required
@admin_required
def reporte_curso(request, curso_pk):
    context = ReporteRepository.course_report(curso_pk)
    if not context["curso"]:
        raise Http404("Curso no encontrado.")
    return render(request, "reportes/reporte_curso.html", context)


@login_required
@admin_required
def reporte_usuario(request, usuario_pk):
    context = ReporteRepository.user_report(usuario_pk)
    if not context["usuario"]:
        raise Http404("Usuario no encontrado.")
    return render(request, "reportes/reporte_usuario.html", context)


@login_required
@admin_required
def progreso_heatmap(request):
    course_id = request.GET.get("curso")
    courses, course, classes, students = ReporteRepository.progress_heatmap(course_id)
    heatmap_data = []
    if course:
        evaluations = EvaluacionRepository.list_by_course(course_id)
        for student in students:
            items = [
                {
                    "tipo": "clase",
                    "titulo": class_item["titulo"],
                    "completado": student["progreso"][index],
                }
                for index, class_item in enumerate(classes)
            ]
            for evaluation in evaluations:
                attempts = EvaluacionRepository.get_intentos_por_usuario(
                    student["usuario"]["email"], evaluation["id"]
                )
                items.append(
                    {
                        "tipo": "evaluacion",
                        "titulo": evaluation["titulo"],
                        "completado": bool(attempts and attempts[0].get("aprobado")),
                        "intentos": len(attempts),
                    }
                )
            heatmap_data.append({"usuario": student["usuario"], "items": items})
    return render(
        request,
        "reportes/progreso_heatmap.html",
        {"cursos": courses, "curso_id": course_id, "heatmap_data": heatmap_data},
    )
