from django.db import models
from django.conf import settings


class Tarea(models.Model):
    curso = models.ForeignKey('cursos.Curso', on_delete=models.CASCADE, related_name='tareas')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    fecha_limite = models.DateTimeField(verbose_name='Fecha límite')
    puntaje_maximo = models.IntegerField(default=100)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tareas_creadas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'
        ordering = ['fecha_limite']

    def __str__(self):
        return f"{self.titulo} - {self.curso.titulo}"


class EntregaTarea(models.Model):
    ESTADO_CHOICES = [
        ('enviado', 'Enviado'),
        ('calificado', 'Calificado'),
        ('devuelto', 'Devuelto'),
    ]
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name='entregas')
    estudiante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='entregas')
    archivo = models.FileField(upload_to='entregas/%Y/%m/', blank=True)
    comentario = models.TextField(blank=True, default='')
    fecha_entrega = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='enviado')
    puntaje_obtenido = models.IntegerField(null=True, blank=True)
    retroalimentacion = models.TextField(blank=True, default='')
    calificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='entregas_calificadas')
    fecha_calificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Entrega de Tarea'
        verbose_name_plural = 'Entregas de Tareas'
        unique_together = ['tarea', 'estudiante']

    def __str__(self):
        return f"{self.estudiante} - {self.tarea.titulo} ({self.get_estado_display()})"
