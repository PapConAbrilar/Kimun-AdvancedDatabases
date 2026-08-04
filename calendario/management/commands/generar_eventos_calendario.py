from django.core.management.base import BaseCommand
from cursos.models import Curso
from evaluaciones.models import Evaluacion
from calendario.models import EventoCalendario, TipoEvento
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Genera eventos de calendario para cursos y evaluaciones existentes'

    def handle(self, *args, **options):
        count = 0
        
        for curso in Curso.objects.all():
            if not EventoCalendario.objects.filter(curso=curso, tipo=TipoEvento.CURSO_START).exists():
                EventoCalendario.objects.create(
                    titulo=f"Inicio: {curso.titulo}",
                    descripcion=f"El curso '{curso.titulo}' ha sido publicado",
                    tipo=TipoEvento.CURSO_START,
                    fecha_inicio=curso.fecha_creacion,
                    fecha_fin=curso.fecha_creacion,
                    curso=curso,
                    creado_por=curso.docente_creador,
                    color='#22c55e'
                )
                count += 1
            
            if curso.fecha_limite and not EventoCalendario.objects.filter(curso=curso, tipo=TipoEvento.CURSO_END).exists():
                EventoCalendario.objects.create(
                    titulo=f"Fecha límite: {curso.titulo}",
                    descripcion=f"Fecha límite para completar el curso '{curso.titulo}'",
                    tipo=TipoEvento.CURSO_END,
                    fecha_inicio=curso.fecha_limite,
                    fecha_fin=curso.fecha_limite,
                    curso=curso,
                    creado_por=curso.docente_creador,
                    color='#ef4444'
                )
                count += 1
        
        for evaluacion in Evaluacion.objects.all():
            if not EventoCalendario.objects.filter(evaluacion=evaluacion).exists():
                fecha_limite = evaluacion.curso.fecha_limite or (timezone.now() + timedelta(days=7))
                EventoCalendario.objects.create(
                    titulo=f"Evaluación: {evaluacion.titulo}",
                    descripcion=f"Fecha límite para completar la evaluación '{evaluacion.titulo}'",
                    tipo=TipoEvento.EVALUACION_DEADLINE,
                    fecha_inicio=fecha_limite,
                    fecha_fin=fecha_limite,
                    curso=evaluacion.curso,
                    evaluacion=evaluacion,
                    creado_por=evaluacion.curso.docente_creador,
                    color='#f59e0b'
                )
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Se generaron {count} eventos de calendario'))
