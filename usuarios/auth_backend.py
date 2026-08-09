import hashlib

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password

from usuarios.repository import UsuarioRepository


class MetaUsuarioDynamoDB:
    class ClavePrimaria:
        @staticmethod
        def value_to_string(usuario):
            return str(usuario.pk)

    pk = ClavePrimaria()


class DynamoDBUser:
    """Adaptador de usuario compatible con la sesión de Django y sin ORM."""

    _meta = MetaUsuarioDynamoDB()

    def __init__(self, item):
        self.pk = item.get("email")
        self.id = self.pk
        self.email = self.pk
        self.username = item.get("username") or self.pk
        self.rol = item.get("rol", "colaborador")
        self.nombre = item.get("nombre", "")
        self.first_name = item.get("first_name", self.nombre)
        self.last_name = item.get("last_name", "")
        self.rut = item.get("rut", "")
        self.cargo_id = item.get("cargo_id", "")
        self.password_hash = item.get("password_hash", "")
        self.is_active = item.get("is_active", True)
        self.is_authenticated = True
        self.is_anonymous = False

    def get_full_name(self):
        nombre = " ".join(
            parte for parte in (self.first_name, self.last_name) if parte
        ).strip()
        return nombre or self.nombre or self.email

    @property
    def is_staff(self):
        return self.rol == "admin"

    @property
    def is_superuser(self):
        return self.rol == "admin"

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        """Django intenta registrar el último acceso; DynamoDB no requiere este paso."""

    def get_session_auth_hash(self):
        return hashlib.sha256(self.password_hash.encode("utf-8")).hexdigest()


class DynamoDBAuthBackend(BaseBackend):
    """Autentica y recupera usuarios exclusivamente desde DynamoDB."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if not email or not password:
            return None
        item = UsuarioRepository.get_by_email(email)
        if not item or not item.get("is_active", True):
            return None
        if check_password(password, item.get("password_hash", "")):
            return DynamoDBUser(item)
        return None

    def get_user(self, user_id):
        item = UsuarioRepository.get_by_email(user_id)
        if item and item.get("is_active", True):
            return DynamoDBUser(item)
        return None
