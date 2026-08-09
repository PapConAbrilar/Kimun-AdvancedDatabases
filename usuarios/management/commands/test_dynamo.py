from django.core.management.base import BaseCommand
from kimun.data_access.dynamodb_client import DynamoDBClient
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

class Command(BaseCommand):
    help = 'Prueba la conexion basica a DynamoDB y la logica de Failover'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Iniciando prueba de conexion a DynamoDB..."))
        
        try:
            # Esto activara la logica de conexion en dynamodb_client.py
            table = DynamoDBClient.get_table()
            self.stdout.write(self.style.SUCCESS(f"¡Exito! Conectado a la tabla: {table.name}"))
            
        except (NoCredentialsError, PartialCredentialsError):
            self.stdout.write(self.style.ERROR(
                "Error: No tienes credenciales de AWS configuradas en tu computador local. "
                "Para probar esto localmente, necesitas poner las credenciales de Learner Lab en ~/.aws/credentials."
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Error al conectar con AWS. Si ves un error de 'ResourceNotFoundException', "
                f"significa que el codigo funciona pero la tabla aun no ha sido creada con Terraform.\nDetalle: {str(e)}"
            ))
