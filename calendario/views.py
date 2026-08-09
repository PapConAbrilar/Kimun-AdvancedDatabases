import calendar as calendar_module
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from calendario.forms import EventoCalendarioForm
from calendario.repository import CalendarioRepository
from cursos.repository import CursoRepository, InscripcionRepository
from usuarios.decorators import docente_or_admin_required


def _email(user):
    return user.email or user.username


def _required(value):
    if not value:
        raise Http404("Evento no encontrado.")
    return value


def _aware(value):
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


def _course_scope(user):
    if user.rol in {"admin", "docente"}:
        return None, CursoRepository.get_all_courses()
    enrollments = InscripcionRepository.list_by_user(_email(user))
    course_ids = [item["curso_id"] for item in enrollments]
    return course_ids, [item["curso"] for item in enrollments]


@login_required
def calendario_view(request):
    try:
        year = int(request.GET.get("year", datetime.now().year))
        month = int(request.GET.get("month", datetime.now().month))
        start = _aware(datetime(year, month, 1))
        last_day = calendar_module.monthrange(year, month)[1]
        end = _aware(datetime(year, month, last_day, 23, 59, 59))
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Parámetros de fecha inválidos.")
    course_ids, courses = _course_scope(request.user)
    selected_course = request.GET.get("curso")
    if selected_course:
        course_ids = [selected_course]
    events = CalendarioRepository.list_events(course_ids=course_ids, start=start, end=end)
    return render(
        request,
        "calendario/calendario.html",
        {
            "eventos": events,
            "day_events": events,
            "year": year,
            "month": month,
            "prev_month": month - 1 if month > 1 else 12,
            "prev_year": year if month > 1 else year - 1,
            "next_month": month + 1 if month < 12 else 1,
            "next_year": year + 1 if month == 12 else year,
            "month_name": calendar_module.month_name[month],
            "empty_days": range(datetime(year, month, 1).weekday()),
            "days": range(1, last_day + 1),
            "today": datetime.now(),
            "cursos": courses,
            "curso_id": selected_course,
        },
    )


@login_required
def calendario_eventos(request):
    try:
        start = datetime.fromisoformat(request.GET.get("start")) if request.GET.get("start") else datetime.now().replace(day=1)
        end = datetime.fromisoformat(request.GET.get("end")) if request.GET.get("end") else start + timedelta(days=30)
        start = _aware(start)
        end = _aware(end)
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Parámetros de fecha inválidos.")
    course_ids, _ = _course_scope(request.user)
    events = CalendarioRepository.list_events(course_ids=course_ids, start=start, end=end)
    return render(request, "calendario/partials/eventos_list.html", {"eventos": events})


@login_required
@docente_or_admin_required
def evento_create(request):
    courses = CursoRepository.get_all_courses()
    form = EventoCalendarioForm(request.POST or None, cursos=courses)
    if request.method == "POST" and form.is_valid():
        event = CalendarioRepository.save(
            {
                **form.cleaned_data,
                "curso_id": form.cleaned_data.get("curso", ""),
                "creado_por_id": _email(request.user),
            }
        )
        messages.success(request, f'Evento "{event["titulo"]}" creado exitosamente.')
        return redirect("calendario:calendario")
    return render(request, "calendario/evento_form.html", {"form": form, "accion": "crear"})


@login_required
@docente_or_admin_required
def evento_edit(request, pk):
    event = _required(CalendarioRepository.get_event(pk))
    if request.user.rol != "admin" and event.get("creado_por_id") != _email(request.user):
        return HttpResponseForbidden("No tienes permisos para editar este evento.")
    courses = CursoRepository.get_all_courses()
    initial = {**event, "curso": event.get("curso_id", "")}
    form = EventoCalendarioForm(request.POST or None, instance=initial, cursos=courses)
    if request.method == "POST" and form.is_valid():
        CalendarioRepository.save(
            {
                **form.cleaned_data,
                "curso_id": form.cleaned_data.get("curso", ""),
                "creado_por_id": event.get("creado_por_id"),
            },
            pk,
        )
        messages.success(request, "Evento actualizado.")
        return redirect("calendario:calendario")
    return render(
        request,
        "calendario/evento_form.html",
        {"form": form, "evento": event, "accion": "editar"},
    )


@login_required
@docente_or_admin_required
def evento_delete(request, pk):
    event = _required(CalendarioRepository.get_event(pk))
    if request.user.rol != "admin" and event.get("creado_por_id") != _email(request.user):
        return HttpResponseForbidden("No tienes permisos para eliminar este evento.")
    if request.method == "POST":
        CalendarioRepository.delete(pk)
        messages.success(request, "Evento eliminado.")
        return redirect("calendario:calendario")
    return render(request, "calendario/evento_confirm_delete.html", {"evento": event})


@login_required
def calendario_ical_export(request):
    course_ids, _ = _course_scope(request.user)
    events = CalendarioRepository.list_events(
        course_ids=course_ids,
        start=timezone.now(),
        end=timezone.now() + timedelta(days=180),
    )
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Kimun//Training Platform//ES"]
    for event in events:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f'UID:{event["id"]}@kimun',
                f'DTSTART:{event["fecha_inicio"]:%Y%m%dT%H%M%S}',
                f'DTEND:{event["fecha_fin"]:%Y%m%dT%H%M%S}',
                f'SUMMARY:{event["titulo"]}',
                f'DESCRIPTION:{event.get("descripcion", "")}',
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    response = HttpResponse("\r\n".join(lines), content_type="text/calendar")
    response["Content-Disposition"] = 'attachment; filename="kimun_eventos.ics"'
    return response
