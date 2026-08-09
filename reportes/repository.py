from collections import Counter

from certificados.repository import CertificadoRepository
from cursos.repository import (
    ClaseRepository,
    CursoRepository,
    InscripcionRepository,
    ProgresoClaseRepository,
)
from evaluaciones.repository import EvaluacionRepository
from usuarios.repository import UsuarioRepository


class ReporteRepository:
    """Consultas agregadas construidas exclusivamente sobre repositorios NoSQL."""

    @staticmethod
    def dashboard():
        users = UsuarioRepository.list_all()
        courses = CursoRepository.get_all_courses()
        enrollments = [
            enrollment
            for user in users
            for enrollment in InscripcionRepository.list_by_user(user["email"])
        ]
        certificates = CertificadoRepository.list_all()
        attempts = [
            attempt
            for user in users
            for attempt in EvaluacionRepository.get_intentos_por_usuario(user["email"])
        ]
        role_counts = Counter(user.get("rol") for user in users)
        state_counts = Counter(item.get("estado") for item in enrollments)
        course_counts = Counter(item.get("curso_id") for item in enrollments)
        average = (
            sum(item.get("puntaje_obtenido", 0) for item in attempts) / len(attempts)
            if attempts
            else 0
        )
        return {
            "total_usuarios": len(users),
            "total_cursos": len(courses),
            "total_inscripciones": len(enrollments),
            "total_certificados": len(certificates),
            "usuarios_por_rol": [
                {"rol": role, "count": count} for role, count in role_counts.items()
            ],
            "inscripciones_por_estado": [
                {"estado": state, "count": count}
                for state, count in state_counts.items()
            ],
            "evaluaciones_promedio": round(average, 1),
            "ultimas_inscripciones": sorted(
                enrollments,
                key=lambda item: str(item.get("fecha_asignacion", "")),
                reverse=True,
            )[:10],
            "cursos_con_mas_inscritos": sorted(
                [
                    {**course, "num_inscritos": course_counts.get(course["id"], 0)}
                    for course in courses
                ],
                key=lambda item: item["num_inscritos"],
                reverse=True,
            )[:5],
        }

    @staticmethod
    def course_report(course_id):
        course = CursoRepository.get_course(course_id)
        enrollments = InscripcionRepository.list_by_course(course_id)
        evaluations = EvaluacionRepository.list_by_course(course_id)
        for enrollment in enrollments:
            attempts = [
                attempt
                for evaluation in evaluations
                for attempt in EvaluacionRepository.get_intentos_por_usuario(
                    enrollment["usuario_id"], evaluation["id"]
                )
            ]
            enrollment["intentos_count"] = len(attempts)
            enrollment["mejor_puntaje"] = max(
                (attempt.get("puntaje_obtenido", 0) for attempt in attempts), default=0
            )
        return {
            "curso": course,
            "inscripciones": enrollments,
            "evaluaciones": evaluations,
        }

    @staticmethod
    def user_report(user_email):
        return {
            "usuario": UsuarioRepository.get_by_email(user_email),
            "inscripciones": InscripcionRepository.list_by_user(user_email),
            "intentos": EvaluacionRepository.get_intentos_por_usuario(user_email),
            "certificados": CertificadoRepository.list_by_user(user_email),
        }

    @staticmethod
    def progress_heatmap(course_id=None):
        courses = CursoRepository.get_all_courses()
        if not course_id:
            return courses, None, [], []
        course = CursoRepository.get_course(course_id)
        classes = ClaseRepository.list_by_course(course_id)
        students = []
        for enrollment in InscripcionRepository.list_by_course(course_id):
            completed = {
                progress["clase_id"]
                for progress in ProgresoClaseRepository.list_by_user(
                    enrollment["usuario_id"]
                )
            }
            students.append(
                {
                    "usuario": enrollment["usuario"],
                    "progreso": [class_item["id"] in completed for class_item in classes],
                    "completadas": len(completed.intersection({item["id"] for item in classes})),
                    "porcentaje": round(
                        len(completed.intersection({item["id"] for item in classes}))
                        * 100
                        / len(classes),
                        1,
                    )
                    if classes
                    else 0,
                }
            )
        return courses, course, classes, students
