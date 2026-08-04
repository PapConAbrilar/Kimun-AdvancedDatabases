from django.urls import path
from . import views

app_name = 'calendario'

urlpatterns = [
    path('', views.calendario_view, name='calendario'),
    path('eventos/', views.calendario_eventos, name='calendario_eventos'),
    path('evento/crear/', views.evento_create, name='evento_create'),
    path('evento/<int:pk>/editar/', views.evento_edit, name='evento_edit'),
    path('evento/<int:pk>/eliminar/', views.evento_delete, name='evento_delete'),
    path('exportar.ics', views.calendario_ical_export, name='calendario_ical_export'),
]
