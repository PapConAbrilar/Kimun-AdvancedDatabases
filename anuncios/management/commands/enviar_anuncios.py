from datetime import timedelta
from typing import Any, cast

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from anuncios.models import Anuncio
from cursos.models import InscripcionCurso


class Command(BaseCommand):
    help = 'Send emails for newly published announcements'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be sent without sending')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        recently_published = cast(Any, Anuncio).objects.filter(
            publicado=True,
            fecha_publicacion__gte=timezone.now() - timedelta(hours=24)
        )

        if not recently_published.exists():
            self.stdout.write('No announcements to send.')
            return

        for anuncio in recently_published:
            if anuncio.curso:
                enrollments = cast(Any, InscripcionCurso).objects.filter(
                    curso=anuncio.curso,
                    estado__in=['asignado', 'en_progreso', 'completado']
                ).select_related('usuario')
                recipients = [e.usuario.email for e in enrollments if e.usuario.email]
            else:
                User = get_user_model()
                recipients = list(User.objects.filter(email__isnull=False).exclude(email='').values_list('email', flat=True))

            if dry_run:
                self.stdout.write(f'[DRY RUN] Would send announcement "{anuncio.titulo}" to {len(recipients)} users')
            else:
                for email in recipients:
                    send_mail(
                        subject=f'Nuevo anuncio: {anuncio.titulo}',
                        message=f'{anuncio.titulo}\n\n{anuncio.contenido[:500]}',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=True,
                    )
                self.stdout.write(f'Sent announcement "{anuncio.titulo}" to {len(recipients)} users')
