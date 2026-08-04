from django.db import models
from django.conf import settings


class TipoEvento(models.TextChoices):
    CLASE_DEADLINE = 'clase_deadline', 'Plazo de Clase'
    EVALUACION_DEADLINE = 'evaluacion_deadline', 'Plazo de Evaluación'
    CURSO_START = 'curso_start', 'Inicio de Curso'
    CURSO_END = 'curso_end', 'Fin de Curso'
    EVENTO_GENERAL = 'evento_general', 'Evento General'


class EventoCalendario(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    tipo = models.CharField(max_length=25, choices=TipoEvento.choices, default=TipoEvento.EVENTO_GENERAL)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    curso = models.ForeignKey('cursos.Curso', on_delete=models.CASCADE, null=True, blank=True, related_name='eventos_calendario')
    evaluacion = models.ForeignKey('evaluaciones.Evaluacion', on_delete=models.CASCADE, null=True, blank=True, related_name='eventos_calendario')
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='eventos_creados')
    color = models.CharField(max_length=7, default='#6366f1', help_text='Color hex, ej: #6366f1')

    class Meta:
        verbose_name = 'Evento de Calendario'
        verbose_name_plural = 'Eventos de Calendario'
        ordering = ['fecha_inicio']

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()})"
