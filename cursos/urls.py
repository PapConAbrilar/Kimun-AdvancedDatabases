from django.urls import path
from . import views

app_name = 'cursos'

urlpatterns = [
    path('', views.curso_list, name='curso_list'),
    path('crear/', views.curso_create, name='curso_create'),
    path('<int:pk>/', views.curso_detail, name='curso_detail'),
    path('<int:pk>/editar/', views.curso_edit, name='curso_edit'),
    path('<int:pk>/eliminar/', views.curso_delete, name='curso_delete'),
    path('<int:pk>/material/crear/', views.material_create, name='material_create'),
    path('material/<int:pk>/eliminar/', views.material_delete, name='material_delete'),
    
    path('categorias/', views.categoria_list, name='categoria_list'),
    path('categorias/crear/', views.categoria_create, name='categoria_create'),
    path('categorias/<int:pk>/editar/', views.categoria_edit, name='categoria_edit'),
    path('categorias/<int:pk>/eliminar/', views.categoria_delete, name='categoria_delete'),
    
    # Clase (Lección) URLs
    path('<int:pk>/clases/', views.clase_list, name='clase_list'),
    path('<int:pk>/clases/crear/', views.clase_create, name='clase_create'),
    path('clases/<int:pk>/', views.clase_detail, name='clase_detail'),
    path('clases/<int:pk>/editar/', views.clase_edit, name='clase_edit'),
    path('clases/<int:pk>/eliminar/', views.clase_delete, name='clase_delete'),
    path('clases/<int:pk>/completar/', views.clase_completar, name='clase_completar'),
]