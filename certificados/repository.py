from uuid import uuid4

from django.utils import timezone

from cursos.repository import CursoRepository
from kimun.data_access.base_repository import BaseRepository, deserializar, serializar
from kimun.data_access.dynamodb_client import DynamoDBClient
from usuarios.repository import UsuarioRepository


CERTIFICATE_STATUS_LABELS = {
    "pendiente": "Pendiente",
    "aprobado": "Aprobado",
    "rechazado": "Rechazado",
}


class CertificadoRepository(BaseRepository):
    entity_type = "CERTIFICATE"
    key_prefix = "CERTIFICATE"
    collection_key = "ENTITY#CERTIFICADOS"

    @classmethod
    def enrich(cls, certificate):
        if not certificate:
            return None
        certificate = deserializar(certificate)
        certificate["usuario"] = UsuarioRepository.get_by_email(
            certificate.get("usuario_id")
        )
        certificate["curso"] = CursoRepository.get_course(certificate.get("curso_id"))
        certificate["aprobado_por"] = (
            UsuarioRepository.get_by_email(certificate.get("aprobado_por_id"))
            if certificate.get("aprobado_por_id")
            else None
        )
        certificate["get_estado_display"] = CERTIFICATE_STATUS_LABELS.get(
            certificate.get("estado"), certificate.get("estado", "")
        )
        return certificate

    @classmethod
    def create(cls, user_email, course_id, state="pendiente"):
        existing = cls.get_for_user_course(user_email, course_id)
        if existing:
            return existing, False
        certificate = cls.save(
            {
                "usuario_id": user_email,
                "curso_id": str(course_id),
                "codigo_verificacion": str(uuid4()),
                "fecha_emision": timezone.now(),
                "estado": state,
                "fecha_aprobacion": None,
                "aprobado_por_id": "",
            }
        )
        return cls.enrich(certificate), True

    @classmethod
    def get_certificate(cls, certificate_id):
        return cls.enrich(cls.get(certificate_id))

    @classmethod
    def list_all(cls, state=None):
        certificates = cls.all()
        if state:
            certificates = [item for item in certificates if item.get("estado") == state]
        return [cls.enrich(item) for item in certificates]

    @classmethod
    def list_by_user(cls, user_email, state=None):
        certificates = [
            item for item in cls.all() if item.get("usuario_id") == user_email
        ]
        if state:
            certificates = [item for item in certificates if item.get("estado") == state]
        return [cls.enrich(item) for item in certificates]

    @classmethod
    def get_for_user_course(cls, user_email, course_id):
        return next(
            (
                item
                for item in cls.list_by_user(user_email)
                if item.get("curso_id") == str(course_id)
            ),
            None,
        )

    @classmethod
    def get_by_verification_code(cls, code):
        code = str(code)
        return next(
            (item for item in cls.list_all() if item.get("codigo_verificacion") == code),
            None,
        )

    @classmethod
    def set_status(cls, certificate_id, state, approved_by=None):
        changes = {"estado": state}
        if state == "aprobado":
            changes.update(
                {
                    "fecha_aprobacion": timezone.now(),
                    "aprobado_por_id": approved_by or "",
                }
            )
        else:
            changes.update({"fecha_aprobacion": None, "aprobado_por_id": ""})
        return cls.enrich(cls.update(certificate_id, changes))

    @classmethod
    def count(cls):
        return len(cls.all())
