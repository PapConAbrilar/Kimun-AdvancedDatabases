from django.utils import timezone

from cursos.repository import CursoRepository
from kimun.data_access.base_repository import (
    BaseRepository,
    deserializar,
    nuevo_id,
    serializar,
)
from kimun.data_access.dynamodb_client import DynamoDBClient
from usuarios.repository import UsuarioRepository


class BancoPreguntasRepository(BaseRepository):
    entity_type = "QUESTION_BANK"
    key_prefix = "BANK"
    collection_key = "ENTITY#BANCOS_PREGUNTAS"

    @classmethod
    def enrich(cls, bank):
        if not bank:
            return None
        bank = deserializar(bank)
        bank["curso"] = (
            CursoRepository.get_course(bank.get("curso_id"))
            if bank.get("curso_id")
            else None
        )
        bank["creado_por"] = UsuarioRepository.get_by_email(bank.get("creado_por_id"))
        bank["preguntas"] = PreguntaRepository.list_by_bank(bank["id"])
        bank["preguntas_count"] = len(bank["preguntas"])
        return bank

    @classmethod
    def list_all(cls, user_email=None, role=None):
        banks = cls.all()
        if role not in {"admin", "docente"} and user_email:
            banks = [
                bank
                for bank in banks
                if bank.get("es_publico") or bank.get("creado_por_id") == user_email
            ]
        return [cls.enrich(bank) for bank in banks]

    @classmethod
    def get_bank(cls, bank_id):
        return cls.enrich(cls.get(bank_id))

    @classmethod
    def delete_bank(cls, bank_id):
        for question in PreguntaRepository.list_by_bank(bank_id):
            PreguntaRepository.delete_question(question["id"])
        return cls.delete(bank_id)


class EvaluacionRepository(BaseRepository):
    entity_type = "EVALUATION"
    key_prefix = "EVALUATION"

    @classmethod
    def save_evaluation(cls, data, evaluation_id=None):
        identifier = str(evaluation_id or nuevo_id())
        item = {
            **data,
            "PK": cls._pk(identifier),
            "SK": cls._sk(identifier),
            "GSI1PK": f"COURSE#{data['curso_id']}",
            "GSI1SK": f"EVALUATION#{identifier}",
            "id": identifier,
            "pk": identifier,
            "entity_type": cls.entity_type,
        }
        DynamoDBClient.put_item(serializar(item))
        return cls.enrich(item)

    @classmethod
    def enrich(cls, evaluation, with_questions=True):
        if not evaluation:
            return None
        evaluation = deserializar(evaluation)
        evaluation["curso"] = CursoRepository.get_course(evaluation.get("curso_id"))
        if with_questions:
            evaluation["preguntas"] = PreguntaRepository.list_by_evaluation(
                evaluation["id"]
            )
            evaluation["preguntas_count"] = len(evaluation["preguntas"])
        return evaluation

    @classmethod
    def get_evaluation(cls, evaluation_id, with_questions=True):
        return cls.enrich(cls.get(evaluation_id), with_questions=with_questions)

    @classmethod
    def list_by_course(cls, course_id, with_questions=True):
        items = DynamoDBClient.query_gsi1(f"COURSE#{course_id}", "EVALUATION#")
        return [cls.enrich(item, with_questions=with_questions) for item in items]

    @classmethod
    def delete_evaluation(cls, evaluation_id):
        for question in PreguntaRepository.list_by_evaluation(evaluation_id):
            PreguntaRepository.delete_question(question["id"])
        attempts = DynamoDBClient.query_gsi1(f"EVAL#{evaluation_id}", "ATTEMPT#")
        for attempt in attempts:
            DynamoDBClient.delete_item(attempt["PK"], attempt["SK"])
        return cls.delete(evaluation_id)

    @classmethod
    def guardar_intento(
        cls,
        usuario_email,
        evaluacion_id,
        puntaje,
        aprobado,
        respuestas,
        hora_inicio=None,
    ):
        identifier = nuevo_id()
        timestamp = timezone.now()
        item = {
            "PK": f"USER#{usuario_email}",
            "SK": f"ATTEMPT#{evaluacion_id}#{identifier}",
            "GSI1PK": f"EVAL#{evaluacion_id}",
            "GSI1SK": f"ATTEMPT#{timestamp.isoformat()}#{usuario_email}",
            "id": identifier,
            "pk": identifier,
            "usuario_id": usuario_email,
            "evaluacion_id": str(evaluacion_id),
            "puntaje": int(puntaje),
            "puntaje_obtenido": int(puntaje),
            "aprobado": bool(aprobado),
            "fecha_intento": timestamp,
            "hora_inicio": hora_inicio,
            "respuestas": respuestas,
            "entity_type": "EVAL_ATTEMPT",
        }
        DynamoDBClient.put_item(serializar(item))
        return cls.enrich_attempt(item)

    @classmethod
    def enrich_attempt(cls, attempt):
        if not attempt:
            return None
        attempt = deserializar(attempt)
        attempt["usuario"] = UsuarioRepository.get_by_email(attempt.get("usuario_id"))
        attempt["evaluacion"] = cls.get_evaluation(
            attempt.get("evaluacion_id"), with_questions=False
        )
        return attempt

    @classmethod
    def get_attempt(cls, user_email, evaluation_id, attempt_id):
        item = DynamoDBClient.get_item(
            f"USER#{user_email}", f"ATTEMPT#{evaluation_id}#{attempt_id}"
        )
        return cls.enrich_attempt(item)

    @classmethod
    def get_intentos_por_usuario(cls, usuario_email, evaluacion_id=None):
        prefix = f"ATTEMPT#{evaluacion_id}#" if evaluacion_id else "ATTEMPT#"
        items = DynamoDBClient.query_by_pk(f"USER#{usuario_email}", prefix)
        attempts = [cls.enrich_attempt(item) for item in items]
        return sorted(
            attempts,
            key=lambda item: str(item.get("fecha_intento", "")),
            reverse=True,
        )

    @classmethod
    def list_attempts_by_evaluation(cls, evaluation_id):
        items = DynamoDBClient.query_gsi1(f"EVAL#{evaluation_id}", "ATTEMPT#")
        return [cls.enrich_attempt(item) for item in items]

    @classmethod
    def count_attempts(cls):
        return sum(
            len(cls.get_intentos_por_usuario(user["email"]))
            for user in UsuarioRepository.list_all()
        )


