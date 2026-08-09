from django.core.management.base import BaseCommand
from usuarios.repository import UsuarioRepository
from cursos.repository import CursoRepository
from evaluaciones.repository import EvaluacionRepository
from django.contrib.auth.hashers import make_password
import random
import time

class Command(BaseCommand):
    help = 'Puebla la tabla de DynamoDB con datos de prueba (100% NoSQL)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Iniciando inyección de datos en DynamoDB..."))
        
        try:
            # 1. Crear Usuarios
            self.stdout.write("1. Creando usuarios...")
            profesor = UsuarioRepository.create_user(
                email="profesor@kimun.cl",
                password_hash=make_password("mockhash123"), # Password válido
                rol="docente",
                nombre="Profesor Kimun"
            )
            
            alumnos = []
            for i in range(1, 6):
                email = f"alumno{i}@kimun.cl"
                alumno = UsuarioRepository.create_user(
                    email=email,
                    password_hash=make_password("mockhash123"),
                    rol="alumno",
                    nombre=f"Alumno {i}"
                )
                alumnos.append(email)
                self.stdout.write(f"   - {email} creado.")

            # 2. Crear Cursos
            self.stdout.write("2. Creando cursos (Catálogo)...")
            cursos_creados = []
            for i in range(1, 4):
                curso = CursoRepository.create_curso(
                    curso_id=f"CURSO-{i}",
                    titulo=f"Curso Avanzado de Base de Datos {i}",
                    descripcion="Aprende NoSQL con DynamoDB",
                    docente_id=profesor['email'],
                    estado="publicado"
                )
                cursos_creados.append(curso.id)
                self.stdout.write(f"   - {curso.titulo} creado.")

            # 3. Crear Intentos de Evaluación (Rendiciones transaccionales)
            self.stdout.write("3. Generando carga transaccional (Evaluaciones)...")
            for alumno_email in alumnos:
                for curso_id in cursos_creados:
                    # Simulamos que cada alumno rindió una prueba por curso
                    puntaje = random.randint(40, 100)
                    aprobado = puntaje >= 60
                    EvaluacionRepository.guardar_intento(
                        usuario_email=alumno_email,
                        evaluacion_id=f"EVAL-{curso_id}",
                        puntaje=puntaje,
                        aprobado=aprobado,
                        respuestas={"1": "A", "2": "C", "3": "B"}
                    )
                    time.sleep(0.1) # Pequeña pausa para no saturar la capa gratuita
            self.stdout.write("   - Intentos de evaluación guardados.")

            self.stdout.write(self.style.SUCCESS(
                "\n¡Seed completado con éxito! La tabla en AWS ahora tiene registros de usuarios, cursos e intentos reales NoSQL."
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al inyectar datos: {str(e)}"))
