from django.contrib import admin
from django.contrib.admin import AdminSite


class KimunAdminSite(AdminSite):
    site_title = 'Kimün - Administración'
    site_header = 'Kimün - Plataforma de Capacitación'
    index_title = 'Panel de Control'

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        
        user = request.user
        if not user.is_superuser:
            rol = getattr(user, 'rol', None)
            
            allowed_apps = []
            
            if rol == 'admin':
                allowed_apps = ['usuarios', 'cursos', 'evaluaciones', 'certificados']
            elif rol == 'docente':
                allowed_apps = ['cursos', 'evaluaciones']
            else:
                allowed_apps = ['cursos', 'certificados']
            
            app_list = [app for app in app_list if app['app_label'] in allowed_apps]
        
        return app_list


kimun_admin_site = KimunAdminSite(name='kimun_admin')