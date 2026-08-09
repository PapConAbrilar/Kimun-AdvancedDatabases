from kimun.data_access.dynamodb_client import DynamoDBClient

class DynamoDBCurso:
    def __init__(self, item):
        self.id = item.get('curso_id')
        self.pk = self.id
        self.titulo = item.get('titulo', '')
        self.descripcion = item.get('descripcion', '')
        self.estado = item.get('estado', 'borrador')
        self.docente_creador_id = item.get('docente_creador_id')
        self.categoria_id = item.get('categoria_id')
        self.fecha_creacion = item.get('fecha_creacion')

    def __str__(self):
        return self.titulo

class CursoRepository:
    @staticmethod
    def get_all_cursos():
        # En Single-Table, buscamos usando GSI o particion dedicada
        # Asumimos que guardamos un registro maestro de cursos 
        # con GSI1PK = "CATALOG#CURSOS"
        items = DynamoDBClient.query_gsi1(gsi1pk="CATALOG#CURSOS")
        return [DynamoDBCurso(item) for item in items]

    @staticmethod
    def get_curso(curso_id):
        item = DynamoDBClient.get_item(f"COURSE#{curso_id}", f"METADATA#{curso_id}")
        if item:
            return DynamoDBCurso(item)
        return None

    @staticmethod
    def create_curso(curso_id, titulo, descripcion, docente_id, estado='borrador'):
        pk = f"COURSE#{curso_id}"
        sk = f"METADATA#{curso_id}"
        
        item = {
            'PK': pk,
            'SK': sk,
            'GSI1PK': 'CATALOG#CURSOS',
            'GSI1SK': pk,
            'curso_id': curso_id,
            'titulo': titulo,
            'descripcion': descripcion,
            'docente_creador_id': docente_id,
            'estado': estado,
            'entity_type': 'COURSE_METADATA'
        }
        DynamoDBClient.put_item(item)
        return DynamoDBCurso(item)
