from django.conf import settings
from django.db import models


class Anuncio(models.Model):
    PRIORIDAD_CHOICES = [
        ('info', 'Informativo'),
        ('aviso', 'Aviso'),
        ('importante', 'Importante'),
        ('urgente', 'Urgente'),
    ]

    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    prioridad = models.CharField(max_length=15, choices=PRIORIDAD_CHOICES, default='info')
    curso = models.ForeignKey('cursos.Curso', on_delete=models.CASCADE, null=True, blank=True, related_name='anuncios')
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='anuncios_creados')
    publicado = models.BooleanField(default=False)  # type: ignore[reportArgumentType]
    fecha_publicacion = models.DateTimeField(null=True, blank=True)
    fecha_expiracion = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Anuncio'
        verbose_name_plural = 'Anuncios'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return str(self.titulo)


class LecturaAnuncio(models.Model):
    anuncio = models.ForeignKey(Anuncio, on_delete=models.CASCADE, related_name='lecturas')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='anuncios_leidos')
    fecha_lectura = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['anuncio', 'usuario']

    def __str__(self):
        return f'{self.usuario} - {self.anuncio}'
