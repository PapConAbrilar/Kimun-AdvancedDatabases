from kimun.data_access.dynamodb_client import DynamoDBClient

class UsuarioRepository:
    """
    Repositorio 100% NoSQL para la gestion de usuarios en DynamoDB.
    Reemplaza a Usuario.objects de SQLite.
    """
    
    @staticmethod
    def get_by_email(email):
        """
        En nuestro diseño NoSQL, usaremos el email como identificador unico.
        PK = USER#<email>
        SK = PROFILE#<email>
        """
        pk = f"USER#{email}"
        sk = f"PROFILE#{email}"
        
        item = DynamoDBClient.get_item(pk, sk)
        return item

    @staticmethod
    def create_user(email, password_hash, rol='alumno', nombre='', is_active=True):
        pk = f"USER#{email}"
        sk = f"PROFILE#{email}"
        
        item_data = {
            'PK': pk,
            'SK': sk,
            'email': email,
            'password_hash': password_hash,
            'rol': rol,
            'nombre': nombre,
            'is_active': is_active,
            'entity_type': 'USER_PROFILE'
        }
        
        DynamoDBClient.put_item(item_data)
        return item_data
