import random
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cursos.repository import CursoRepository, InscripcionRepository
from evaluaciones.repository import EvaluacionRepository
from usuarios.repository import UsuarioRepository
from certificados.repository import CertificadoRepository

# Estados de enrolamiento con pesos (más completados que pendientes)
ENROLLMENT_STATES = ["asignado", "en_progreso", "completado"]
ENROLLMENT_WEIGHTS = [1, 2, 5]  # 1/8 asignado, 2/8 en_progreso, 5/8 completado

# Áreas/cargos de la ONG ALUMCO para distribuir entre alumnos
AREAS_CARGO = [
    "Profesional de Atención Directa",
    "Técnico de Atención Directa",
    "Asistente de Trato Directo",
    "Auxiliares de Servicio",
    "Manipuladores de Alimento",
]


class Command(BaseCommand):
    help = "Puebla DynamoDB con datos demostrativos de Kimün (KPIs incluidos)."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando carga de datos en DynamoDB...")
        now = timezone.now()

        try:
            # ── Usuarios ──────────────────────────────────────────
            admin = self._asegurar_usuario(
                "admin@kimun.cl", "admin", "Administración Kimün",
                area="Administración y Apoyo",
            )
            docente = self._asegurar_usuario(
                "profesor@kimun.cl", "docente", "Profesor Kimün",
                area="Administración y Apoyo",
            )

            estudiantes = []
            areas = AREAS_CARGO.copy()
            for i in range(1, 8):  # 7 alumnos para tener más datos
                area = areas[(i - 1) % len(areas)]
                est = self._asegurar_usuario(
                    f"alumno{i}@kimun.cl", "colaborador", f"Alumno {i}",
                    area=area,
                )
                # Guardar el área/cargo en el perfil (necesario para KPI 4)
                from usuarios.repository import UsuarioRepository
                UsuarioRepository.update_user(
                    est["email"],
                    {"areacargo_nombre": area, "cargo_id": area.lower().replace(" ", "_")},
                )
                estudiantes.append(est)

            self.stdout.write(f"   ✅ {len(estudiantes) + 2} usuarios creados")

            # ── Cursos ────────────────────────────────────────────
            cursos_data = [
                ("CURSO-1", "Cuidados Básicos del Adulto Mayor", "Higiene, movilización y prevención de caídas en residencias ELEAM."),
                ("CURSO-2", "Primeros Auxilios en ELEAM", "RCP básico, manejo de emergencias y botiquín."),
                ("CURSO-3", "Marco Legal y Normativas", "Derechos del adulto mayor, normativa SENAMA y protocolos."),
                ("CURSO-4", "Gestión Emocional del Cuidador", "Estrés laboral, autocuidado y comunicación efectiva."),
                ("CURSO-5", "Nutrición en la Tercera Edad", "Dietas balanceadas, disfagia y alimentación asistida."),
            ]

            cursos = []
            evaluaciones = []
            for cid, titulo, desc in cursos_data:
                curso = CursoRepository.create_curso(
                    curso_id=cid, titulo=titulo, descripcion=desc,
                    docente_id=docente["email"], estado="publicado",
                )
                cursos.append(curso)

                evaluacion = EvaluacionRepository.save_evaluation(
                    {
                        "curso_id": curso["id"],
                        "titulo": f"Evaluación Final — {titulo}",
                        "descripcion": "Evaluación de conocimientos del curso.",
                        "porcentaje_aprobacion": 60,
                        "intentos_permitidos": 3,
                        "creado_por_id": docente["email"],
                    },
                    f"EVAL-{curso['id']}",
                )
                evaluaciones.append(evaluacion)
                self.stdout.write(f"   📚 {titulo}")

            # ── Enrolamientos + Evaluaciones + Certificados ───────
            total_enrollments = 0
            total_attempts = 0
            total_certs = 0

            for estudiante in estudiantes:
                for i, curso in enumerate(cursos):
                    # Determinar estado del enrolamiento (pesado hacia completado)
                    estado = random.choices(ENROLLMENT_STATES, weights=ENROLLMENT_WEIGHTS, k=1)[0]

                    # Fechas realistas
                    dias_antes = random.randint(5, 60)
                    fecha_asignacion = (now - timedelta(days=dias_antes)).strftime('%Y-%m-%d')
                    fecha_completado = None
                    if estado == "completado":
                        fecha_completado = (now - timedelta(days=dias_antes) + timedelta(days=random.randint(10, 90))).strftime('%Y-%m-%d')

                    # Crear enrolamiento directamente (para controlar fechas)
                    from kimun.data_access.dynamodb_client import DynamoDBClient
                    from kimun.data_access.base_repository import serializar

                    item = {
                        "PK": f"USER#{estudiante['email']}",
                        "SK": f"ENROLLMENT#{curso['id']}",
                        "GSI1PK": f"COURSE#{curso['id']}",
                        "GSI1SK": f"ENROLLMENT#USER#{estudiante['email']}",
                        "id": f"{estudiante['email']}:{curso['id']}",
                        "pk": f"{estudiante['email']}:{curso['id']}",
                        "usuario_id": estudiante["email"],
                        "curso_id": str(curso["id"]),
                        "cursotitulo": curso.get("titulo", ""),
                        "estado": estado,
                        "fecha_asignacion": fecha_asignacion,
                        "fecha_completado": fecha_completado,
                        "entity_type": "ENROLLMENT",
                    }
                    DynamoDBClient.put_item(serializar(item))
                    total_enrollments += 1

                    # Intentos de evaluación (solo si completó o está en progreso)
                    if estado in ("completado", "en_progreso"):
                        evaluacion = evaluaciones[i]
                        puntaje = random.randint(40, 100)
                        EvaluacionRepository.guardar_intento(
                            usuario_email=estudiante["email"],
                            evaluacion_id=evaluacion["id"],
                            puntaje=puntaje,
                            aprobado=puntaje >= 60,
                            respuestas={"1": "A", "2": "C", "3": "B"},
                        )
                        total_attempts += 1

                    # Certificados (solo si completó el curso)
                    if estado == "completado":
                        cert_state = random.choices(
                            ["aprobado", "pendiente", "rechazado"],
                            weights=[7, 2, 1],  # Mayoría aprobados
                            k=1,
                        )[0]
                        CertificadoRepository.create(
                            estudiante["email"], curso["id"], state=cert_state
                        )
                        total_certs += 1

            self.stdout.write(f"   ✅ {total_enrollments} enrolamientos")
            self.stdout.write(f"   ✅ {total_attempts} intentos de evaluación")
            self.stdout.write(f"   ✅ {total_certs} certificados")

            self.stdout.write(
                self.style.SUCCESS(
                    "\n✔ Carga demostrativa completada.\n"
                    "   Ejecutá: python manage.py exportar_datos_s3 --solo-export\n"
                    "   Luego:   python manage.py setup_athena_tables\n"
                    "   Luego:   python manage.py exportar_datos_s3 --solo-kpis"
                )
            )
        except Exception as error:
            raise CommandError(f"No fue posible cargar los datos: {error}") from error

    @staticmethod
    def _asegurar_usuario(email, rol, nombre, area=None):
        existente = UsuarioRepository.get_by_email(email)
        if existente:
            return existente
        return UsuarioRepository.create_user(
            email=email,
            password_hash=make_password(
                "admin" if rol == "admin" else "profesor" if rol == "docente" else "alumno"
            ),
            rol=rol,
            nombre=nombre,
        )
