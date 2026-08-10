from django.urls import path
from . import views
from . import bigdata_views

app_name = 'reportes'

urlpatterns = [
    path('', views.dashboard_reportes, name='dashboard_reportes'),
    path('progreso/', views.progreso_heatmap, name='progreso_heatmap'),
    path('curso/<str:curso_pk>/', views.reporte_curso, name='reporte_curso'),
    path('usuario/<str:usuario_pk>/', views.reporte_usuario, name='reporte_usuario'),
    path('bigdata/', bigdata_views.bigdata_dashboard, name='bigdata_dashboard'),
]
