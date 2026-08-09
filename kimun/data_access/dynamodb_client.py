import logging

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from django.conf import settings


logger = logging.getLogger(__name__)


class DynamoDBClient:
    """Acceso centralizado a DynamoDB con escritura dual y failover regional."""

    _table_cache = None
    _active_region = None

    @classmethod
    def _table_for_region(cls, region, verify=True):
        table_name = getattr(settings, "DYNAMODB_TABLE_NAME", "KimunData-Demo")
        table = boto3.resource("dynamodb", region_name=region).Table(table_name)
        if verify:
            table.load()
        return table

    @classmethod
    def clear_cache(cls):
        cls._table_cache = None
        cls._active_region = None

    @classmethod
    def get_table(cls):
        if cls._table_cache is not None:
            return cls._table_cache

        primary_region = getattr(settings, "AWS_REGION_PRIMARY", "us-east-1")
        secondary_region = getattr(settings, "AWS_REGION_SECONDARY", "us-west-2")

        try:
            cls._table_cache = cls._table_for_region(primary_region)
            cls._active_region = primary_region
            logger.info("Conectado a DynamoDB en %s", primary_region)
        except (ClientError, EndpointConnectionError) as error:
            logger.warning(
                "No fue posible utilizar DynamoDB en %s: %s. Activando %s.",
                primary_region,
                error,
                secondary_region,
            )
            cls._table_cache = cls._table_for_region(secondary_region)
            cls._active_region = secondary_region

        return cls._table_cache

    @classmethod
    def _execute_with_failover(cls, operation):
        primary_region = getattr(settings, "AWS_REGION_PRIMARY", "us-east-1")
        secondary_region = getattr(settings, "AWS_REGION_SECONDARY", "us-west-2")

        try:
            return operation(cls.get_table())
        except (ClientError, EndpointConnectionError) as error:
            code = ""
            if isinstance(error, ClientError):
                code = error.response.get("Error", {}).get("Code", "")

            puede_hacer_failover = (
                cls._active_region == primary_region
                and (
                    isinstance(error, EndpointConnectionError)
                    or code
                    in {
                        "ResourceNotFoundException",
                        "InternalServerError",
                        "RequestLimitExceeded",
                        "ThrottlingException",
                    }
                )
            )
            if not puede_hacer_failover:
                raise

            logger.warning("Operación fallida en Virginia. Reintentando en Oregon.")
            cls._table_cache = cls._table_for_region(secondary_region)
            cls._active_region = secondary_region
            return operation(cls._table_cache)

    @classmethod
    def _replicate(cls, operation_name, **kwargs):
        primary_region = getattr(settings, "AWS_REGION_PRIMARY", "us-east-1")
        secondary_region = getattr(settings, "AWS_REGION_SECONDARY", "us-west-2")
        destination = (
            secondary_region if cls._active_region == primary_region else primary_region
        )

        try:
            table = cls._table_for_region(destination, verify=False)
            getattr(table, operation_name)(**kwargs)
        except Exception as error:  # La réplica no debe ocultar el resultado principal.
            logger.warning("No fue posible replicar la operación en %s: %s", destination, error)

    @classmethod
    def put_item(cls, item_data):
        cls._execute_with_failover(lambda table: table.put_item(Item=item_data))
        cls._replicate("put_item", Item=item_data)
        return item_data

    @classmethod
    def get_item(cls, pk, sk):
        response = cls._execute_with_failover(
            lambda table: table.get_item(Key={"PK": pk, "SK": sk})
        )
        return response.get("Item")

    @classmethod
    def delete_item(cls, pk, sk):
        key = {"PK": pk, "SK": sk}
        cls._execute_with_failover(lambda table: table.delete_item(Key=key))
        cls._replicate("delete_item", Key=key)
        return True

    @classmethod
    def query_by_pk(cls, pk, sk_prefix=None):
        from boto3.dynamodb.conditions import Key

        condition = Key("PK").eq(pk)
        if sk_prefix:
            condition &= Key("SK").begins_with(sk_prefix)

        def query_all(table):
            items = []
            params = {"KeyConditionExpression": condition}
            while True:
                response = table.query(**params)
                items.extend(response.get("Items", []))
                last_key = response.get("LastEvaluatedKey")
                if not last_key:
                    return items
                params["ExclusiveStartKey"] = last_key

        return cls._execute_with_failover(query_all)

    @classmethod
    def query_gsi1(cls, gsi1pk, gsi1sk_prefix=None):
        from boto3.dynamodb.conditions import Key

        condition = Key("GSI1PK").eq(gsi1pk)
        if gsi1sk_prefix:
            condition &= Key("GSI1SK").begins_with(gsi1sk_prefix)

        def query_all(table):
            items = []
            params = {
                "IndexName": "GSI1",
                "KeyConditionExpression": condition,
            }
            while True:
                response = table.query(**params)
                items.extend(response.get("Items", []))
                last_key = response.get("LastEvaluatedKey")
                if not last_key:
                    return items
                params["ExclusiveStartKey"] = last_key

        return cls._execute_with_failover(query_all)

    @classmethod
    def delete_partition(cls, pk, sk_prefix=None):
        items = cls.query_by_pk(pk, sk_prefix)
        for item in items:
            cls.delete_item(item["PK"], item["SK"])
        return len(items)
