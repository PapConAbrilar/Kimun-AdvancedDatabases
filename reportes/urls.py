from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.dashboard_reportes, name='dashboard_reportes'),
    path('progreso/', views.progreso_heatmap, name='progreso_heatmap'),
    path('curso/<int:curso_pk>/', views.reporte_curso, name='reporte_curso'),
    path('usuario/<int:usuario_pk>/', views.reporte_usuario, name='reporte_usuario'),
]