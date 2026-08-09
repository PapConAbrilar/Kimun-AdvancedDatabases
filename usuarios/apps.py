from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    name = 'usuarios'

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.core.exceptions import ValidationError
        
        try:
            User = get_user_model()
            old_to_python = User._meta.pk.to_python
            
            def new_to_python(value):
                try:
                    return old_to_python(value)
                except (ValueError, ValidationError, TypeError):
                    return str(value)
            
            User._meta.pk.to_python = new_to_python
        except Exception:
            pass
