from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from certificados.repository import CertificadoRepository
from cursos.repository import CursoRepository, InscripcionRepository
from evaluaciones.repository import EvaluacionRepository
from reportes.repository import ReporteRepository
from usuarios.decorators import admin_required
from usuarios.forms import UsuarioForm
from usuarios.repository import AreaCargoRepository, UsuarioRepository
from usuarios.utils import notificar_inscripcion, verificar_recordatorios


def _user_email(user):
    return user.email or user.username


def _required(value, message="Registro no encontrado."):
    if not value:
        raise Http404(message)
    return value


def _area_groups(areas):
    collaborator_names = {
        "Profesional de Atención Directa",
        "Técnico de Atención Directa",
        "Asistente de Trato Directo",
        "Auxiliares de Servicio",
        "Manipuladores de Alimento",
    }
    admin_names = {"Administración y Apoyo", "Directivos"}
    teacher_names = {"Docente Interno", "Docente Externo"}
    return {
        "areas": areas,
        "areas_colaborador": [item for item in areas if item["nombre"] in collaborator_names],
        "areas_admin": [item for item in areas if item["nombre"] in admin_names],
        "areas_docente": [item for item in areas if item["nombre"] in teacher_names],
    }


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("inicio")
        messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, "registration/login.html", {"form": {}})


def logout_view(request):
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect("usuarios:login")


@login_required(login_url="usuarios:login")
def inicio(request):
    email = _user_email(request.user)
    now = timezone.now()
    context = {}

    if request.user.rol == "admin":
        dashboard = ReporteRepository.dashboard()
        context.update(dashboard)
        context["ultimas_inscripciones"] = dashboard["ultimas_inscripciones"][:5]
    elif request.user.rol == "docente":
        courses = CursoRepository.get_all_courses(teacher_id=email)
        enrollments = [
            enrollment
            for course in courses
            for enrollment in InscripcionRepository.list_by_course(course["id"])
        ]
        context.update(
            {
                "mis_cursos_count": len(courses),
                "mis_inscripciones_count": len(enrollments),
            }
        )

    if request.user.rol in {"colaborador", "alumno", "docente"}:
        enrollments = InscripcionRepository.list_by_user(email)
        certificates = CertificadoRepository.list_by_user(email)
        upcoming = []
        for enrollment in enrollments:
            deadline = enrollment["curso"].get("fecha_limite")
            if not deadline:
                continue
            days = (deadline - now).days
            if 0 <= days <= 7:
                upcoming.append(
                    {
                        "titulo": enrollment["curso"]["titulo"],
                        "fecha_limite": deadline,
                        "dias": days,
                        "vencido": False,
                    }
                )
        context.update(
            {
                "mis_inscripciones": enrollments[:3],
                "mis_certificados_count": len(certificates),
                "cursos_cercanos": upcoming,
            }
        )
        verificar_recordatorios(request.user)

    return render(request, "inicio.html", context)


@login_required
def mis_cursos(request):
    email = _user_email(request.user)
    context = {"now": timezone.now()}
    if request.user.rol == "admin":
        context.update(
            {
                "cursos": CursoRepository.get_all_courses(),
                "es_docente": True,
                "es_admin": True,
            }
        )
    elif request.user.rol == "docente":
        context.update(
            {
                "cursos": CursoRepository.get_all_courses(teacher_id=email),
                "es_docente": True,
            }
        )
    else:
        context["inscripciones"] = InscripcionRepository.list_by_user(email)
    return render(request, "usuarios/mis_cursos.html", context)


@login_required
def perfil(request):
    email = _user_email(request.user)
    enrollments = InscripcionRepository.list_by_user(email)
    attempts = EvaluacionRepository.get_intentos_por_usuario(email)
    certificates = CertificadoRepository.list_by_user(email)
    completed = sum(item["estado"] == "completado" for item in enrollments)
    in_progress = sum(item["estado"] == "en_progreso" for item in enrollments)
    total = len(enrollments)
    return render(
        request,
        "usuarios/perfil.html",
        {
            "intentos": attempts[:10],
            "certificados": certificates,
            "total_enrolled": total,
            "completed_count": completed,
            "in_progress_count": in_progress,
            "certificados_count": len(certificates),
            "evaluations_taken": len(attempts),
            "evaluations_passed": sum(item.get("aprobado", False) for item in attempts),
            "completion_rate": int(completed * 100 / total) if total else 0,
            "recent_inscripciones": enrollments[:5],
        },
    )


class PasswordChangeRepositoryForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput, label="Contraseña actual")
    new_password1 = forms.CharField(widget=forms.PasswordInput, label="Nueva contraseña")
    new_password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña")

    def clean(self):
        data = super().clean()
        if data.get("new_password1") != data.get("new_password2"):
            raise forms.ValidationError("Las contraseñas nuevas no coinciden.")
        return data


@login_required
def password_change(request):
    email = _user_email(request.user)
    user = UsuarioRepository.get_by_email(email)
    form = PasswordChangeRepositoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not check_password(form.cleaned_data["old_password"], user.get("password_hash")):
            form.add_error("old_password", "La contraseña actual no es correcta.")
        else:
            UsuarioRepository.update_user(
                email, {"password_hash": make_password(form.cleaned_data["new_password1"])}
            )
            messages.success(request, "Contraseña actualizada exitosamente.")
            return redirect("usuarios:perfil")
    return render(request, "usuarios/password_change.html", {"form": form})


