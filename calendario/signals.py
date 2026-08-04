from typing import Any, cast

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import EventoCalendario, TipoEvento
from cursos.models import Curso
from evaluaciones.models import Evaluacion
from tareas.models import Tarea

EventoCalendarioModel = cast(Any, EventoCalendario)
TareaModel = cast(Any, Tarea)


@receiver(post_save, sender=Curso)
def crear_eventos_curso(sender, instance, created, **kwargs):
    """Crea eventos de calendario cuando se crea o actualiza un curso."""
    if created:
        EventoCalendarioModel.objects.create(
            titulo=f"Inicio: {instance.titulo}",
            descripcion=f"El curso '{instance.titulo}' ha sido publicado",
            tipo=TipoEvento.CURSO_START,
            fecha_inicio=instance.fecha_creacion,
            fecha_fin=instance.fecha_creacion,
            curso=instance,
            creado_por=instance.docente_creador,
            color='#22c55e'
        )
    
    if instance.fecha_limite:
        EventoCalendarioModel.objects.filter(curso=instance, tipo=TipoEvento.CURSO_END).delete()
        EventoCalendarioModel.objects.create(
            titulo=f"Fecha límite: {instance.titulo}",
            descripcion=f"Fecha límite para completar el curso '{instance.titulo}'",
            tipo=TipoEvento.CURSO_END,
            fecha_inicio=instance.fecha_limite,
            fecha_fin=instance.fecha_limite,
            curso=instance,
            creado_por=instance.docente_creador,
            color='#ef4444'
        )


@receiver(post_delete, sender=Curso)
def eliminar_eventos_curso(sender, instance, **kwargs):
    """Elimina todos los eventos de calendario asociados al curso eliminado."""
    EventoCalendarioModel.objects.filter(curso=instance).delete()


@receiver(post_save, sender=Evaluacion)
def crear_evento_evaluacion(sender, instance, created, **kwargs):
    """Crea evento de calendario cuando se crea una evaluación."""
    if created:
        from django.utils import timezone
        from datetime import timedelta
        fecha_limite = instance.curso.fecha_limite or (timezone.now() + timedelta(days=7))
        
        EventoCalendarioModel.objects.create(
            titulo=f"Evaluación: {instance.titulo}",
            descripcion=f"Fecha límite para completar la evaluación '{instance.titulo}'",
            tipo=TipoEvento.EVALUACION_DEADLINE,
            fecha_inicio=fecha_limite,
            fecha_fin=fecha_limite,
            curso=instance.curso,
            evaluacion=instance,
            creado_por=instance.curso.docente_creador,
            color='#f59e0b'
        )


@receiver(post_delete, sender=Evaluacion)
def eliminar_evento_evaluacion(sender, instance, **kwargs):
    """Elimina el evento de calendario asociado a la evaluación eliminada."""
    EventoCalendarioModel.objects.filter(evaluacion=instance).delete()


@receiver(pre_save, sender=Tarea)
def preparar_evento_tarea(sender, instance, **kwargs):
    if not instance.pk:
        instance._evento_tarea_filtro = None
        return

    tarea_anterior = TareaModel.objects.filter(pk=instance.pk).first()
    if tarea_anterior:
        instance._evento_tarea_filtro = {
            'titulo': f"Tarea: {tarea_anterior.titulo}",
            'descripcion': tarea_anterior.descripcion,
            'tipo': TipoEvento.CLASE_DEADLINE,
            'fecha_inicio': tarea_anterior.fecha_limite,
            'fecha_fin': tarea_anterior.fecha_limite,
            'curso': tarea_anterior.curso,
            'creado_por': tarea_anterior.creado_por,
            'color': '#6366f1',
        }


@receiver(post_save, sender=Tarea)
def crear_evento_tarea(sender, instance, created, **kwargs):
    if not created and getattr(instance, '_evento_tarea_filtro', None):
        EventoCalendarioModel.objects.filter(**instance._evento_tarea_filtro).delete()

    EventoCalendarioModel.objects.create(
        titulo=f"Tarea: {instance.titulo}",
        descripcion=instance.descripcion,
        tipo=TipoEvento.CLASE_DEADLINE,
        fecha_inicio=instance.fecha_limite,
        fecha_fin=instance.fecha_limite,
        curso=instance.curso,
        creado_por=instance.creado_por,
        color='#6366f1'
    )


@receiver(post_delete, sender=Tarea)
def eliminar_evento_tarea(sender, instance, **kwargs):
    EventoCalendarioModel.objects.filter(
        titulo=f"Tarea: {instance.titulo}",
        descripcion=instance.descripcion,
        tipo=TipoEvento.CLASE_DEADLINE,
        fecha_inicio=instance.fecha_limite,
        fecha_fin=instance.fecha_limite,
        curso=instance.curso,
        creado_por=instance.creado_por,
        color='#6366f1'
    ).delete()


@receiver(post_save)
def sincronizar_evento_anuncio(sender, instance, **kwargs):
    from anuncios.models import Anuncio
    from django.utils import timezone

    if sender is not Anuncio:
        return

    eventos = EventoCalendarioModel.objects.filter(
        titulo__startswith=f'Anuncio [{instance.pk}]: ',
        tipo=TipoEvento.EVENTO_GENERAL,
        color='#8b5cf6',
    )

    if instance.curso_id:
        eventos = eventos.filter(curso=instance.curso)
    else:
        eventos = eventos.filter(curso__isnull=True)

    eventos.delete()

    if not instance.publicado or not instance.fecha_expiracion:
        return

    EventoCalendarioModel.objects.create(
        titulo=f"Anuncio [{instance.pk}]: {instance.titulo}",
        descripcion=instance.contenido[:200],
        tipo=TipoEvento.EVENTO_GENERAL,
        fecha_inicio=instance.fecha_publicacion or timezone.now(),
        fecha_fin=instance.fecha_expiracion,
        curso=instance.curso,
        creado_por=instance.creado_por,
        color='#8b5cf6'
    )


@receiver(post_delete)
def eliminar_evento_anuncio(sender, instance, **kwargs):
    from anuncios.models import Anuncio

    if sender is not Anuncio:
        return

    eventos = EventoCalendarioModel.objects.filter(
        titulo__startswith=f'Anuncio [{instance.pk}]: ',
        tipo=TipoEvento.EVENTO_GENERAL,
        color='#8b5cf6',
    )

    if instance.curso_id:
        eventos = eventos.filter(curso=instance.curso)
    else:
        eventos = eventos.filter(curso__isnull=True)

    eventos.delete()
