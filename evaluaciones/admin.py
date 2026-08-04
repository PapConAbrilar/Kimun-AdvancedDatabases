from django.contrib import admin
from .models import Evaluacion, Pregunta, Alternativa, IntentoEvaluacion


class AlternativaInline(admin.TabularInline):
    model = Alternativa
    extra = 2
    fields = ('texto', 'es_correcta')
    verbose_name_plural = 'Alternativas'


@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'porcentaje_aprobacion')
    list_filter = ('curso',)
    search_fields = ('titulo', 'curso__titulo')


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('texto', 'evaluacion')
    list_filter = ('evaluacion',)
    inlines = [AlternativaInline]


@admin.register(Alternativa)
class AlternativaAdmin(admin.ModelAdmin):
    list_display = ('texto', 'pregunta', 'es_correcta')
    list_filter = ('es_correcta',)
    search_fields = ('texto',)


@admin.register(IntentoEvaluacion)
class IntentoEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'evaluacion', 'puntaje_obtenido', 'aprobado', 'fecha_intento')
    list_filter = ('aprobado', 'fecha_intento')
    search_fields = ('usuario__username', 'evaluacion__titulo')