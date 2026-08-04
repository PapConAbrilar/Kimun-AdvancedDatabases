from django.urls import path
from . import views

app_name = 'certificados'

urlpatterns = [
    path('', views.certificado_list, name='certificado_list'),
    path('mis-certificados/', views.mis_certificados, name='mis_certificados'),
    path('generar/<int:curso_pk>/', views.generar_certificado, name='generar_certificado'),
    path('descargar/<int:pk>/', views.descargar_certificado, name='descargar_certificado'),
    path('eliminar/<int:pk>/', views.eliminar_certificado, name='eliminar_certificado'),
    path('verificar/<uuid:codigo>/', views.verificar_certificado, name='verificar_certificado'),
    path('pendientes/', views.certificados_pendientes, name='certificados_pendientes'),
    path('<int:pk>/aprobar/', views.aprobar_certificado, name='aprobar_certificado'),
    path('<int:pk>/rechazar/', views.rechazar_certificado, name='rechazar_certificado'),
    path('<int:pk>/resetear/', views.resetear_certificado, name='resetear_certificado'),
]