@login_required
@admin_required
def usuario_list(request):
    users = UsuarioRepository.list_all()
    page = Paginator(users, 20).get_page(request.GET.get("page", 1))
    return render(request, "usuarios/usuario_list.html", {"usuarios": page, "page_obj": page})


@login_required
@admin_required
def usuario_create(request):
    areas = AreaCargoRepository.list_all()
    form = UsuarioForm(request.POST or None, areas=areas)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        if UsuarioRepository.get_by_email(data["email"]):
            form.add_error("email", "Ya existe un usuario con ese correo electrónico.")
        elif not data.get("password"):
            form.add_error("password", "La contraseña es obligatoria al crear un usuario.")
        else:
            user = UsuarioRepository.create_user(
                data["email"],
                make_password(data["password"]),
                rol=data["rol"],
                rut=data["rut"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                cargo_id=data.get("cargo"),
            )
            messages.success(request, f'Usuario "{user["nombre"]}" creado exitosamente.')
            return redirect("usuarios:usuario_list")
    return render(
        request,
        "usuarios/usuario_form.html",
        {"form": form, **_area_groups(areas), "accion": "crear"},
    )


@login_required
@admin_required
def usuario_edit(request, pk):
    user = _required(UsuarioRepository.get_by_email(pk), "Usuario no encontrado.")
    areas = AreaCargoRepository.list_all()
    initial = {**user, "cargo": user.get("cargo_id", "")}
    form = UsuarioForm(request.POST or None, instance=initial, areas=areas)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        changes = {
            "username": data["username"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "rut": data["rut"],
            "rol": data["rol"],
            "cargo_id": data.get("cargo", ""),
        }
        if data.get("password"):
            changes["password_hash"] = make_password(data["password"])
        UsuarioRepository.update_user(pk, changes)
        messages.success(request, "Usuario actualizado.")
        return redirect("usuarios:usuario_list")
    return render(
        request,
        "usuarios/usuario_form.html",
        {"form": form, "usuario": user, **_area_groups(areas), "accion": "editar"},
    )


@login_required
@admin_required
def usuario_delete(request, pk):
    user = _required(UsuarioRepository.get_by_email(pk), "Usuario no encontrado.")
    if request.method == "POST":
        if pk == _user_email(request.user):
            messages.error(request, "No puedes eliminar tu propia cuenta.")
        else:
            UsuarioRepository.delete_user(pk)
            messages.success(request, f'Usuario "{user["nombre"]}" eliminado.')
        return redirect("usuarios:usuario_list")
    return render(request, "usuarios/usuario_confirm_delete.html", {"usuario": user})


@login_required
@admin_required
def inscribir_curso(request, curso_id):
    course = _required(CursoRepository.get_course(curso_id), "Curso no encontrado.")
    if request.method == "POST":
        user_email = request.POST.get("usuario_id")
        user = UsuarioRepository.get_by_email(user_email)
        if not user:
            messages.error(request, "Usuario no encontrado.")
        elif InscripcionRepository.get(user_email, curso_id):
            messages.error(request, "El usuario ya está inscrito en este curso.")
        else:
            enrollment = InscripcionRepository.save(user_email, curso_id)
            notificar_inscripcion(enrollment)
            messages.success(request, f'{user["nombre"]} ha sido inscrito en {course["titulo"]}.')
            return redirect("cursos:curso_detail", pk=curso_id)
    enrolled = {item["usuario_id"] for item in InscripcionRepository.list_by_course(curso_id)}
    available = [
        user for user in UsuarioRepository.list_all(role="colaborador") if user["email"] not in enrolled
    ]
    return render(request, "usuarios/inscribir_curso.html", {"curso": course, "usuarios": available})


@login_required
@admin_required
def inscribir_curso_bulk(request, curso_id):
    course = _required(CursoRepository.get_course(curso_id), "Curso no encontrado.")
    enrolled = {item["usuario_id"] for item in InscripcionRepository.list_by_course(curso_id)}
    if request.method == "POST":
        selected = request.POST.getlist("usuarios")
        if not selected:
            messages.error(request, "Selecciona al menos un usuario.")
        else:
            created = 0
            for email in selected:
                if email not in enrolled and UsuarioRepository.get_by_email(email):
                    enrollment = InscripcionRepository.save(email, curso_id)
                    notificar_inscripcion(enrollment)
                    created += 1
            messages.success(request, f"{created} usuario(s) inscrito(s) exitosamente.")
            return redirect("cursos:curso_detail", pk=curso_id)
    query = request.GET.get("q", "").lower()
    available = [
        user for user in UsuarioRepository.list_all(role="colaborador") if user["email"] not in enrolled
    ]
    if query:
        available = [
            user
            for user in available
            if query in " ".join(
                [user.get("username", ""), user.get("nombre", ""), user.get("rut", "")]
            ).lower()
        ]
    return render(
        request,
        "usuarios/inscribir_curso_bulk.html",
        {"curso": course, "usuarios": available, "query": query},
    )
