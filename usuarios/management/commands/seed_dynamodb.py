import random

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from cursos.repository import CursoRepository
from evaluaciones.repository import EvaluacionRepository
from usuarios.repository import UsuarioRepository


class Command(BaseCommand):
    help = "Puebla DynamoDB con datos demostrativos de Kimün"

    def handle(self, *args, **options):
        self.stdout.write("Iniciando carga de datos en DynamoDB...")
        try:
            docente = self._asegurar_usuario(
                "profesor@kimun.cl", "docente", "Profesor Kimün"
            )
            estudiantes = [
                self._asegurar_usuario(
                    f"alumno{indice}@kimun.cl",
                    "colaborador",
                    f"Alumno {indice}",
                )
                for indice in range(1, 6)
            ]

            evaluaciones = []
            for indice in range(1, 4):
                curso = CursoRepository.create_curso(
                    curso_id=f"CURSO-{indice}",
                    titulo=f"Curso avanzado de bases de datos {indice}",
                    descripcion="Aprendizaje práctico de NoSQL con DynamoDB.",
                    docente_id=docente["email"],
                    estado="publicado",
                )
                evaluacion = EvaluacionRepository.save_evaluation(
                    {
                        "curso_id": curso["id"],
                        "titulo": f"Evaluación de {curso['titulo']}",
                        "descripcion": "Evaluación demostrativa.",
                        "porcentaje_aprobacion": 60,
                        "intentos_permitidos": 3,
                        "creado_por_id": docente["email"],
                    },
                    f"EVAL-{curso['id']}",
                )
                evaluaciones.append(evaluacion)
                self.stdout.write(f"  Curso creado: {curso['titulo']}")

            for estudiante in estudiantes:
                for evaluacion in evaluaciones:
                    puntaje = random.randint(40, 100)
                    EvaluacionRepository.guardar_intento(
                        usuario_email=estudiante["email"],
                        evaluacion_id=evaluacion["id"],
                        puntaje=puntaje,
                        aprobado=puntaje >= 60,
                        respuestas={"1": "A", "2": "C", "3": "B"},
                    )

            self.stdout.write(
                self.style.SUCCESS("Carga demostrativa completada en DynamoDB.")
            )
        except Exception as error:
            raise CommandError(f"No fue posible cargar los datos: {error}") from error

    @staticmethod
    def _asegurar_usuario(email, rol, nombre):
        existente = UsuarioRepository.get_by_email(email)
        if existente:
            return existente
        return UsuarioRepository.create_user(
            email=email,
            password_hash=make_password("mockhash123"),
            rol=rol,
            nombre=nombre,
        )
