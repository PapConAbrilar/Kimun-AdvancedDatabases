from django.urls import path
from . import views

app_name = 'cursos'

urlpatterns = [
    path('', views.curso_list, name='curso_list'),
    path('crear/', views.curso_create, name='curso_create'),
    path('categorias/', views.categoria_list, name='categoria_list'),
    path('categorias/crear/', views.categoria_create, name='categoria_create'),
    path('categorias/<str:pk>/editar/', views.categoria_edit, name='categoria_edit'),
    path('categorias/<str:pk>/eliminar/', views.categoria_delete, name='categoria_delete'),
    path('material/<str:pk>/eliminar/', views.material_delete, name='material_delete'),
    path('clases/<str:pk>/', views.clase_detail, name='clase_detail'),
    path('clases/<str:pk>/editar/', views.clase_edit, name='clase_edit'),
    path('clases/<str:pk>/eliminar/', views.clase_delete, name='clase_delete'),
    path('clases/<str:pk>/completar/', views.clase_completar, name='clase_completar'),
    path('<str:pk>/', views.curso_detail, name='curso_detail'),
    path('<str:pk>/editar/', views.curso_edit, name='curso_edit'),
    path('<str:pk>/eliminar/', views.curso_delete, name='curso_delete'),
    path('<str:pk>/material/crear/', views.material_create, name='material_create'),

    # Rutas de clases (lecciones)
    path('<str:pk>/clases/', views.clase_list, name='clase_list'),
    path('<str:pk>/clases/crear/', views.clase_create, name='clase_create'),
]
