from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def notificar_inscripcion(inscripcion):
    """Envía email cuando un usuario es inscrito a un curso"""
    if not inscripcion.usuario.email:
        return False
    
    subject = f'Nuevo curso asignado: {inscripcion.curso.titulo}'
    message = f'''Hola {inscripcion.usuario.get_full_name or inscripcion.usuario.username},

Se te ha asignado el curso "{inscripcion.curso.titulo}".

Descripción del curso:
{inscripcion.curso.descripcion}

Ingresa a la plataforma Kimün para ver los materiales y comenzar tu capacitación.

Saludos,
Equipo ALUMCO'''

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else None,
            [inscripcion.usuario.email],
            fail_silently=False,
        )
        return True
    except Exception:
        return False


def notificar_certificado(certificado):
    """Envía email cuando un usuario obtiene un certificado"""
    if not certificado.usuario.email:
        return False
    
    subject = f'¡Felicidades! Certificado obtenido: {certificado.curso.titulo}'
    message = f'''Hola {certificado.usuario.get_full_name or certificado.usuario.username},

¡Felicidades! Has completado el curso "{certificado.curso.titulo}" y has obtenido tu certificado.

Tu código de verificación es: {certificado.codigo_verificacion}

Puedes verificar y descargar tu certificado en la plataforma Kimün.

Saludos,
Equipo ALUMCO'''

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else None,
            [certificado.usuario.email],
            fail_silently=False,
        )
        return True
    except Exception:
        return False


def verificar_recordatorios(usuario):
    """Check and send deadline reminders to user"""
    from cursos.models import InscripcionCurso
    from usuarios.models import Recordatorio
    
    if not usuario.email:
        return []
    
    now = timezone.now()
    reminders_sent = []
    
    reminder_thresholds = {
        '7_dias': timedelta(days=7),
        '3_dias': timedelta(days=3),
        '1_dia': timedelta(days=1),
    }
    
    inscripciones = InscripcionCurso.objects.filter(
        usuario=usuario,
        estado__in=['asignado', 'en_progreso']
    ).select_related('curso')
    
    for inscripcion in inscripciones:
        curso = inscripcion.curso
        
        if not curso.fecha_limite:
            continue
        
        if curso.fecha_limite < now:
            continue
        
        for tipo, delta in reminder_thresholds.items():
            reminder_date = curso.fecha_limite - delta
            
            if now >= reminder_date and now < reminder_date + timedelta(hours=24):
                if not Recordatorio.objects.filter(
                    usuario=usuario,
                    curso=curso,
                    tipo=tipo
                ).exists():
                    days_left = delta.days
                    subject = f'Recordatorio: {days_left} días para completar "{curso.titulo}"'
                    message = f'''Hola {usuario.get_full_name or usuario.username},

Este es un recordatorio automático. El curso "{curso.titulo}" tiene fecha límite el {curso.fecha_limite.strftime('%d de %B de %Y')}.

Te quedan {days_left} días para completar el curso. No olvides realizar las evaluaciones para obtener tu certificado.

Ingresa a la plataforma Kimün para continuar con tu capacitación.

Saludos,
Equipo ALUMCO'''

                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else None,
                            [usuario.email],
                            fail_silently=False,
                        )
                        Recordatorio.objects.create(
                            usuario=usuario,
                            curso=curso,
                            tipo=tipo
                        )
                        reminders_sent.append(curso.titulo)
                    except Exception:
                        pass
    
    return reminders_sent