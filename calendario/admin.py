from django.contrib import admin
from .models import EventoCalendario


@admin.register(EventoCalendario)
class EventoCalendarioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'fecha_inicio', 'fecha_fin', 'creado_por')
    list_filter = ('tipo', 'fecha_inicio', 'creado_por')
    search_fields = ('titulo', 'descripcion')
    date_hierarchy = 'fecha_inicio'
