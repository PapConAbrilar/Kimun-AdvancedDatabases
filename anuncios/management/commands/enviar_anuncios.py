from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from anuncios.repository import AnuncioRepository
from cursos.repository import InscripcionRepository
from usuarios.repository import UsuarioRepository


class Command(BaseCommand):
    help = "Envía por correo los anuncios publicados durante las últimas 24 horas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Muestra los envíos sin mandar correos",
        )

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(hours=24)
        anuncios = [
            item
            for item in AnuncioRepository.all()
            if item.get("publicado")
            and item.get("fecha_publicacion")
            and item["fecha_publicacion"] >= limite
        ]
        if not anuncios:
            self.stdout.write("No hay anuncios recientes para enviar.")
            return

        for anuncio in anuncios:
            curso_id = anuncio.get("curso_id")
            if curso_id:
                destinatarios = {
                    item["usuario_id"]
                    for item in InscripcionRepository.list_by_course(curso_id)
                    if item.get("estado") in {"asignado", "en_progreso", "completado"}
                }
            else:
                destinatarios = {
                    item["email"]
                    for item in UsuarioRepository.list_all(active_only=True)
                    if item.get("email")
                }

            if options["simular"]:
                self.stdout.write(
                    f'[SIMULACIÓN] "{anuncio["titulo"]}" para {len(destinatarios)} usuarios'
                )
                continue

            for correo in destinatarios:
                send_mail(
                    subject=f'Nuevo anuncio: {anuncio["titulo"]}',
                    message=f'{anuncio["titulo"]}\n\n{anuncio.get("contenido", "")[:500]}',
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[correo],
                    fail_silently=True,
                )
            self.stdout.write(
                f'Anuncio "{anuncio["titulo"]}" enviado a {len(destinatarios)} usuarios.'
            )
