from django.utils import timezone

from cursos.repository import CursoRepository
from kimun.data_access.base_repository import BaseRepository, deserializar, serializar
from kimun.data_access.dynamodb_client import DynamoDBClient
from usuarios.repository import UsuarioRepository


PRIORITY_LABELS = {
    "info": "Informativo",
    "aviso": "Aviso",
    "importante": "Importante",
    "urgente": "Urgente",
}


class AnuncioRepository(BaseRepository):
    entity_type = "ANNOUNCEMENT"
    key_prefix = "ANNOUNCEMENT"
    collection_key = "ENTITY#ANUNCIOS"

    @classmethod
    def enrich(cls, announcement, user_email=None):
        if not announcement:
            return None
        announcement = deserializar(announcement)
        announcement["curso"] = (
            CursoRepository.get_course(announcement.get("curso_id"))
            if announcement.get("curso_id")
            else None
        )
        announcement["creado_por"] = UsuarioRepository.get_by_email(
            announcement.get("creado_por_id")
        )
        announcement["get_prioridad_display"] = PRIORITY_LABELS.get(
            announcement.get("prioridad"), announcement.get("prioridad", "")
        )
        announcement["leido"] = (
            cls.is_read(announcement["id"], user_email) if user_email else False
        )
        return announcement

    @classmethod
    def list_visible(cls, user_email, role, course_ids=None):
        now = timezone.now()
        announcements = cls.all()
        if role not in {"admin", "docente"}:
            allowed = {str(item) for item in (course_ids or [])}
            announcements = [
                item
                for item in announcements
                if item.get("publicado")
                and (not item.get("curso_id") or item.get("curso_id") in allowed)
                and (
                    not item.get("fecha_expiracion")
                    or deserializar(item).get("fecha_expiracion") >= now
                )
            ]
        announcements.sort(
            key=lambda item: str(item.get("fecha_creacion", "")), reverse=True
        )
        return [cls.enrich(item, user_email) for item in announcements]

    @staticmethod
    def mark_read(announcement_id, user_email):
        item = {
            "PK": f"USER#{user_email}",
            "SK": f"ANNOUNCEMENT_READ#{announcement_id}",
            "anuncio_id": str(announcement_id),
            "usuario_id": user_email,
            "fecha_lectura": timezone.now(),
            "entity_type": "ANNOUNCEMENT_READ",
        }
        DynamoDBClient.put_item(serializar(item))
        return deserializar(item)

    @staticmethod
    def is_read(announcement_id, user_email):
        return bool(
            DynamoDBClient.get_item(
                f"USER#{user_email}", f"ANNOUNCEMENT_READ#{announcement_id}"
            )
        )
