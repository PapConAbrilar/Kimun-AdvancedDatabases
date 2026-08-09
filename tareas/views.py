from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from calendario.repository import CalendarioRepository
from cursos.repository import CursoRepository, InscripcionRepository
from tareas.forms import CalificacionForm, EntregaTareaForm, TareaForm
from tareas.repository import EntregaTareaRepository, TareaRepository
from usuarios.decorators import docente_or_admin_required


def _email(user):
    return user.email or user.username


def _required(value, message):
    if not value:
        raise Http404(message)
    return value


def _can_manage(user, course):
    return user.rol == "admin" or (
        user.rol == "docente" and course.get("docente_creador_id") == _email(user)
    )


@login_required
def tarea_list(request, curso_pk):
    course = _required(CursoRepository.get_course(curso_pk), "Curso no encontrado.")
    if not _can_manage(request.user, course):
        if not InscripcionRepository.get(_email(request.user), curso_pk):
            return HttpResponseForbidden("Debes estar inscrito en este curso.")
    return render(
        request,
        "tareas/tarea_list.html",
        {"curso": course, "tareas": TareaRepository.list_by_course(curso_pk)},
    )


@login_required
def tarea_detail(request, pk):
    task = _required(TareaRepository.get_task(pk), "Tarea no encontrada.")
    course = task["curso"]
    email = _email(request.user)
    can_manage = _can_manage(request.user, course)
    if not can_manage and not InscripcionRepository.get(email, course["id"]):
        return HttpResponseForbidden("Debes estar inscrito en este curso.")
    submissions = EntregaTareaRepository.list_by_task(pk) if can_manage else []
    submission = None if can_manage else EntregaTareaRepository.get(pk, email)
    for item in submissions + ([submission] if submission else []):
        if item.get("archivo"):
            try:
                item["archivo_url"] = default_storage.url(item["archivo"])
            except Exception:
                item["archivo_url"] = ""
    return render(
        request,
        "tareas/tarea_detail.html",
        {
            "tarea": task,
            "entregas": submissions,
            "entrega": submission,
            "puede_gestionar": can_manage,
            "puede_entregar": not can_manage and timezone.now() <= task["fecha_limite"],
        },
    )


@login_required
@docente_or_admin_required
def tarea_create(request, curso_pk):
    course = _required(CursoRepository.get_course(curso_pk), "Curso no encontrado.")
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No tienes permisos para crear tareas.")
    form = TareaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = TareaRepository.save_task(
            {
                **form.cleaned_data,
                "curso_id": str(curso_pk),
                "creado_por_id": _email(request.user),
            }
        )
        CalendarioRepository.sync_task(task)
        messages.success(request, "Tarea creada exitosamente.")
        return redirect("tareas:tarea_detail", pk=task["id"])
    return render(request, "tareas/tarea_form.html", {"form": form, "curso": course})


@login_required
@docente_or_admin_required
def tarea_edit(request, pk):
    task = _required(TareaRepository.get_task(pk), "Tarea no encontrada.")
    course = task["curso"]
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No tienes permisos para editar esta tarea.")
    form = TareaForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        task = TareaRepository.save_task(
            {
                **form.cleaned_data,
                "curso_id": course["id"],
                "creado_por_id": task.get("creado_por_id"),
                "fecha_creacion": task.get("fecha_creacion"),
            },
            pk,
        )
        CalendarioRepository.sync_task(task)
        messages.success(request, "Tarea actualizada.")
        return redirect("tareas:tarea_detail", pk=pk)
    return render(
        request,
        "tareas/tarea_form.html",
        {"form": form, "curso": course, "tarea": task},
    )


@login_required
@docente_or_admin_required
def tarea_delete(request, pk):
    task = _required(TareaRepository.get_task(pk), "Tarea no encontrada.")
    if not _can_manage(request.user, task["curso"]):
        return HttpResponseForbidden("No tienes permisos para eliminar esta tarea.")
    if request.method == "POST":
        course_id = task["curso_id"]
        TareaRepository.delete_task(pk)
        CalendarioRepository.delete_by_origin(f"tarea-{pk}")
        messages.success(request, "Tarea eliminada.")
        return redirect("tareas:tarea_list", curso_pk=course_id)
    return render(request, "tareas/tarea_confirm_delete.html", {"tarea": task})


@login_required
def entrega_create(request, tarea_pk):
    task = _required(TareaRepository.get_task(tarea_pk), "Tarea no encontrada.")
    email = _email(request.user)
    if not InscripcionRepository.get(email, task["curso_id"]):
        return HttpResponseForbidden("Debes estar inscrito en el curso.")
    if EntregaTareaRepository.get(tarea_pk, email):
        messages.error(request, "Ya existe una entrega para esta tarea.")
        return redirect("tareas:tarea_detail", pk=tarea_pk)
    if timezone.now() > task["fecha_limite"]:
        messages.error(request, "El plazo de entrega ha finalizado.")
        return redirect("tareas:tarea_detail", pk=tarea_pk)
    form = EntregaTareaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        path = ""
        uploaded = form.cleaned_data.get("archivo")
        if uploaded:
            path = default_storage.save(f"entregas/{uploaded.name}", uploaded)
        EntregaTareaRepository.save(
            {
                "tarea_id": str(tarea_pk),
                "estudiante_id": email,
                "archivo": path,
                "comentario": form.cleaned_data.get("comentario", ""),
            }
        )
        messages.success(request, "Entrega enviada.")
        return redirect("tareas:tarea_detail", pk=tarea_pk)
    return render(request, "tareas/entrega_form.html", {"form": form, "tarea": task})


@login_required
@docente_or_admin_required
def entrega_grade(request, pk):
    submission = _required(
        EntregaTareaRepository.get_by_id(pk), "Entrega no encontrada."
    )
    task = submission["tarea"]
    if not _can_manage(request.user, task["curso"]):
        return HttpResponseForbidden("No tienes permisos para calificar esta entrega.")
    form = CalificacionForm(request.POST or None, instance=submission, tarea=task)
    if request.method == "POST" and form.is_valid():
        EntregaTareaRepository.save(
            {
                **submission,
                "puntaje_obtenido": form.cleaned_data["puntaje_obtenido"],
                "retroalimentacion": form.cleaned_data.get("retroalimentacion", ""),
                "estado": "calificado",
                "calificado_por_id": _email(request.user),
                "fecha_calificacion": timezone.now(),
            },
            submission["id"],
        )
        messages.success(request, "Entrega calificada.")
        return redirect("tareas:tarea_detail", pk=task["id"])
    return render(
        request,
        "tareas/entrega_grade.html",
        {"form": form, "entrega": submission, "tarea": task},
    )
