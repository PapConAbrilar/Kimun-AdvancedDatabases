from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.inicio, name='inicio'),
    path('mis-cursos/', views.mis_cursos, name='mis_cursos'),
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/contrasena/', views.password_change, name='password_change'),
    path('cursos/<int:curso_id>/inscribir/', views.inscribir_curso, name='inscribir_curso'),
    path('cursos/<int:curso_id>/inscribir-bulk/', views.inscribir_curso_bulk, name='inscribir_curso_bulk'),
    path('usuarios/', views.usuario_list, name='usuario_list'),
    path('usuarios/crear/', views.usuario_create, name='usuario_create'),
    path('usuarios/<int:pk>/editar/', views.usuario_edit, name='usuario_edit'),
    path('usuarios/<int:pk>/eliminar/', views.usuario_delete, name='usuario_delete'),
]