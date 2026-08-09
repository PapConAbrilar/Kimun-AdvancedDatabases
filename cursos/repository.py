from django.utils import timezone

from kimun.data_access.base_repository import (
    BaseRepository,
    deserializar,
    nuevo_id,
    serializar,
)
from kimun.data_access.dynamodb_client import DynamoDBClient
from usuarios.repository import UsuarioRepository, present_user


COURSE_STATUS_LABELS = {"borrador": "Borrador", "publicado": "Publicado"}
ENROLLMENT_STATUS_LABELS = {
    "asignado": "Asignado",
    "en_progreso": "En progreso",
    "completado": "Completado",
}
MATERIAL_TYPE_LABELS = {"pdf": "PDF", "video": "Video URL"}


class CategoriaRepository(BaseRepository):
    entity_type = "CATEGORY"
    key_prefix = "CATEGORY"
    collection_key = "CATALOG#CATEGORIAS"

    @classmethod
    def list_all(cls):
        categories = cls.all()
        courses = CursoRepository.get_all_courses(enrich=False)
        for category in categories:
            category["cursos_count"] = sum(
                1 for course in courses if course.get("categoria_id") == category["id"]
            )
        return sorted(categories, key=lambda category: category.get("nombre", "").lower())


class CursoRepository(BaseRepository):
    entity_type = "COURSE_METADATA"
    key_prefix = "COURSE"
    collection_key = "CATALOG#CURSOS"

    @classmethod
    def enrich(cls, course):
        if not course:
            return None
        course = deserializar(course)
        course["get_estado_display"] = COURSE_STATUS_LABELS.get(
            course.get("estado"), course.get("estado", "")
        )
        teacher_id = course.get("docente_creador_id")
        category_id = course.get("categoria_id")
        course["docente_creador"] = (
            UsuarioRepository.get_by_email(teacher_id) if teacher_id else None
        )
        course["categoria"] = CategoriaRepository.get(category_id) if category_id else None
        return course

    @classmethod
    def get_course(cls, course_id, enrich=True):
        course = cls.get(course_id)
        return cls.enrich(course) if enrich else course

    @classmethod
    def get_curso(cls, curso_id):
        return cls.get_course(curso_id)

    @classmethod
    def get_all_courses(cls, state=None, teacher_id=None, category_id=None, enrich=True):
        courses = cls.all()
        if state:
            courses = [course for course in courses if course.get("estado") == state]
        if teacher_id:
            courses = [
                course
                for course in courses
                if course.get("docente_creador_id") == str(teacher_id)
            ]
        if category_id:
            courses = [
                course for course in courses if course.get("categoria_id") == str(category_id)
            ]
        courses.sort(key=lambda course: str(course.get("fecha_creacion", "")), reverse=True)
        return [cls.enrich(course) for course in courses] if enrich else courses

    @classmethod
    def get_all_cursos(cls):
        return cls.get_all_courses()

    @classmethod
    def create_course(cls, data, course_id=None):
        payload = {
            "titulo": data.get("titulo", ""),
            "descripcion": data.get("descripcion", ""),
            "docente_creador_id": data.get("docente_creador_id", ""),
            "categoria_id": data.get("categoria_id") or "",
            "estado": data.get("estado", "borrador"),
            "fecha_limite": data.get("fecha_limite"),
            "fecha_creacion": data.get("fecha_creacion") or timezone.now(),
        }
        return cls.enrich(cls.save(payload, course_id))

    @classmethod
    def create_curso(cls, curso_id, titulo, descripcion, docente_id, estado="borrador"):
        return cls.create_course(
            {
                "titulo": titulo,
                "descripcion": descripcion,
                "docente_creador_id": docente_id,
                "estado": estado,
            },
            curso_id,
        )

    @classmethod
    def update_course(cls, course_id, changes):
        return cls.enrich(cls.update(course_id, changes))

    @classmethod
    def delete_course(cls, course_id):
        related = DynamoDBClient.query_gsi1(f"COURSE#{course_id}")
        for item in related:
            DynamoDBClient.delete_item(item["PK"], item["SK"])
        return cls.delete(course_id)

    @classmethod
    def count(cls):
        return len(cls.all())


class MaterialRepository(BaseRepository):
    entity_type = "MATERIAL"
    key_prefix = "MATERIAL"

    @classmethod
    def save_material(cls, data, material_id=None):
        identifier = str(material_id or nuevo_id())
        item = {
            **data,
            "PK": cls._pk(identifier),
            "SK": cls._sk(identifier),
            "GSI1PK": f"COURSE#{data['curso_id']}",
            "GSI1SK": f"MATERIAL#{identifier}",
            "id": identifier,
            "pk": identifier,
            "entity_type": cls.entity_type,
            "get_tipo_display": MATERIAL_TYPE_LABELS.get(data.get("tipo"), data.get("tipo", "")),
        }
        DynamoDBClient.put_item(serializar(item))
        return deserializar(item)

    @classmethod
    def list_by_course(cls, course_id):
        items = DynamoDBClient.query_gsi1(f"COURSE#{course_id}", "MATERIAL#")
        return [deserializar(item) for item in items]


