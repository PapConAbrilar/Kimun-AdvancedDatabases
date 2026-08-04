from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.db.models import Q
from datetime import datetime, timedelta
import calendar as cal_module
from .models import EventoCalendario, TipoEvento
from usuarios.decorators import docente_or_admin_required


@login_required
def calendario_view(request):
    try:
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
    except (ValueError, TypeError):
        return HttpResponseBadRequest('Parámetros de fecha inválidos.')

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year + 1 if month == 12 else year

    # Calculate days in month and empty days before first day
    _, last_day = cal_module.monthrange(year, month)

    # Get the weekday of the first day (0=Monday, 6=Sunday)
    first_weekday = datetime(year, month, 1).weekday()

    # empty_days should be the number of empty cells before day 1
    # In the template, weekday 0 = Monday. If first_weekday is 0 (Monday), empty_days = 0
    # If first_weekday is 5 (Saturday), empty_days = 5 (Mon-Fri filled, then start Sat)
    empty_days = range(first_weekday)

    # days is a list of day numbers 1 to last_day
    days = list(range(1, last_day + 1))

    # today for highlighting
    today = datetime.now()

    # Get events for the month (existing code)
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month, last_day, 23, 59, 59)

    from cursos.models import Curso, InscripcionCurso

    if request.user.rol in ['admin', 'docente']:
        eventos = EventoCalendario.objects.filter(
            Q(fecha_inicio__gte=start_date) & Q(fecha_inicio__lte=end_date)
        ).select_related('curso', 'evaluacion').order_by('fecha_inicio')
        cursos = Curso.objects.all().order_by('titulo')
    else:
        enrolled_course_ids = InscripcionCurso.objects.filter(
            usuario=request.user
        ).values_list('curso_id', flat=True)
        eventos = EventoCalendario.objects.filter(
            Q(fecha_inicio__gte=start_date) & Q(fecha_inicio__lte=end_date),
            Q(curso_id__in=enrolled_course_ids) | Q(curso__isnull=True)
        ).select_related('curso', 'evaluacion').order_by('fecha_inicio')
        cursos = Curso.objects.filter(id__in=enrolled_course_ids).order_by('titulo')

    curso_id = request.GET.get('curso')
    if curso_id:
        try:
            curso_id_int = int(curso_id)
            eventos = eventos.filter(curso_id=curso_id_int)
        except ValueError:
            pass

    # Pass all required context variables
    context = {
        'eventos': eventos,
        'day_events': eventos,
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'month_name': cal_module.month_name[month],
        'empty_days': empty_days,
        'days': days,
        'today': today,
        'cursos': cursos,
        'curso_id': curso_id,
    }
    return render(request, 'calendario/calendario.html', context)


@login_required
def calendario_eventos(request):
    start = request.GET.get('start')
    end = request.GET.get('end')

    try:
        if start:
            start_date = datetime.fromisoformat(start)
        else:
            start_date = datetime.now().replace(day=1)

        if end:
            end_date = datetime.fromisoformat(end)
        else:
            end_date = start_date + timedelta(days=30)
    except (ValueError, TypeError):
        return HttpResponseBadRequest('Parámetros de fecha inválidos.')
    
    if request.user.rol in ['admin', 'docente']:
        eventos = EventoCalendario.objects.filter(
            Q(fecha_inicio__gte=start_date) & Q(fecha_inicio__lte=end_date)
        ).select_related('curso', 'evaluacion').order_by('fecha_inicio')
    else:
        from cursos.models import InscripcionCurso
        enrolled_course_ids = InscripcionCurso.objects.filter(
            usuario=request.user
        ).values_list('curso_id', flat=True)
        eventos = EventoCalendario.objects.filter(
            Q(fecha_inicio__gte=start_date) & Q(fecha_inicio__lte=end_date),
            Q(curso_id__in=enrolled_course_ids) | Q(curso__isnull=True)
        ).select_related('curso', 'evaluacion').order_by('fecha_inicio')
    
    return render(request, 'calendario/partials/eventos_list.html', {'eventos': eventos})


@login_required
@docente_or_admin_required
def evento_create(request):
    if request.method == 'POST':
        from .forms import EventoCalendarioForm
        form = EventoCalendarioForm(request.POST)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.creado_por = request.user
            evento.save()
            messages.success(request, f'Evento "{evento.titulo}" creado exitosamente.')
            return redirect('calendario:calendario')
    else:
        from .forms import EventoCalendarioForm
        form = EventoCalendarioForm()
    
    return render(request, 'calendario/evento_form.html', {'form': form, 'accion': 'crear'})


@login_required
@docente_or_admin_required
def evento_edit(request, pk):
    evento = get_object_or_404(EventoCalendario, pk=pk)
    
    if request.user.rol != 'admin' and evento.creado_por != request.user:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('No tienes permisos para editar este evento.')
    
    if request.method == 'POST':
        from .forms import EventoCalendarioForm
        form = EventoCalendarioForm(request.POST, instance=evento)
        if form.is_valid():
            form.save()
            messages.success(request, f'Evento "{evento.titulo}" actualizado.')
            return redirect('calendario:calendario')
    else:
        from .forms import EventoCalendarioForm
        form = EventoCalendarioForm(instance=evento)
    
    return render(request, 'calendario/evento_form.html', {'form': form, 'evento': evento, 'accion': 'editar'})


@login_required
@docente_or_admin_required
def evento_delete(request, pk):
    evento = get_object_or_404(EventoCalendario, pk=pk)
    
    if request.user.rol != 'admin' and evento.creado_por != request.user:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('No tienes permisos para eliminar este evento.')
    
    if request.method == 'POST':
        titulo = evento.titulo
        evento.delete()
        messages.success(request, f'Evento "{titulo}" eliminado.')
        return redirect('calendario:calendario')
    
    return render(request, 'calendario/evento_confirm_delete.html', {'evento': evento})


@login_required
def calendario_ical_export(request):
    start_date = datetime.now()
    end_date = start_date + timedelta(days=180)
    
    if request.user.rol in ['admin', 'docente']:
        eventos = EventoCalendario.objects.filter(
            Q(fecha_inicio__gte=start_date) & Q(fecha_inicio__lte=end_date)
        ).select_related('curso', 'evaluacion')
    else:
        from cursos.models import InscripcionCurso
        enrolled_course_ids = InscripcionCurso.objects.filter(
            usuario=request.user
        ).values_list('curso_id', flat=True)
        eventos = EventoCalendario.objects.filter(
            Q(fecha_inicio__gte=start_date) & Q(fecha_inicio__lte=end_date),
            Q(curso_id__in=enrolled_course_ids) | Q(curso__isnull=True)
        ).select_related('curso', 'evaluacion')
    
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Kimun//Training Platform//ES',
    ]
    
    for evento in eventos:
        lines.append('BEGIN:VEVENT')
        lines.append(f'UID:{evento.pk}@kimun')
        lines.append(f'DTSTART:{evento.fecha_inicio.strftime("%Y%m%dT%H%M%S")}')
        lines.append(f'DTEND:{evento.fecha_fin.strftime("%Y%m%dT%H%M%S")}')
        lines.append(f'SUMMARY:{evento.titulo}')
        lines.append(f'DESCRIPTION:{evento.descripcion}')
        lines.append('END:VEVENT')
    
    lines.append('END:VCALENDAR')
    
    response = HttpResponse('\r\n'.join(lines), content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename="kimun_eventos.ics"'
    return response
