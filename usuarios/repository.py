from django.utils import timezone

from kimun.data_access.base_repository import BaseRepository, deserializar, serializar
from kimun.data_access.dynamodb_client import DynamoDBClient


ROLE_LABELS = {
    "admin": "Administrador",
    "docente": "Docente",
    "colaborador": "Colaborador",
    "alumno": "Colaborador",
}


def present_user(item):
    if not item:
        return None
    user = deserializar(item)
    email = user.get("email") or user.get("username") or user.get("id")
    first_name = user.get("first_name") or user.get("nombre", "")
    last_name = user.get("last_name", "")
    full_name = " ".join(part for part in (first_name, last_name) if part).strip()
    user.update(
        {
            "id": email,
            "pk": email,
            "email": email,
            "username": user.get("username") or email,
            "first_name": first_name,
            "last_name": last_name,
            "nombre": full_name or email,
            "get_full_name": full_name,
            "get_rol_display": ROLE_LABELS.get(user.get("rol"), user.get("rol", "")),
            "is_active": user.get("is_active", True),
        }
    )
    return user


class AreaCargoRepository(BaseRepository):
    entity_type = "AREA_CARGO"
    key_prefix = "AREA"
    collection_key = "ENTITY#AREAS"

    @classmethod
    def list_all(cls):
        return sorted(cls.all(), key=lambda area: area.get("nombre", "").lower())


class UsuarioRepository(BaseRepository):
    entity_type = "USER_PROFILE"
    key_prefix = "USER"
    collection_key = "ENTITY#USUARIOS"

    @classmethod
    def _sk(cls, identifier):
        return f"PROFILE#{identifier}"

    @classmethod
    def save(cls, data, identifier=None):
        email = str(identifier or data.get("email") or data.get("username"))
        item = {
            **data,
            "PK": cls._pk(email),
            "SK": cls._sk(email),
            "GSI1PK": cls.collection_key,
            "GSI1SK": f"USER#{email}",
            "id": email,
            "pk": email,
            "email": email,
            "username": data.get("username") or email,
            "entity_type": cls.entity_type,
        }
        DynamoDBClient.put_item(serializar(item))
        return present_user(item)

    @classmethod
    def get_by_email(cls, email):
        return present_user(DynamoDBClient.get_item(cls._pk(email), cls._sk(email)))

    @classmethod
    def get(cls, identifier):
        return cls.get_by_email(identifier)

    @classmethod
    def list_all(cls, role=None, active_only=False):
        users = [present_user(item) for item in DynamoDBClient.query_gsi1(cls.collection_key)]
        if role:
            users = [user for user in users if user.get("rol") == role]
        if active_only:
            users = [user for user in users if user.get("is_active", True)]
        return sorted(users, key=lambda user: user.get("nombre", "").lower())

    @classmethod
    def create_user(
        cls,
        email,
        password_hash,
        rol="colaborador",
        nombre="",
        is_active=True,
        rut="",
        first_name="",
        last_name="",
        cargo_id=None,
    ):
        if cls.get_by_email(email):
            raise ValueError("Ya existe un usuario con ese correo electrónico.")
        if nombre and not first_name:
            first_name = nombre
        return cls.save(
            {
                "password_hash": password_hash,
                "rol": rol,
                "nombre": nombre or " ".join((first_name, last_name)).strip(),
                "first_name": first_name,
                "last_name": last_name,
                "rut": rut,
                "cargo_id": cargo_id or "",
                "is_active": is_active,
                "date_joined": timezone.now(),
            },
            email,
        )

    @classmethod
    def update_user(cls, email, changes):
        current = cls.get_by_email(email)
        if not current:
            return None
        protected = {"PK", "SK", "GSI1PK", "GSI1SK", "entity_type", "id", "pk"}
        data = {key: value for key, value in current.items() if key not in protected}
        data.update(changes)
        return cls.save(data, email)

    @classmethod
    def delete_user(cls, email):
        return DynamoDBClient.delete_partition(cls._pk(email))

    @classmethod
    def count(cls, role=None):
        return len(cls.list_all(role=role))

    @classmethod
    def save_reminder(cls, email, course_id, reminder_type):
        item = {
            "PK": cls._pk(email),
            "SK": f"REMINDER#{course_id}#{reminder_type}",
            "email": email,
            "curso_id": str(course_id),
            "tipo": reminder_type,
            "fecha_envio": timezone.now(),
            "entity_type": "REMINDER",
        }
        DynamoDBClient.put_item(serializar(item))
        return deserializar(item)

    @classmethod
    def reminder_exists(cls, email, course_id, reminder_type):
        return bool(
            DynamoDBClient.get_item(
                cls._pk(email), f"REMINDER#{course_id}#{reminder_type}"
            )
        )
