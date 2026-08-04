from django.contrib import admin
from .models import Tarea, EntregaTarea


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'fecha_limite', 'puntaje_maximo', 'creado_por', 'fecha_creacion')
    list_filter = ('fecha_limite', 'fecha_creacion', 'curso')
    search_fields = ('titulo', 'descripcion', 'curso__titulo')
    date_hierarchy = 'fecha_limite'


@admin.register(EntregaTarea)
class EntregaTareaAdmin(admin.ModelAdmin):
    list_display = ('tarea', 'estudiante', 'estado', 'puntaje_obtenido', 'fecha_entrega', 'calificado_por')
    list_filter = ('estado', 'fecha_entrega', 'fecha_calificacion')
    search_fields = ('estudiante__username', 'estudiante__first_name', 'tarea__titulo', 'comentario')
    readonly_fields = ('fecha_entrega',)
