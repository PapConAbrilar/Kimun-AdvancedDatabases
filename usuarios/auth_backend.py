from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from usuarios.repository import UsuarioRepository

class DynamoDBUser:
    """
    Objeto simulado (Duck-Typing) que se hace pasar por un usuario de Django.
    Evita que el framework se rompa al no usar el ORM relacional.
    """
    def __init__(self, item):
        self.pk = item.get('email')  # Django necesita un identificador 'pk'
        self.id = self.pk
        self.email = item.get('email')
        self.rol = item.get('rol', 'alumno')
        self.nombre = item.get('nombre', '')
        self.is_active = item.get('is_active', True)
        self.is_authenticated = True
        self.is_anonymous = False
        
    @property
    def is_staff(self):
        return self.rol == 'admin'
        
    @property
    def is_superuser(self):
        return self.rol == 'admin'
        
    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Evita errores si Django intenta guardar el 'last_login'
        pass


class DynamoDBAuthBackend(BaseBackend):
    """
    Backend de autenticación 100% NoSQL.
    Ignora SQLite y busca los usuarios directamente en DynamoDB.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # En nuestro diseño, el username es el email
        email = username
        if not email or not password:
            return None
            
        # Buscar en DynamoDB
        user_item = UsuarioRepository.get_by_email(email)
        
        if user_item:
            password_hash = user_item.get('password_hash')
            # Verificar la contraseña encriptada
            if check_password(password, password_hash):
                return DynamoDBUser(user_item)
                
        return None

    def get_user(self, user_id):
        # user_id en nuestro caso es el email
        user_item = UsuarioRepository.get_by_email(user_id)
        if user_item:
            return DynamoDBUser(user_item)
        return None
