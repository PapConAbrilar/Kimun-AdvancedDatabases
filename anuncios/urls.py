from django.urls import path

from .views import (
    anuncio_create,
    anuncio_delete,
    anuncio_detail,
    anuncio_edit,
    anuncio_list,
    marcar_leido,
)

app_name = 'anuncios'

urlpatterns = [
    path('', anuncio_list, name='anuncio_list'),
    path('crear/', anuncio_create, name='anuncio_create'),
    path('<str:pk>/', anuncio_detail, name='anuncio_detail'),
    path('<str:pk>/editar/', anuncio_edit, name='anuncio_edit'),
    path('<str:pk>/eliminar/', anuncio_delete, name='anuncio_delete'),
    path('<str:pk>/marcar-leido/', marcar_leido, name='marcar_leido'),
]
