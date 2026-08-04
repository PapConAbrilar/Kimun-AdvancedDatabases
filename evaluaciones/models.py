from django.db import models
from django.conf import settings


class BancoPreguntas(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    curso = models.ForeignKey('cursos.Curso', on_delete=models.CASCADE, null=True, blank=True, related_name='bancos_preguntas')
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bancos_creados')
    es_publico = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Banco de Preguntas'
        verbose_name_plural = 'Bancos de Preguntas'

    def __str__(self):
        return self.nombre


class Evaluacion(models.Model):
    curso = models.ForeignKey('cursos.Curso', on_delete=models.CASCADE, related_name='evaluaciones')
    titulo = models.CharField(max_length=200)
    porcentaje_aprobacion = models.IntegerField(default=70)
    max_intentos = models.IntegerField(default=0, help_text='0 = sin límite')
    duracion_minutos = models.IntegerField(null=True, blank=True, help_text='Minutos, vacío = sin límite')
    preguntas_por_intento = models.IntegerField(null=True, blank=True, help_text='Aleatorizar N preguntas del banco')

    class Meta:
        verbose_name = 'Evaluación'
        verbose_name_plural = 'Evaluaciones'

    def __str__(self):
        return f"{self.titulo} - {self.curso.titulo}"


class Pregunta(models.Model):
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='preguntas', null=True, blank=True)
    banco = models.ForeignKey(BancoPreguntas, on_delete=models.SET_NULL, null=True, blank=True, related_name='preguntas')
    texto = models.TextField()

    class Meta:
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'

    def __str__(self):
        return self.texto[:50]


class Alternativa(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='alternativas')
    texto = models.CharField(max_length=500)
    es_correcta = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Alternativa'
        verbose_name_plural = 'Alternativas'

    def __str__(self):
        return f"{self.texto[:30]}... ({'Correcta' if self.es_correcta else 'Incorrecta'})"


class IntentoEvaluacion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='intentos_evaluacion')
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='intentos')
    puntaje_obtenido = models.IntegerField()
    aprobado = models.BooleanField(default=False)
    fecha_intento = models.DateTimeField(auto_now_add=True)
    hora_inicio = models.DateTimeField(null=True, blank=True)
    respuestas = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Intento de Evaluación'
        verbose_name_plural = 'Intentos de Evaluación'

    def __str__(self):
        return f"{self.usuario} - {self.evaluacion.titulo} ({self.puntaje_obtenido}%)"
