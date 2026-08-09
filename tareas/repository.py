from django.utils import timezone

from cursos.repository import CursoRepository
from kimun.data_access.base_repository import BaseRepository, deserializar, nuevo_id, serializar
from kimun.data_access.dynamodb_client import DynamoDBClient
from usuarios.repository import UsuarioRepository


SUBMISSION_STATUS_LABELS = {
    "enviado": "Enviado",
    "calificado": "Calificado",
    "devuelto": "Devuelto",
}


class TareaRepository(BaseRepository):
    entity_type = "TASK"
    key_prefix = "TASK"

    @classmethod
    def save_task(cls, data, task_id=None):
        identifier = str(task_id or nuevo_id())
        item = {
            **data,
            "PK": cls._pk(identifier),
            "SK": cls._sk(identifier),
            "GSI1PK": f"COURSE#{data['curso_id']}",
            "GSI1SK": f"TASK#{data.get('fecha_limite', '')}#{identifier}",
            "id": identifier,
            "pk": identifier,
            "entity_type": cls.entity_type,
            "fecha_creacion": data.get("fecha_creacion") or timezone.now(),
        }
        DynamoDBClient.put_item(serializar(item))
        return cls.enrich(item)

    @classmethod
    def enrich(cls, task):
        if not task:
            return None
        task = deserializar(task)
        task["curso"] = CursoRepository.get_course(task.get("curso_id"))
        task["creado_por"] = UsuarioRepository.get_by_email(task.get("creado_por_id"))
        return task

    @classmethod
    def get_task(cls, task_id):
        return cls.enrich(cls.get(task_id))

    @classmethod
    def list_by_course(cls, course_id):
        items = DynamoDBClient.query_gsi1(f"COURSE#{course_id}", "TASK#")
        tasks = [cls.enrich(item) for item in items]
        return sorted(tasks, key=lambda task: str(task.get("fecha_limite", "")))

    @classmethod
    def delete_task(cls, task_id):
        for submission in EntregaTareaRepository.list_by_task(task_id):
            DynamoDBClient.delete_item(submission["PK"], submission["SK"])
        return cls.delete(task_id)


class EntregaTareaRepository:
    @staticmethod
    def get(task_id, user_email):
        item = DynamoDBClient.get_item(
            f"USER#{user_email}", f"SUBMISSION#{task_id}"
        )
        return EntregaTareaRepository.enrich(item)

    @staticmethod
    def get_by_id(submission_id):
        users = UsuarioRepository.list_all()
        for user in users:
            items = DynamoDBClient.query_by_pk(f"USER#{user['email']}", "SUBMISSION#")
            for item in items:
                if item.get("id") == str(submission_id):
                    return EntregaTareaRepository.enrich(item)
        return None

    @staticmethod
    def save(data, submission_id=None):
        identifier = str(submission_id or data.get("id") or nuevo_id())
        task_id = str(data["tarea_id"])
        user_email = data["estudiante_id"]
        item = {
            **data,
            "PK": f"USER#{user_email}",
            "SK": f"SUBMISSION#{task_id}",
            "GSI1PK": f"TASK#{task_id}",
            "GSI1SK": f"SUBMISSION#{data.get('fecha_entrega') or timezone.now()}#{user_email}",
            "id": identifier,
            "pk": identifier,
            "estado": data.get("estado", "enviado"),
            "fecha_entrega": data.get("fecha_entrega") or timezone.now(),
            "entity_type": "TASK_SUBMISSION",
        }
        DynamoDBClient.put_item(serializar(item))
        return EntregaTareaRepository.enrich(item)

    @staticmethod
    def enrich(submission):
        if not submission:
            return None
        submission = deserializar(submission)
        submission["tarea"] = TareaRepository.get_task(submission.get("tarea_id"))
        submission["estudiante"] = UsuarioRepository.get_by_email(
            submission.get("estudiante_id")
        )
        submission["calificado_por"] = (
            UsuarioRepository.get_by_email(submission.get("calificado_por_id"))
            if submission.get("calificado_por_id")
            else None
        )
        submission["get_estado_display"] = SUBMISSION_STATUS_LABELS.get(
            submission.get("estado"), submission.get("estado", "")
        )
        return submission

    @staticmethod
    def list_by_task(task_id):
        items = DynamoDBClient.query_gsi1(f"TASK#{task_id}", "SUBMISSION#")
        return [EntregaTareaRepository.enrich(item) for item in items]

    @staticmethod
    def list_by_user(user_email):
        items = DynamoDBClient.query_by_pk(f"USER#{user_email}", "SUBMISSION#")
        return [EntregaTareaRepository.enrich(item) for item in items]
