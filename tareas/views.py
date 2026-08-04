from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q
from .models import Tarea, EntregaTarea
from .forms import TareaForm, EntregaTareaForm, CalificacionForm
from cursos.models import Curso, InscripcionCurso
from usuarios.decorators import docente_or_admin_required


@login_required
def tarea_list(request, curso_pk):
    curso = get_object_or_404(Curso, pk=curso_pk)
    tareas = curso.tareas.all()
    
    if request.user.rol == 'colaborador':
        inscripcion = InscripcionCurso.objects.filter(
            usuario=request.user, curso=curso
        ).first()
        if not inscripcion:
            messages.error(request, 'No estás inscrito en este curso.')
            return redirect('cursos:curso_detail', pk=curso_pk)
    
    context = {
        'curso': curso,
        'tareas': tareas,
    }
    return render(request, 'tareas/tarea_list.html', context)


@login_required
def tarea_detail(request, pk):
    tarea = get_object_or_404(Tarea, pk=pk)
    
    if request.user.rol == 'colaborador':
        inscripcion = InscripcionCurso.objects.filter(
            usuario=request.user, curso=tarea.curso
        ).first()
        if not inscripcion:
            messages.error(request, 'No estás inscrito en este curso.')
            return redirect('cursos:curso_detail', pk=tarea.curso.pk)

    entrega = None
    if request.user.rol == 'colaborador':
        entrega = EntregaTarea.objects.filter(
            tarea=tarea, estudiante=request.user
        ).first()
    
    context = {
        'tarea': tarea,
        'entrega': entrega,
    }
    return render(request, 'tareas/tarea_detail.html', context)


@login_required
@docente_or_admin_required
def tarea_create(request, curso_pk):
    curso = get_object_or_404(Curso, pk=curso_pk)
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes crear tareas en este curso.')
    
    if request.method == 'POST':
        form = TareaForm(request.POST)
        if form.is_valid():
            tarea = form.save(commit=False)
            tarea.curso = curso
            tarea.creado_por = request.user
            tarea.save()
            messages.success(request, f'Tarea "{tarea.titulo}" creada exitosamente.')
            return redirect('tareas:tarea_list', curso_pk=curso_pk)
    else:
        form = TareaForm()
    
    context = {
        'curso': curso,
        'form': form,
    }
    return render(request, 'tareas/tarea_form.html', context)


@login_required
@docente_or_admin_required
def tarea_edit(request, pk):
    tarea = get_object_or_404(Tarea, pk=pk)
    
    if request.user.rol == 'docente' and tarea.creado_por != request.user:
        return HttpResponseForbidden('No puedes editar esta tarea.')
    
    if request.method == 'POST':
        form = TareaForm(request.POST, instance=tarea)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tarea "{tarea.titulo}" actualizada.')
            return redirect('tareas:tarea_list', curso_pk=tarea.curso.pk)
    else:
        form = TareaForm(instance=tarea)
    
    context = {
        'tarea': tarea,
        'form': form,
    }
    return render(request, 'tareas/tarea_form.html', context)


@login_required
@docente_or_admin_required
def tarea_delete(request, pk):
    tarea = get_object_or_404(Tarea, pk=pk)
    
    if request.user.rol == 'docente' and tarea.creado_por != request.user:
        return HttpResponseForbidden('No puedes eliminar esta tarea.')
    
    curso_pk = tarea.curso.pk
    
    if request.method == 'POST':
        tarea.delete()
        messages.success(request, 'Tarea eliminada.')
        return redirect('tareas:tarea_list', curso_pk=curso_pk)
    
    return render(request, 'tareas/tarea_confirm_delete.html', {'tarea': tarea})


@login_required
def entrega_create(request, tarea_pk):
    tarea = get_object_or_404(Tarea, pk=tarea_pk)
    
    inscripcion = InscripcionCurso.objects.filter(
        usuario=request.user, curso=tarea.curso
    ).first()
    if not inscripcion:
        messages.error(request, 'No estás inscrito en este curso.')
        return redirect('cursos:curso_detail', pk=tarea.curso.pk)

    existing = EntregaTarea.objects.filter(
        tarea=tarea, estudiante=request.user
    ).first()
    if existing:
        messages.error(request, 'Ya entregaste esta tarea.')
        return redirect('tareas:tarea_detail', pk=tarea.pk)
    
    if request.method == 'POST':
        form = EntregaTareaForm(request.POST, request.FILES)
        if form.is_valid():
            entrega = form.save(commit=False)
            entrega.tarea = tarea
            entrega.estudiante = request.user
            entrega.save()
            messages.success(request, 'Tarea entregada exitosamente.')
            return redirect('tareas:tarea_detail', pk=tarea.pk)
    else:
        form = EntregaTareaForm()
    
    context = {
        'tarea': tarea,
        'form': form,
    }
    return render(request, 'tareas/entrega_form.html', context)


@login_required
@docente_or_admin_required
def entrega_grade(request, pk):
    entrega = get_object_or_404(EntregaTarea, pk=pk)
    
    if request.user.rol == 'docente' and entrega.tarea.creado_por != request.user:
        return HttpResponseForbidden('No puedes calificar esta entrega.')
    
    if request.method == 'POST':
        form = CalificacionForm(request.POST, instance=entrega)
        if form.is_valid():
            entrega = form.save(commit=False)
            entrega.estado = 'calificado'
            entrega.calificado_por = request.user
            from django.utils import timezone
            entrega.fecha_calificacion = timezone.now()
            entrega.save()
            messages.success(request, 'Entrega calificada.')
            return redirect('tareas:tarea_detail', pk=entrega.tarea.pk)
    else:
        form = CalificacionForm(instance=entrega)
    
    context = {
        'entrega': entrega,
        'form': form,
    }
    return render(request, 'tareas/entrega_grade.html', context)
