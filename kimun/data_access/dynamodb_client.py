import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class DynamoDBClient:
    """
    Cliente centralizado para interactuar con DynamoDB implementando el patron Single-Table.
    Incluye la logica de Failover Automatico para cumplir con el requisito de 'Botar un Nodo'.
    """
    _table_cache = None

    @classmethod
    def get_table(cls):
        """
        Retorna la tabla de DynamoDB. Si la region primaria falla (simulacion de caida),
        salta automaticamente a la region secundaria (Global Tables).
        """
        if cls._table_cache:
            return cls._table_cache

        table_name = getattr(settings, 'DYNAMODB_TABLE_NAME', 'KimunData-Demo')
        primary_region = getattr(settings, 'AWS_REGION_PRIMARY', 'us-east-1')
        secondary_region = getattr(settings, 'AWS_REGION_SECONDARY', 'sa-east-1')

        try:
            # 1. Intento de conexion al Nodo Primario
            dynamodb = boto3.resource('dynamodb', region_name=primary_region)
            table = dynamodb.Table(table_name)
            
            # Forzar una llamada a AWS para verificar que la tabla exista fisicamente
            # Si fue eliminada por el equipo, esto lanzara una excepcion
            table.load()
            
            logger.info(f"Conectado a DynamoDB en region primaria ({primary_region})")
            cls._table_cache = table
            return table

        except (ClientError, EndpointConnectionError) as e:
            logger.warning(f"Falla detectada en Nodo Primario ({primary_region}). Detalle: {e}")
            logger.warning(f"--- EJECUTANDO FAILOVER HACIA REGION SECUNDARIA ({secondary_region}) ---")
            
            # 2. Conexion de contingencia al Nodo Secundario (Global Tables)
            dynamodb_replica = boto3.resource('dynamodb', region_name=secondary_region)
            table_replica = dynamodb_replica.Table(table_name)
            
            # Guardamos la tabla secundaria en cache para no seguir intentando la primaria rota
            cls._table_cache = table_replica
            return table_replica

    @classmethod
    def put_item(cls, item_data):
        table = cls.get_table()
        table.put_item(Item=item_data)
        return True

    @classmethod
    def get_item(cls, pk, sk):
        table = cls.get_table()
        response = table.get_item(
            Key={
                'PK': pk,
                'SK': sk
            }
        )
        return response.get('Item')

    @classmethod
    def delete_item(cls, pk, sk):
        table = cls.get_table()
        table.delete_item(
            Key={
                'PK': pk,
                'SK': sk
            }
        )
        return True

    @classmethod
    def query_by_pk(cls, pk, sk_prefix=None):
        from boto3.dynamodb.conditions import Key
        
        table = cls.get_table()
        
        if sk_prefix:
            key_condition = Key('PK').eq(pk) & Key('SK').begins_with(sk_prefix)
        else:
            key_condition = Key('PK').eq(pk)
            
        response = table.query(KeyConditionExpression=key_condition)
        return response.get('Items', [])

    @classmethod
    def query_gsi1(cls, gsi1pk, gsi1sk_prefix=None):
        from boto3.dynamodb.conditions import Key
        
        table = cls.get_table()
        
        if gsi1sk_prefix:
            key_condition = Key('GSI1PK').eq(gsi1pk) & Key('GSI1SK').begins_with(gsi1sk_prefix)
        else:
            key_condition = Key('GSI1PK').eq(gsi1pk)
            
        response = table.query(
            IndexName='GSI1',
            KeyConditionExpression=key_condition
        )
        return response.get('Items', [])
