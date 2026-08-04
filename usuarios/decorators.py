from functools import wraps
from django.http import HttpResponseForbidden
from cursos.models import Curso


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return HttpResponseForbidden('Debes iniciar sesión.')
            
            if request.user.rol not in roles:
                return HttpResponseForbidden('No tienes permisos para acceder a esta página.')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def course_owner_or_admin(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return HttpResponseForbidden('Debes iniciar sesión.')
        
        if request.user.rol == 'admin':
            return view_func(request, *args, **kwargs)
        
        if request.user.rol == 'docente':
            curso_pk = kwargs.get('pk') or kwargs.get('curso_pk')
            
            if curso_pk:
                try:
                    curso = Curso.objects.get(pk=curso_pk)
                    if curso.docente_creador == request.user:
                        return view_func(request, *args, **kwargs)
                except Curso.DoesNotExist:
                    pass
            
            return HttpResponseForbidden('No tienes permisos para acceder a este curso.')
        
        return HttpResponseForbidden('No tienes permisos para acceder a esta página.')
    return _wrapped_view


def admin_required(view_func):
    return role_required('admin')(view_func)


def docente_or_admin_required(view_func):
    return role_required('admin', 'docente')(view_func)
