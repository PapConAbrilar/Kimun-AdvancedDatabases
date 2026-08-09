from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from calendario.repository import CalendarioRepository
from cursos.repository import CursoRepository
from evaluaciones.repository import EvaluacionRepository


class Command(BaseCommand):
    help = "Genera en DynamoDB los eventos de cursos y evaluaciones existentes"

    def handle(self, *args, **options):
        creados = 0
        existentes = CalendarioRepository.all()

        for curso in CursoRepository.get_all_courses(enrich=False):
            inicio_id = f"curso-inicio-{curso['id']}"
            if not any(item.get("origen_id") == inicio_id for item in existentes):
                CalendarioRepository.save(
                    {
                        "titulo": f"Inicio: {curso['titulo']}",
                        "descripcion": f"El curso '{curso['titulo']}' ha sido publicado",
                        "tipo": "curso_start",
                        "fecha_inicio": curso["fecha_creacion"],
                        "fecha_fin": curso["fecha_creacion"],
                        "curso_id": curso["id"],
                        "creado_por_id": curso.get("docente_creador_id", ""),
                        "color": "#22c55e",
                        "origen_id": inicio_id,
                    }
                )
                creados += 1

            fecha_limite = curso.get("fecha_limite")
            fin_id = f"curso-fin-{curso['id']}"
            if fecha_limite and not any(
                item.get("origen_id") == fin_id for item in existentes
            ):
                CalendarioRepository.save(
                    {
                        "titulo": f"Fecha límite: {curso['titulo']}",
                        "descripcion": f"Fecha límite para completar el curso '{curso['titulo']}'",
                        "tipo": "curso_end",
                        "fecha_inicio": fecha_limite,
                        "fecha_fin": fecha_limite,
                        "curso_id": curso["id"],
                        "creado_por_id": curso.get("docente_creador_id", ""),
                        "color": "#ef4444",
                        "origen_id": fin_id,
                    }
                )
                creados += 1

            for evaluacion in EvaluacionRepository.list_by_course(
                curso["id"], with_questions=False
            ):
                origen_id = f"evaluacion-{evaluacion['id']}"
                if any(item.get("origen_id") == origen_id for item in existentes):
                    continue
                limite = fecha_limite or timezone.now() + timedelta(days=7)
                CalendarioRepository.save(
                    {
                        "titulo": f"Evaluación: {evaluacion['titulo']}",
                        "descripcion": f"Fecha límite para completar la evaluación '{evaluacion['titulo']}'",
                        "tipo": "evaluacion_deadline",
                        "fecha_inicio": limite,
                        "fecha_fin": limite,
                        "curso_id": curso["id"],
                        "evaluacion_id": evaluacion["id"],
                        "creado_por_id": curso.get("docente_creador_id", ""),
                        "color": "#f59e0b",
                        "origen_id": origen_id,
                    }
                )
                creados += 1

        self.stdout.write(
            self.style.SUCCESS(f"Se generaron {creados} eventos en DynamoDB.")
        )
