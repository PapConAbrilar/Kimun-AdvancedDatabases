from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from cursos.repository import InscripcionRepository
from usuarios.repository import UsuarioRepository


def _send(subject, message, recipient):
    if not recipient:
        return False
    try:
        send_mail(
            subject,
            message,
            getattr(settings, "DEFAULT_FROM_EMAIL", None),
            [recipient],
            fail_silently=False,
        )
        return True
    except Exception:
        return False


def notificar_inscripcion(inscripcion):
    user = inscripcion.get("usuario") or {}
    course = inscripcion.get("curso") or {}
    return _send(
        f'Nuevo curso asignado: {course.get("titulo", "")}',
        (
            f'Hola {user.get("nombre") or user.get("username", "")},\n\n'
            f'Se te ha asignado el curso "{course.get("titulo", "")}".\n\n'
            f'{course.get("descripcion", "")}\n\nEquipo ALUMCO'
        ),
        user.get("email"),
    )


def notificar_certificado(certificado):
    user = certificado.get("usuario") or {}
    course = certificado.get("curso") or {}
    return _send(
        f'Certificado obtenido: {course.get("titulo", "")}',
        (
            f'Hola {user.get("nombre") or user.get("username", "")},\n\n'
            f'Has completado el curso "{course.get("titulo", "")}".\n'
            f'Código de verificación: {certificado.get("codigo_verificacion", "")}.'
        ),
        user.get("email"),
    )


def verificar_recordatorios(usuario):
    email = usuario.email or usuario.username
    if not email:
        return []
    now = timezone.now()
    sent = []
    thresholds = {
        "7_dias": timedelta(days=7),
        "3_dias": timedelta(days=3),
        "1_dia": timedelta(days=1),
    }
    for enrollment in InscripcionRepository.list_by_user(
        email, states={"asignado", "en_progreso"}
    ):
        course = enrollment["curso"]
        deadline = course.get("fecha_limite")
        if not deadline or deadline < now:
            continue
        for reminder_type, delta in thresholds.items():
            reminder_date = deadline - delta
            if reminder_date <= now < reminder_date + timedelta(hours=24):
                if UsuarioRepository.reminder_exists(email, course["id"], reminder_type):
                    continue
                if _send(
                    f'Recordatorio: {delta.days} días para completar "{course["titulo"]}"',
                    f'El curso "{course["titulo"]}" vence el {deadline:%d/%m/%Y}.',
                    email,
                ):
                    UsuarioRepository.save_reminder(email, course["id"], reminder_type)
                    sent.append(course["titulo"])
    return sent
