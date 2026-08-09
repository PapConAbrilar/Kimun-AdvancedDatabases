from django.urls import path
from . import views

app_name = 'tareas'

urlpatterns = [
    path('curso/<str:curso_pk>/tareas/', views.tarea_list, name='tarea_list'),
    path('tarea/<str:pk>/', views.tarea_detail, name='tarea_detail'),
    path('curso/<str:curso_pk>/tareas/crear/', views.tarea_create, name='tarea_create'),
    path('tarea/<str:pk>/editar/', views.tarea_edit, name='tarea_edit'),
    path('tarea/<str:pk>/eliminar/', views.tarea_delete, name='tarea_delete'),
    path('tarea/<str:tarea_pk>/entregar/', views.entrega_create, name='entrega_create'),
    path('entrega/<str:pk>/calificar/', views.entrega_grade, name='entrega_grade'),
]
