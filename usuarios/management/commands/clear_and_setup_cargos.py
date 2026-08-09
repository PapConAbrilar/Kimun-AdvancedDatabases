from django.core.management.base import BaseCommand, CommandError

from anuncios.repository import AnuncioRepository
from calendario.repository import CalendarioRepository
from certificados.repository import CertificadoRepository
from cursos.repository import (
    CategoriaRepository,
    ClaseRepository,
    CursoRepository,
    MaterialRepository,
)
from evaluaciones.repository import BancoPreguntasRepository, EvaluacionRepository
from tareas.repository import TareaRepository
from usuarios.repository import AreaCargoRepository, UsuarioRepository


CARGOS = [
    "Profesional de Atención Directa",
    "Técnico de Atención Directa",
    "Asistente de Trato Directo",
    "Auxiliares de Servicio",
    "Manipuladores de Alimento",
    "Administración y Apoyo",
    "Directivos",
    "Docente Interno",
    "Docente Externo",
]


class Command(BaseCommand):
    help = "Limpia los datos de DynamoDB, conserva administradores y recrea cargos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Confirma la eliminación de datos de la tabla configurada",
        )

    def handle(self, *args, **options):
        if not options["confirmar"]:
            raise CommandError("La operación requiere el argumento --confirmar.")

        self.stdout.write("Eliminando datos funcionales de DynamoDB...")

        for certificado in CertificadoRepository.list_all():
            CertificadoRepository.delete(certificado["id"])
        for evento in CalendarioRepository.all():
            CalendarioRepository.delete(evento["id"])
        for anuncio in AnuncioRepository.all():
            AnuncioRepository.delete(anuncio["id"])

        for banco in BancoPreguntasRepository.list_all():
            BancoPreguntasRepository.delete_bank(banco["id"])

        for curso in CursoRepository.get_all_courses(enrich=False):
            curso_id = curso["id"]
            for tarea in TareaRepository.list_by_course(curso_id):
                TareaRepository.delete_task(tarea["id"])
            for evaluacion in EvaluacionRepository.list_by_course(curso_id):
                EvaluacionRepository.delete_evaluation(evaluacion["id"])
            for material in MaterialRepository.list_by_course(curso_id):
                MaterialRepository.delete(material["id"])
            for clase in ClaseRepository.list_by_course(curso_id):
                ClaseRepository.delete(clase["id"])
            CursoRepository.delete_course(curso_id)

        for categoria in CategoriaRepository.list_all():
            CategoriaRepository.delete(categoria["id"])
        for usuario in UsuarioRepository.list_all():
            if usuario.get("rol") != "admin":
                UsuarioRepository.delete_user(usuario["email"])
        for cargo in AreaCargoRepository.list_all():
            AreaCargoRepository.delete(cargo["id"])

        for nombre in CARGOS:
            AreaCargoRepository.save({"nombre": nombre})
            self.stdout.write(f"  Cargo creado: {nombre}")

        self.stdout.write(
            self.style.SUCCESS(
                "Limpieza finalizada. Se conservaron los administradores y se recrearon "
                f"{len(CARGOS)} cargos."
            )
        )
