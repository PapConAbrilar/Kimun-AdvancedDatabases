from kimun.data_access.dynamodb_client import DynamoDBClient
from datetime import datetime

class DynamoDBIntento:
    def __init__(self, item):
        self.id = item.get('SK').split('#')[-1]
        self.pk = self.id
        self.puntaje_obtenido = item.get('puntaje', 0)
        self.aprobado = item.get('aprobado', False)
        self.fecha_intento = item.get('fecha_intento')
        self.respuestas = item.get('respuestas', {})

class EvaluacionRepository:
    @staticmethod
    def guardar_intento(usuario_email, evaluacion_id, puntaje, aprobado, respuestas):
        timestamp = datetime.now().isoformat()
        pk = f"USER#{usuario_email}"
        sk = f"ATTEMPT#{evaluacion_id}#{timestamp}"
        
        item = {
            'PK': pk,
            'SK': sk,
            'GSI1PK': f"EVAL#{evaluacion_id}",
            'GSI1SK': f"USER#{usuario_email}#{timestamp}",
            'puntaje': puntaje,
            'aprobado': aprobado,
            'fecha_intento': timestamp,
            'respuestas': respuestas,
            'entity_type': 'EVAL_ATTEMPT'
        }
        
        DynamoDBClient.put_item(item)
        return DynamoDBIntento(item)

    @staticmethod
    def get_intentos_por_usuario(usuario_email, evaluacion_id):
        # Buscamos en la particion del usuario los intentos de esta evaluacion especifica
        items = DynamoDBClient.query_by_pk(f"USER#{usuario_email}", f"ATTEMPT#{evaluacion_id}#")
        return [DynamoDBIntento(item) for item in items]
