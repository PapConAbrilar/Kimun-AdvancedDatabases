from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import UserPassesTestMixin
from cursos.repository import CursoRepository


class RoleRequiredMixin(UserPassesTestMixin):
    required_roles = []

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        return self.request.user.rol in self.required_roles

    def handle_no_permission(self):
        return HttpResponseForbidden('No tienes permisos para acceder a esta página.')


class AdminRequiredMixin(RoleRequiredMixin):
    required_roles = ['admin']


class DocenteOrAdminRequiredMixin(RoleRequiredMixin):
    required_roles = ['admin', 'docente']


class CourseOwnerOrAdminMixin(UserPassesTestMixin):
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        
        if self.request.user.rol == 'admin':
            return True
        
        if self.request.user.rol == 'docente':
            curso_pk = self.kwargs.get('pk') or self.kwargs.get('curso_pk')
            if curso_pk:
                try:
                    curso = CursoRepository.get_course(curso_pk, enrich=False)
                    email = self.request.user.email or self.request.user.username
                    return bool(curso and curso.get('docente_creador_id') == email)
                except (TypeError, ValueError):
                    return False
        
        return False

    def handle_no_permission(self):
        return HttpResponseForbidden('No tienes permisos para acceder a este curso.')
