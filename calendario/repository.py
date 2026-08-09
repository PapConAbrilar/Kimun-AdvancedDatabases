from datetime import timedelta

from django.utils import timezone

from cursos.repository import CursoRepository
from evaluaciones.repository import EvaluacionRepository
from kimun.data_access.base_repository import BaseRepository, deserializar
from usuarios.repository import UsuarioRepository


EVENT_TYPE_LABELS = {
    "clase_deadline": "Plazo de clase",
    "evaluacion_deadline": "Plazo de evaluación",
    "curso_start": "Inicio de curso",
    "curso_end": "Fin de curso",
    "evento_general": "Evento general",
}


class CalendarioRepository(BaseRepository):
    entity_type = "CALENDAR_EVENT"
    key_prefix = "EVENT"
    collection_key = "ENTITY#EVENTOS"

    @classmethod
    def enrich(cls, event):
        if not event:
            return None
        event = deserializar(event)
        event["curso"] = (
            CursoRepository.get_course(event.get("curso_id"))
            if event.get("curso_id")
            else None
        )
        event["evaluacion"] = (
            EvaluacionRepository.get_evaluation(
                event.get("evaluacion_id"), with_questions=False
            )
            if event.get("evaluacion_id")
            else None
        )
        event["creado_por"] = UsuarioRepository.get_by_email(
            event.get("creado_por_id")
        )
        event["get_tipo_display"] = EVENT_TYPE_LABELS.get(
            event.get("tipo"), event.get("tipo", "")
        )
        return event

    @classmethod
    def list_events(cls, course_ids=None, start=None, end=None):
        events = cls.all()
        if course_ids is not None:
            allowed = {str(item) for item in course_ids}
            events = [
                event
                for event in events
                if not event.get("curso_id") or event.get("curso_id") in allowed
            ]
        if start:
            events = [event for event in events if event.get("fecha_fin") >= start]
        if end:
            events = [event for event in events if event.get("fecha_inicio") <= end]
        events.sort(key=lambda event: event.get("fecha_inicio"))
        return [cls.enrich(event) for event in events]

    @classmethod
    def get_event(cls, event_id):
        return cls.enrich(cls.get(event_id))

    @classmethod
    def save_by_origin(cls, origin_id, data):
        existing = next(
            (item for item in cls.all() if item.get("origen_id") == origin_id),
            None,
        )
        identifier = existing["id"] if existing else None
        return cls.save({**data, "origen_id": origin_id}, identifier)

    @classmethod
    def delete_by_origin(cls, origin_id):
        deleted = 0
        for item in cls.all():
            if item.get("origen_id") == origin_id:
                cls.delete(item["id"])
                deleted += 1
        return deleted

    @classmethod
    def sync_course(cls, course):
        course_id = course["id"]
        author_id = course.get("docente_creador_id", "")
        created_at = course.get("fecha_creacion") or timezone.now()
        cls.save_by_origin(
            f"curso-inicio-{course_id}",
            {
                "titulo": f"Inicio: {course['titulo']}",
                "descripcion": f"El curso '{course['titulo']}' ha sido publicado",
                "tipo": "curso_start",
                "fecha_inicio": created_at,
                "fecha_fin": created_at,
                "curso_id": course_id,
                "creado_por_id": author_id,
                "color": "#22c55e",
            },
        )
        end = course.get("fecha_limite")
        origin = f"curso-fin-{course_id}"
        if not end:
            cls.delete_by_origin(origin)
            return
        cls.save_by_origin(
            origin,
            {
                "titulo": f"Fecha límite: {course['titulo']}",
                "descripcion": f"Fecha límite para completar el curso '{course['titulo']}'",
                "tipo": "curso_end",
                "fecha_inicio": end,
                "fecha_fin": end,
                "curso_id": course_id,
                "creado_por_id": author_id,
                "color": "#ef4444",
            },
        )

    @classmethod
    def sync_task(cls, task):
        deadline = task.get("fecha_limite")
        origin = f"tarea-{task['id']}"
        if not deadline:
            cls.delete_by_origin(origin)
            return
        cls.save_by_origin(
            origin,
            {
                "titulo": f"Tarea: {task['titulo']}",
                "descripcion": task.get("descripcion", ""),
                "tipo": "clase_deadline",
                "fecha_inicio": deadline,
                "fecha_fin": deadline,
                "curso_id": task.get("curso_id", ""),
                "creado_por_id": task.get("creado_por_id", ""),
                "color": "#6366f1",
            },
        )

    @classmethod
    def sync_evaluation(cls, evaluation):
        course = evaluation.get("curso") or CursoRepository.get_course(
            evaluation.get("curso_id")
        )
        deadline = course.get("fecha_limite") if course else None
        deadline = deadline or timezone.now() + timedelta(days=7)
        cls.save_by_origin(
            f"evaluacion-{evaluation['id']}",
            {
                "titulo": f"Evaluación: {evaluation['titulo']}",
                "descripcion": f"Fecha límite para completar la evaluación '{evaluation['titulo']}'",
                "tipo": "evaluacion_deadline",
                "fecha_inicio": deadline,
                "fecha_fin": deadline,
                "curso_id": evaluation.get("curso_id", ""),
                "evaluacion_id": evaluation["id"],
                "creado_por_id": evaluation.get("creado_por_id", ""),
                "color": "#f59e0b",
            },
        )

    @classmethod
    def sync_announcement(cls, announcement):
        origin = f"anuncio-{announcement['id']}"
        if not announcement.get("publicado") or not announcement.get("fecha_expiracion"):
            cls.delete_by_origin(origin)
            return
        cls.save_by_origin(
            origin,
            {
                "titulo": f"Anuncio: {announcement['titulo']}",
                "descripcion": announcement.get("contenido", "")[:200],
                "tipo": "evento_general",
                "fecha_inicio": announcement.get("fecha_publicacion") or timezone.now(),
                "fecha_fin": announcement["fecha_expiracion"],
                "curso_id": announcement.get("curso_id", ""),
                "creado_por_id": announcement.get("creado_por_id", ""),
                "color": "#8b5cf6",
            },
        )
