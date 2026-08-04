from django.urls import path
from . import views

app_name = 'tareas'

urlpatterns = [
    path('curso/<int:curso_pk>/tareas/', views.tarea_list, name='tarea_list'),
    path('tarea/<int:pk>/', views.tarea_detail, name='tarea_detail'),
    path('curso/<int:curso_pk>/tareas/crear/', views.tarea_create, name='tarea_create'),
    path('tarea/<int:pk>/editar/', views.tarea_edit, name='tarea_edit'),
    path('tarea/<int:pk>/eliminar/', views.tarea_delete, name='tarea_delete'),
    path('tarea/<int:tarea_pk>/entregar/', views.entrega_create, name='entrega_create'),
    path('entrega/<int:pk>/calificar/', views.entrega_grade, name='entrega_grade'),
]