class ClaseRepository(BaseRepository):
    entity_type = "CLASS"
    key_prefix = "CLASS"

    @classmethod
    def save_class(cls, data, class_id=None):
        identifier = str(class_id or nuevo_id())
        order = int(data.get("orden") or 1)
        item = {
            **data,
            "orden": order,
            "PK": cls._pk(identifier),
            "SK": cls._sk(identifier),
            "GSI1PK": f"COURSE#{data['curso_id']}",
            "GSI1SK": f"CLASS#{order:06d}#{identifier}",
            "id": identifier,
            "pk": identifier,
            "entity_type": cls.entity_type,
            "fecha_creacion": data.get("fecha_creacion") or timezone.now(),
            "fecha_actualizacion": timezone.now(),
        }
        DynamoDBClient.put_item(serializar(item))
        return deserializar(item)

    @classmethod
    def list_by_course(cls, course_id):
        items = DynamoDBClient.query_gsi1(f"COURSE#{course_id}", "CLASS#")
        classes = [deserializar(item) for item in items]
        return sorted(classes, key=lambda item: item.get("orden", 0))

    @classmethod
    def previous_and_next(cls, class_item):
        classes = cls.list_by_course(class_item["curso_id"])
        position = next(
            (index for index, item in enumerate(classes) if item["id"] == class_item["id"]),
            -1,
        )
        previous = classes[position - 1] if position > 0 else None
        following = classes[position + 1] if 0 <= position < len(classes) - 1 else None
        return previous, following


class InscripcionRepository:
    @staticmethod
    def get(user_email, course_id):
        item = DynamoDBClient.get_item(
            f"USER#{user_email}", f"ENROLLMENT#{course_id}"
        )
        return InscripcionRepository.enrich(item)

    @staticmethod
    def save(user_email, course_id, state="asignado"):
        item = {
            "PK": f"USER#{user_email}",
            "SK": f"ENROLLMENT#{course_id}",
            "GSI1PK": f"COURSE#{course_id}",
            "GSI1SK": f"ENROLLMENT#USER#{user_email}",
            "id": f"{user_email}:{course_id}",
            "pk": f"{user_email}:{course_id}",
            "usuario_id": user_email,
            "curso_id": str(course_id),
            "estado": state,
            "fecha_asignacion": timezone.now(),
            "entity_type": "ENROLLMENT",
        }
        DynamoDBClient.put_item(serializar(item))
        return InscripcionRepository.enrich(item)

    @staticmethod
    def enrich(item):
        if not item:
            return None
        enrollment = deserializar(item)
        enrollment["usuario"] = UsuarioRepository.get_by_email(enrollment["usuario_id"])
        enrollment["curso"] = CursoRepository.get_course(enrollment["curso_id"])
        enrollment["get_estado_display"] = ENROLLMENT_STATUS_LABELS.get(
            enrollment.get("estado"), enrollment.get("estado", "")
        )
        return enrollment

    @staticmethod
    def list_by_user(user_email, states=None):
        items = DynamoDBClient.query_by_pk(f"USER#{user_email}", "ENROLLMENT#")
        if states:
            items = [item for item in items if item.get("estado") in states]
        return [InscripcionRepository.enrich(item) for item in items]

    @staticmethod
    def list_by_course(course_id):
        items = DynamoDBClient.query_gsi1(
            f"COURSE#{course_id}", "ENROLLMENT#"
        )
        return [InscripcionRepository.enrich(item) for item in items]

    @staticmethod
    def update_state(user_email, course_id, state):
        current = InscripcionRepository.get(user_email, course_id)
        if not current:
            return None
        return InscripcionRepository.save(user_email, course_id, state)

    @staticmethod
    def count():
        return sum(
            len(InscripcionRepository.list_by_user(user["email"]))
            for user in UsuarioRepository.list_all()
        )


class ProgresoClaseRepository:
    @staticmethod
    def get(user_email, class_id):
        item = DynamoDBClient.get_item(f"USER#{user_email}", f"PROGRESS#{class_id}")
        return deserializar(item) if item else None

    @staticmethod
    def complete(user_email, class_item):
        item = {
            "PK": f"USER#{user_email}",
            "SK": f"PROGRESS#{class_item['id']}",
            "GSI1PK": f"CLASS#{class_item['id']}",
            "GSI1SK": f"USER#{user_email}",
            "usuario_id": user_email,
            "clase_id": class_item["id"],
            "curso_id": class_item["curso_id"],
            "fecha_completado": timezone.now(),
            "entity_type": "CLASS_PROGRESS",
        }
        DynamoDBClient.put_item(serializar(item))
        return deserializar(item)

    @staticmethod
    def list_by_user(user_email):
        items = DynamoDBClient.query_by_pk(f"USER#{user_email}", "PROGRESS#")
        return [deserializar(item) for item in items]

    @staticmethod
    def list_by_class(class_id):
        items = DynamoDBClient.query_gsi1(f"CLASS#{class_id}", "USER#")
        return [deserializar(item) for item in items]