class PreguntaRepository(BaseRepository):
    entity_type = "QUESTION"
    key_prefix = "QUESTION"

    @classmethod
    def save_question(cls, data, question_id=None):
        identifier = str(question_id or nuevo_id())
        parent_type = "EVALUATION" if data.get("evaluacion_id") else "BANK"
        parent_id = data.get("evaluacion_id") or data.get("banco_id")
        item = {
            **data,
            "PK": cls._pk(identifier),
            "SK": cls._sk(identifier),
            "GSI1PK": f"{parent_type}#{parent_id}",
            "GSI1SK": f"QUESTION#{identifier}",
            "id": identifier,
            "pk": identifier,
            "entity_type": cls.entity_type,
        }
        DynamoDBClient.put_item(serializar(item))
        return cls.enrich(item)

    @classmethod
    def enrich(cls, question):
        if not question:
            return None
        question = deserializar(question)
        question["alternativas"] = AlternativaRepository.list_by_question(question["id"])
        return question

    @classmethod
    def list_by_evaluation(cls, evaluation_id):
        items = DynamoDBClient.query_gsi1(
            f"EVALUATION#{evaluation_id}", "QUESTION#"
        )
        return [cls.enrich(item) for item in items]

    @classmethod
    def list_by_bank(cls, bank_id):
        items = DynamoDBClient.query_gsi1(f"BANK#{bank_id}", "QUESTION#")
        return [cls.enrich(item) for item in items]

    @classmethod
    def delete_question(cls, question_id):
        for alternative in AlternativaRepository.list_by_question(question_id):
            AlternativaRepository.delete(alternative["id"])
        return cls.delete(question_id)


class AlternativaRepository(BaseRepository):
    entity_type = "ALTERNATIVE"
    key_prefix = "ALTERNATIVE"

    @classmethod
    def save_alternative(cls, data, alternative_id=None):
        identifier = str(alternative_id or nuevo_id())
        item = {
            **data,
            "PK": cls._pk(identifier),
            "SK": cls._sk(identifier),
            "GSI1PK": f"QUESTION#{data['pregunta_id']}",
            "GSI1SK": f"ALTERNATIVE#{identifier}",
            "id": identifier,
            "pk": identifier,
            "entity_type": cls.entity_type,
        }
        DynamoDBClient.put_item(serializar(item))
        return deserializar(item)

    @classmethod
    def list_by_question(cls, question_id):
        items = DynamoDBClient.query_gsi1(
            f"QUESTION#{question_id}", "ALTERNATIVE#"
        )
        return [deserializar(item) for item in items]


def save_question_with_alternatives(question_data, alternatives, question_id=None):
    if question_id:
        for alternative in AlternativaRepository.list_by_question(question_id):
            AlternativaRepository.delete(alternative["id"])
    question = PreguntaRepository.save_question(question_data, question_id)
    question["alternativas"] = [
        AlternativaRepository.save_alternative(
            {
                "pregunta_id": question["id"],
                "texto": alternative.get("texto", ""),
                "es_correcta": bool(alternative.get("es_correcta")),
            }
        )
        for alternative in alternatives
    ]
    return question
