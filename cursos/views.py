from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from calendario.repository import CalendarioRepository
from cursos.forms import CategoriaForm, ClaseForm, CursoForm, MaterialForm
from cursos.repository import (
    CategoriaRepository,
    ClaseRepository,
    CursoRepository,
    InscripcionRepository,
    MaterialRepository,
    ProgresoClaseRepository,
)
from evaluaciones.repository import EvaluacionRepository
from tareas.repository import TareaRepository
from usuarios.decorators import docente_or_admin_required
from usuarios.repository import UsuarioRepository


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
def curso_list(request):
    category_id = request.GET.get("categoria") or None
    search = request.GET.get("q", "").strip().lower()
    state = None if request.user.rol in {"admin", "docente"} else "publicado"
    courses = CursoRepository.get_all_courses(state=state, category_id=category_id)
    if search:
        courses = [
            course
            for course in courses
            if search in f'{course.get("titulo", "")} {course.get("descripcion", "")}'.lower()
        ]
    return render(
        request,
        "cursos/curso_list.html",
        {
            "cursos": courses,
            "categorias": CategoriaRepository.list_all(),
            "categoria_filter": category_id or "",
            "query": search,
        },
    )


@login_required
@docente_or_admin_required
def curso_create(request):
    categories = CategoriaRepository.list_all()
    teachers = UsuarioRepository.list_all(role="docente")
    form = CursoForm(
        request.POST or None,
        categorias=categories,
        docentes=teachers,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        teacher = data.get("docente_creador") or _email(request.user)
        course = CursoRepository.create_course(
            {
                "titulo": data["titulo"],
                "descripcion": data["descripcion"],
                "categoria_id": data.get("categoria", ""),
                "estado": data["estado"],
                "docente_creador_id": teacher,
                "fecha_limite": data.get("fecha_limite"),
            }
        )
        CalendarioRepository.sync_course(course)
        messages.success(request, "Curso creado exitosamente.")
        return redirect("cursos:curso_detail", pk=course["id"])
    return render(request, "cursos/curso_form.html", {"form": form, "accion": "crear"})


@login_required
def curso_detail(request, pk):
    course = _required(CursoRepository.get_course(pk), "Curso no encontrado.")
    email = _email(request.user)
    enrollment = InscripcionRepository.get(email, pk)
    can_manage = _can_manage(request.user, course)
    if course.get("estado") != "publicado" and not can_manage:
        return HttpResponseForbidden("No tienes permisos para ver este curso.")

    classes = ClaseRepository.list_by_course(pk)
    progress = {item["clase_id"] for item in ProgresoClaseRepository.list_by_user(email)}
    class_items = [{"clase": item, "completado": item["id"] in progress} for item in classes]
    completed_classes = sum(item["completado"] for item in class_items)
    class_progress = int(completed_classes * 100 / len(classes)) if classes else 0
    materials = MaterialRepository.list_by_course(pk)
    for material in materials:
        if material.get("archivo"):
            try:
                material["archivo_url"] = default_storage.url(material["archivo"])
            except Exception:
                material["archivo_url"] = ""
    evaluations = EvaluacionRepository.list_by_course(pk)
    tasks = TareaRepository.list_by_course(pk)
    course["tiene_evaluaciones"] = bool(evaluations)
    approved_evaluations = 0
    if enrollment:
        approved_evaluations = sum(
            any(
                attempt.get("aprobado")
                for attempt in EvaluacionRepository.get_intentos_por_usuario(
                    email, evaluation["id"]
                )
            )
            for evaluation in evaluations
        )
    course_progress = (
        int(approved_evaluations * 100 / len(evaluations)) if evaluations else 0
    )
    return render(
        request,
        "cursos/curso_detail.html",
        {
            "curso": course,
            "materiales": materials,
            "clases": classes,
            "clases_con_estado": class_items,
            "clases_progress": class_progress,
            "tareas": tasks[:5],
            "evaluaciones": evaluations,
            "is_enrolled": bool(enrollment),
            "inscripcion": enrollment,
            "puede_gestionar": can_manage,
            "puede_editar": can_manage,
            "course_progress": course_progress,
            "now": timezone.now(),
        },
    )


@login_required
@docente_or_admin_required
def curso_edit(request, pk):
    course = _required(CursoRepository.get_course(pk), "Curso no encontrado.")
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No tienes permisos para editar este curso.")
    categories = CategoriaRepository.list_all()
    teachers = UsuarioRepository.list_all(role="docente")
    initial = {
        **course,
        "categoria": course.get("categoria_id", ""),
        "docente_creador": course.get("docente_creador_id", ""),
    }
    form = CursoForm(
        request.POST or None,
        instance=initial,
        categorias=categories,
        docentes=teachers,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        updated_course = CursoRepository.update_course(
            pk,
            {
                "titulo": data["titulo"],
                "descripcion": data["descripcion"],
                "categoria_id": data.get("categoria", ""),
                "estado": data["estado"],
                "docente_creador_id": data.get("docente_creador")
                or course.get("docente_creador_id"),
                "fecha_limite": data.get("fecha_limite"),
            },
        )
        CalendarioRepository.sync_course(updated_course)
        messages.success(request, "Curso actualizado.")
        return redirect("cursos:curso_detail", pk=pk)
    return render(
        request,
        "cursos/curso_form.html",
        {"form": form, "curso": course, "accion": "editar"},
    )


@login_required
@docente_or_admin_required
def curso_delete(request, pk):
    course = _required(CursoRepository.get_course(pk), "Curso no encontrado.")
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No tienes permisos para eliminar este curso.")
    if request.method == "POST":
        CursoRepository.delete_course(pk)
        CalendarioRepository.delete_by_origin(f"curso-inicio-{pk}")
        CalendarioRepository.delete_by_origin(f"curso-fin-{pk}")
        messages.success(request, "Curso eliminado.")
        return redirect("cursos:curso_list")
    return render(request, "cursos/curso_confirm_delete.html", {"curso": course})


@login_required
@docente_or_admin_required
def material_create(request, pk):
    course = _required(CursoRepository.get_course(pk), "Curso no encontrado.")
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No tienes permisos para administrar materiales.")
    form = MaterialForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        path = ""
        if data.get("archivo"):
            path = default_storage.save(
                f'materiales/{data["archivo"].name}', data["archivo"]
            )
        MaterialRepository.save_material(
            {
                "curso_id": str(pk),
                "titulo": data["titulo"],
                "tipo": data["tipo"],
                "archivo": path,
                "url": data.get("url", ""),
            }
        )
        messages.success(request, "Material agregado.")
        return redirect("cursos:curso_detail", pk=pk)
    return render(request, "cursos/material_form.html", {"form": form, "curso": course})


@login_required
@docente_or_admin_required
def material_delete(request, pk):
    material = _required(MaterialRepository.get(pk), "Material no encontrado.")
    course = _required(CursoRepository.get_course(material["curso_id"]), "Curso no encontrado.")
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No tienes permisos para eliminar este material.")
    if request.method == "POST":
        if material.get("archivo"):
            default_storage.delete(material["archivo"])
        MaterialRepository.delete(pk)
        messages.success(request, "Material eliminado.")
    return redirect("cursos:curso_detail", pk=course["id"])


@login_required
def categoria_list(request):
    return render(
        request,
        "cursos/categoria_list.html",
        {"categorias": CategoriaRepository.list_all()},
    )


@login_required
@docente_or_admin_required
def categoria_create(request):
    form = CategoriaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        CategoriaRepository.save(form.cleaned_data)
        messages.success(request, "Categoría creada.")
        return redirect("cursos:categoria_list")
    return render(request, "cursos/categoria_form.html", {"form": form, "accion": "crear"})


@login_required
@docente_or_admin_required
def categoria_edit(request, pk):
    category = _required(CategoriaRepository.get(pk), "Categoría no encontrada.")
    form = CategoriaForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        CategoriaRepository.save(form.cleaned_data, pk)
        messages.success(request, "Categoría actualizada.")
        return redirect("cursos:categoria_list")
    return render(
        request,
        "cursos/categoria_form.html",
        {"form": form, "categoria": category, "accion": "editar"},
    )


@login_required
@docente_or_admin_required
def categoria_delete(request, pk):
    category = _required(CategoriaRepository.get(pk), "Categoría no encontrada.")
    category["cursos_count"] = sum(
        course.get("categoria_id") == str(pk)
        for course in CursoRepository.get_all_courses(enrich=False)
    )
    if request.method == "POST":
        if category["cursos_count"]:
            messages.error(request, "No se puede eliminar una categoría con cursos asociados.")
        else:
            CategoriaRepository.delete(pk)
            messages.success(request, "Categoría eliminada.")
        return redirect("cursos:categoria_list")
    return render(
        request, "cursos/categoria_confirm_delete.html", {"categoria": category}
    )


@login_required
def clase_list(request, pk):
    course = _required(CursoRepository.get_course(pk), "Curso no encontrado.")
    email = _email(request.user)
    progress = {item["clase_id"] for item in ProgresoClaseRepository.list_by_user(email)}
    items = [
        {"clase": class_item, "completado": class_item["id"] in progress}
        for class_item in ClaseRepository.list_by_course(pk)
    ]
    return render(request, "cursos/clase_list.html", {"curso": course, "clases": items})


@login_required
@docente_or_admin_required
def clase_create(request, pk):
    course = _required(CursoRepository.get_course(pk), "Curso no encontrado.")
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No tienes permisos para crear clases.")
    classes = ClaseRepository.list_by_course(pk)
    form = ClaseForm(
        request.POST or None,
        clases=classes,
        initial={"orden": len(classes) + 1},
    )
    if request.method == "POST" and form.is_valid():
        ClaseRepository.save_class({**form.cleaned_data, "curso_id": str(pk)})
        messages.success(request, "Clase creada.")
        return redirect("cursos:clase_list", pk=pk)
    return render(request, "cursos/clase_form.html", {"form": form, "curso": course})


@login_required
def clase_detail(request, pk):
    class_item = _required(ClaseRepository.get(pk), "Clase no encontrada.")
    course = _required(CursoRepository.get_course(class_item["curso_id"]), "Curso no encontrado.")
    email = _email(request.user)
    enrollment = InscripcionRepository.get(email, course["id"])
    if not _can_manage(request.user, course) and not enrollment:
        return HttpResponseForbidden("Debes estar inscrito en este curso.")
    previous, following = ClaseRepository.previous_and_next(class_item)
    completed = bool(ProgresoClaseRepository.get(email, pk))
    previous_completed = not previous or bool(ProgresoClaseRepository.get(email, previous["id"]))
    return render(
        request,
        "cursos/clase_detail.html",
        {
            "clase": class_item,
            "curso": course,
            "clase_anterior": previous,
            "siguiente_clase": following,
            "completado": completed,
            "puede_completar": previous_completed,
        },
    )


@login_required
@docente_or_admin_required
def clase_edit(request, pk):
    class_item = _required(ClaseRepository.get(pk), "Clase no encontrada.")
    course = _required(CursoRepository.get_course(class_item["curso_id"]), "Curso no encontrado.")
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No tienes permisos para editar esta clase.")
    form = ClaseForm(
        request.POST or None,
        instance=class_item,
        clases=ClaseRepository.list_by_course(course["id"]),
    )
    if request.method == "POST" and form.is_valid():
        ClaseRepository.save_class(
            {**form.cleaned_data, "curso_id": course["id"]}, pk
        )
        messages.success(request, "Clase actualizada.")
        return redirect("cursos:clase_detail", pk=pk)
    return render(
        request,
        "cursos/clase_form.html",
        {"form": form, "curso": course, "clase": class_item},
    )


@login_required
@docente_or_admin_required
def clase_delete(request, pk):
    class_item = _required(ClaseRepository.get(pk), "Clase no encontrada.")
    course = _required(CursoRepository.get_course(class_item["curso_id"]), "Curso no encontrado.")
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No tienes permisos para eliminar esta clase.")
    if request.method == "POST":
        ClaseRepository.delete(pk)
        messages.success(request, "Clase eliminada.")
        return redirect("cursos:clase_list", pk=course["id"])
    return render(
        request,
        "cursos/clase_confirm_delete.html",
        {"clase": class_item, "curso": course},
    )


@login_required
def clase_completar(request, pk):
    if request.method != "POST":
        return redirect("cursos:clase_detail", pk=pk)
    class_item = _required(ClaseRepository.get(pk), "Clase no encontrada.")
    email = _email(request.user)
    enrollment = InscripcionRepository.get(email, class_item["curso_id"])
    if not enrollment:
        return HttpResponseForbidden("Debes estar inscrito en este curso.")
    previous, _ = ClaseRepository.previous_and_next(class_item)
    if previous and not ProgresoClaseRepository.get(email, previous["id"]):
        messages.error(request, "Debes completar la clase anterior primero.")
    elif not ProgresoClaseRepository.get(email, pk):
        ProgresoClaseRepository.complete(email, class_item)
        if enrollment["estado"] == "asignado":
            InscripcionRepository.update_state(email, class_item["curso_id"], "en_progreso")
        messages.success(request, "Clase marcada como completada.")
    return redirect("cursos:clase_detail", pk=pk)
