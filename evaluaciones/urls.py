from django.urls import path
from . import views

app_name = 'evaluaciones'

urlpatterns = [
    path('curso/<int:curso_pk>/evaluaciones/', views.evaluacion_list, name='evaluacion_list'),
    path('curso/<int:curso_pk>/evaluaciones/crear/', views.evaluacion_create, name='evaluacion_create'),
    path('evaluacion/<int:pk>/editar/', views.evaluacion_edit, name='evaluacion_edit'),
    path('evaluacion/<int:pk>/eliminar/', views.evaluacion_delete, name='evaluacion_delete'),
    path('evaluacion/<int:pk>/tomar/', views.tomar_evaluacion, name='tomar_evaluacion'),
    path('evaluacion/<int:pk>/resultado/<int:intento_pk>/', views.resultado_evaluacion, name='resultado_evaluacion'),
    path('bancos/', views.banco_list, name='banco_list'),
    path('bancos/crear/', views.banco_create, name='banco_create'),
    path('bancos/<int:pk>/', views.banco_detail, name='banco_detail'),
    path('bancos/<int:pk>/editar/', views.banco_edit, name='banco_edit'),
    path('bancos/<int:pk>/eliminar/', views.banco_delete, name='banco_delete'),
    path('bancos/<int:banco_pk>/agregar-pregunta/', views.banco_agregar_pregunta, name='banco_agregar_pregunta'),
]