from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from django.utils.dateparse import parse_date, parse_datetime

from kimun.data_access.dynamodb_client import DynamoDBClient


DATE_FIELDS = {
    "fecha_creacion",
    "fecha_actualizacion",
    "fecha_asignacion",
    "fecha_completado",
    "fecha_intento",
    "fecha_limite",
    "fecha_entrega",
    "fecha_calificacion",
    "fecha_emision",
    "fecha_aprobacion",
    "fecha_inicio",
    "fecha_fin",
    "fecha_publicacion",
    "fecha_expiracion",
    "hora_inicio",
}


def nuevo_id():
    return uuid4().hex


def serializar(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: serializar(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializar(item) for item in value]
    return value


def deserializar(value, field_name=None):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {key: deserializar(item, key) for key, item in value.items()}
    if isinstance(value, list):
        return [deserializar(item) for item in value]
    if isinstance(value, str) and field_name in DATE_FIELDS:
        return parse_datetime(value) or parse_date(value) or value
    return value


class BaseRepository:
    """Operaciones comunes para entidades raíz del diseño Single-Table."""

    entity_type = None
    key_prefix = None
    collection_key = None

    @classmethod
    def _pk(cls, identifier):
        return f"{cls.key_prefix}#{identifier}"

    @classmethod
    def _sk(cls, identifier):
        return f"METADATA#{identifier}"

    @classmethod
    def save(cls, data, identifier=None):
        identifier = str(identifier or data.get("id") or nuevo_id())
        item = {
            **data,
            "PK": cls._pk(identifier),
            "SK": cls._sk(identifier),
            "id": identifier,
            "pk": identifier,
            "entity_type": cls.entity_type,
        }
        if cls.collection_key:
            item["GSI1PK"] = cls.collection_key
            item["GSI1SK"] = f"{cls.key_prefix}#{identifier}"
        DynamoDBClient.put_item(serializar(item))
        return deserializar(item)

    @classmethod
    def get(cls, identifier):
        item = DynamoDBClient.get_item(cls._pk(identifier), cls._sk(identifier))
        return deserializar(item) if item else None

    @classmethod
    def all(cls):
        if not cls.collection_key:
            raise ValueError("El repositorio no define una colección consultable.")
        items = DynamoDBClient.query_gsi1(cls.collection_key)
        return [deserializar(item) for item in items]

    @classmethod
    def delete(cls, identifier):
        return DynamoDBClient.delete_item(cls._pk(identifier), cls._sk(identifier))

    @classmethod
    def update(cls, identifier, changes):
        current = cls.get(identifier)
        if current is None:
            return None
        protected = {"PK", "SK", "GSI1PK", "GSI1SK", "entity_type", "id", "pk"}
        clean = {key: value for key, value in current.items() if key not in protected}
        clean.update(changes)
        return cls.save(clean, identifier)
