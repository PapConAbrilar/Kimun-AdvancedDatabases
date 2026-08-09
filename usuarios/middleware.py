from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import (
    BACKEND_SESSION_KEY,
    HASH_SESSION_KEY,
    SESSION_KEY,
    load_backend,
)
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.utils.crypto import constant_time_compare
from django.utils.functional import SimpleLazyObject


def get_dynamodb_user(request):
    """Recupera el usuario sin convertir su correo a una clave primaria SQL."""

    user_id = request.session.get(SESSION_KEY)
    backend_path = request.session.get(BACKEND_SESSION_KEY)
    if not user_id or not backend_path:
        return AnonymousUser()
    if backend_path not in settings.AUTHENTICATION_BACKENDS:
        return AnonymousUser()

    backend = load_backend(backend_path)
    user = backend.get_user(user_id)
    if user is None:
        return AnonymousUser()

    session_hash = request.session.get(HASH_SESSION_KEY, "")
    current_hash = user.get_session_auth_hash()
    if session_hash and not constant_time_compare(session_hash, current_hash):
        request.session.flush()
        return AnonymousUser()
    return user


class DynamoDBAuthenticationMiddleware:
    """Middleware de autenticación para identificadores de usuario tipo correo."""

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(request, "session"):
            raise ImproperlyConfigured(
                "DynamoDBAuthenticationMiddleware requiere SessionMiddleware."
            )
        request.user = SimpleLazyObject(lambda: get_dynamodb_user(request))
        request.auser = lambda: sync_to_async(get_dynamodb_user)(request)
        return self.get_response(request)
