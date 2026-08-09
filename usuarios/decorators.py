from functools import wraps

from django.http import HttpResponseForbidden

from cursos.repository import CursoRepository


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not getattr(request, "user", None) or not request.user.is_authenticated:
                return HttpResponseForbidden("Debes iniciar sesión.")
            if request.user.rol not in roles:
                return HttpResponseForbidden("No tienes permisos para acceder a esta página.")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def course_owner_or_admin(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return HttpResponseForbidden("Debes iniciar sesión.")
        if request.user.rol == "admin":
            return view_func(request, *args, **kwargs)
        course_id = kwargs.get("pk") or kwargs.get("curso_pk") or kwargs.get("curso_id")
        course = CursoRepository.get_course(course_id, enrich=False) if course_id else None
        email = request.user.email or request.user.username
        if request.user.rol == "docente" and course:
            if course.get("docente_creador_id") == email:
                return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("No tienes permisos para acceder a este curso.")

    return wrapped


def admin_required(view_func):
    return role_required("admin")(view_func)


def docente_or_admin_required(view_func):
    return role_required("admin", "docente")(view_func)
