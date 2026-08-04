from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from calendario.models import EventoCalendario, TipoEvento
from calendario.forms import EventoCalendarioForm
from cursos.models import Curso, InscripcionCurso
from evaluaciones.models import Evaluacion

Usuario = get_user_model()


class EventoCalendarioModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso de Primeros Auxilios',
            descripcion='Aprende primeros auxilios básicos',
            docente_creador=self.docente,
            estado='publicado'
        )
        self.evaluacion = Evaluacion.objects.create(
            curso=self.curso,
            titulo='Evaluación de Primeros Auxilios',
            porcentaje_aprobacion=70
        )
        self.fecha_inicio = timezone.now() + timedelta(days=7)
        self.fecha_fin = timezone.now() + timedelta(days=14)
        self.evento = EventoCalendario.objects.create(
            titulo='Plazo de Evaluación',
            descripcion='Fecha límite para completar la evaluación',
            tipo=TipoEvento.EVALUACION_DEADLINE,
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            curso=self.curso,
            evaluacion=self.evaluacion,
            creado_por=self.docente,
            color='#ff5733'
        )

    def test_evento_calendario_creation(self):
        self.assertEqual(self.evento.titulo, 'Plazo de Evaluación')
        self.assertEqual(self.evento.descripcion, 'Fecha límite para completar la evaluación')
        self.assertEqual(self.evento.tipo, TipoEvento.EVALUACION_DEADLINE)
        self.assertEqual(self.evento.curso, self.curso)
        self.assertEqual(self.evento.evaluacion, self.evaluacion)
        self.assertEqual(self.evento.creado_por, self.docente)
        self.assertEqual(self.evento.color, '#ff5733')

    def test_evento_calendario_str_method(self):
        expected = "Plazo de Evaluación (Plazo de Evaluación)"
        self.assertEqual(str(self.evento), expected)

    def test_evento_calendario_default_color(self):
        evento_default = EventoCalendario.objects.create(
            titulo='Evento Sin Color',
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            creado_por=self.docente
        )
        self.assertEqual(evento_default.color, '#6366f1')

    def test_evento_calendario_ordering(self):
        EventoCalendario.objects.all().delete()
        fecha_ayer = timezone.now() - timedelta(days=1)
        fecha_manana = timezone.now() + timedelta(days=1)

        evento_ayer = EventoCalendario.objects.create(
            titulo='Evento Ayer',
            fecha_inicio=fecha_ayer,
            fecha_fin=fecha_ayer,
            creado_por=self.docente
        )
        evento_manana = EventoCalendario.objects.create(
            titulo='Evento Mañana',
            fecha_inicio=fecha_manana,
            fecha_fin=fecha_manana,
            creado_por=self.docente
        )

        eventos = list(EventoCalendario.objects.all())
        self.assertEqual(eventos[0], evento_ayer)
        self.assertEqual(eventos[1], evento_manana)

    def test_evento_calendario_tipo_choices(self):
        choices = dict(TipoEvento.choices)
        self.assertIn('clase_deadline', choices)
        self.assertIn('evaluacion_deadline', choices)
        self.assertIn('curso_start', choices)
        self.assertIn('curso_end', choices)
        self.assertIn('evento_general', choices)
        self.assertEqual(choices['clase_deadline'], 'Plazo de Clase')
        self.assertEqual(choices['evaluacion_deadline'], 'Plazo de Evaluación')
        self.assertEqual(choices['curso_start'], 'Inicio de Curso')
        self.assertEqual(choices['curso_end'], 'Fin de Curso')
        self.assertEqual(choices['evento_general'], 'Evento General')

    def test_evento_calendario_default_tipo(self):
        evento_default = EventoCalendario.objects.create(
            titulo='Evento General',
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            creado_por=self.docente
        )
        self.assertEqual(evento_default.tipo, TipoEvento.EVENTO_GENERAL)

    def test_evento_calendario_curso_nullable(self):
        evento_sin_curso = EventoCalendario.objects.create(
            titulo='Evento Sin Curso',
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            creado_por=self.docente
        )
        self.assertIsNone(evento_sin_curso.curso)
        self.assertIsNone(evento_sin_curso.evaluacion)

    def test_evento_calendario_related_names(self):
        self.assertGreaterEqual(self.curso.eventos_calendario.count(), 1)
        self.assertGreaterEqual(self.evaluacion.eventos_calendario.count(), 1)
        self.assertGreaterEqual(self.docente.eventos_creados.count(), 1)

    def test_evento_calendario_verbose_names(self):
        self.assertEqual(EventoCalendario._meta.verbose_name, 'Evento de Calendario')
        self.assertEqual(EventoCalendario._meta.verbose_name_plural, 'Eventos de Calendario')


class CalendarioSignalTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente_signal', password='testpass', rol='docente', rut='22222222-2'
        )

    def test_signal_curso_creates_start_event(self):
        curso = Curso.objects.create(
            titulo='Curso de Señales',
            descripcion='Test de señales',
            docente_creador=self.docente,
            estado='publicado'
        )
        
        evento_start = EventoCalendario.objects.filter(curso=curso, tipo=TipoEvento.CURSO_START).first()
        self.assertIsNotNone(evento_start)
        self.assertEqual(evento_start.titulo, f"Inicio: {curso.titulo}")
        self.assertEqual(evento_start.color, '#22c55e')
        self.assertEqual(evento_start.creado_por, self.docente)

    def test_signal_curso_creates_end_event_on_fecha_limite(self):
        from django.utils import timezone
        from datetime import timedelta
        
        fecha_limite = timezone.now() + timedelta(days=30)
        curso = Curso.objects.create(
            titulo='Curso con Fecha Límite',
            descripcion='Test fecha límite',
            docente_creador=self.docente,
            estado='publicado',
            fecha_limite=fecha_limite
        )
        
        evento_end = EventoCalendario.objects.filter(curso=curso, tipo=TipoEvento.CURSO_END).first()
        self.assertIsNotNone(evento_end)
        self.assertEqual(evento_end.titulo, f"Fecha límite: {curso.titulo}")
        self.assertEqual(evento_end.color, '#ef4444')
        self.assertEqual(evento_end.fecha_inicio, fecha_limite)

    def test_signal_evaluacion_creates_event(self):
        from django.utils import timezone
        from datetime import timedelta
        
        curso = Curso.objects.create(
            titulo='Curso para Evaluación',
            descripcion='Test evaluación',
            docente_creador=self.docente,
            estado='publicado'
        )
        
        evaluacion = Evaluacion.objects.create(
            curso=curso,
            titulo='Evaluación de Test',
            porcentaje_aprobacion=70
        )
        
        evento_eval = EventoCalendario.objects.filter(evaluacion=evaluacion).first()
        self.assertIsNotNone(evento_eval)
        self.assertEqual(evento_eval.titulo, f"Evaluación: {evaluacion.titulo}")
        self.assertEqual(evento_eval.tipo, TipoEvento.EVALUACION_DEADLINE)
        self.assertEqual(evento_eval.color, '#f59e0b')

    def test_signal_curso_delete_cascades_events(self):
        curso = Curso.objects.create(
            titulo='Curso a Eliminar',
            descripcion='Test eliminación',
            docente_creador=self.docente,
            estado='publicado'
        )
        
        self.assertTrue(EventoCalendario.objects.filter(curso=curso).exists())
        
        curso_id = curso.id
        curso.delete()
        
        self.assertFalse(EventoCalendario.objects.filter(curso__id=curso_id).exists())

    def test_signal_evaluacion_delete_cascades_events(self):
        curso = Curso.objects.create(
            titulo='Curso para Evaluación Delete',
            descripcion='Test delete evaluación',
            docente_creador=self.docente,
            estado='publicado'
        )
        
        evaluacion = Evaluacion.objects.create(
            curso=curso,
            titulo='Evaluación a Eliminar',
            porcentaje_aprobacion=70
        )
        
        self.assertTrue(EventoCalendario.objects.filter(evaluacion=evaluacion).exists())
        
        evaluacion_id = evaluacion.id
        evaluacion.delete()
        
        self.assertFalse(EventoCalendario.objects.filter(evaluacion__id=evaluacion_id).exists())

    def test_signal_curso_update_fecha_limite_updates_end_event(self):
        from django.utils import timezone
        from datetime import timedelta
        
        curso = Curso.objects.create(
            titulo='Curso Update Fecha',
            descripcion='Test update fecha',
            docente_creador=self.docente,
            estado='publicado'
        )
        
        fecha_limite1 = timezone.now() + timedelta(days=30)
        curso.fecha_limite = fecha_limite1
        curso.save()
        
        evento_end = EventoCalendario.objects.filter(curso=curso, tipo=TipoEvento.CURSO_END).first()
        self.assertEqual(evento_end.fecha_inicio, fecha_limite1)
        
        fecha_limite2 = timezone.now() + timedelta(days=60)
        curso.fecha_limite = fecha_limite2
        curso.save()
        
        evento_end_actualizado = EventoCalendario.objects.filter(curso=curso, tipo=TipoEvento.CURSO_END).first()
        self.assertEqual(evento_end_actualizado.fecha_inicio, fecha_limite2)
        self.assertEqual(EventoCalendario.objects.filter(curso=curso, tipo=TipoEvento.CURSO_END).count(), 1)


class EventoCalendarioFormTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente_form', password='testpass', rol='docente', rut='33333333-3'
        )
        self.curso = Curso.objects.create(
            titulo='Curso de Formularios',
            descripcion='Test de formularios',
            docente_creador=self.docente,
            estado='publicado'
        )
        self.fecha_inicio = timezone.now() + timedelta(days=7)
        self.fecha_fin = timezone.now() + timedelta(days=14)

    def test_form_valid_data(self):
        form_data = {
            'titulo': 'Evento de Prueba',
            'descripcion': 'Descripción del evento',
            'tipo': TipoEvento.EVENTO_GENERAL,
            'fecha_inicio': self.fecha_inicio.strftime('%Y-%m-%dT%H:%M'),
            'fecha_fin': self.fecha_fin.strftime('%Y-%m-%dT%H:%M'),
            'curso': self.curso.id,
            'color': '#ff5733'
        }
        form = EventoCalendarioForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_fecha_fin_before_fecha_inicio_invalid(self):
        fecha_fin_anterior = self.fecha_inicio - timedelta(days=1)
        form_data = {
            'titulo': 'Evento Inválido',
            'descripcion': 'Evento con fechas incorrectas',
            'tipo': TipoEvento.EVENTO_GENERAL,
            'fecha_inicio': self.fecha_inicio.strftime('%Y-%m-%dT%H:%M'),
            'fecha_fin': fecha_fin_anterior.strftime('%Y-%m-%dT%H:%M'),
            'color': '#6366f1'
        }
        form = EventoCalendarioForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn('La fecha de fin debe ser posterior a la fecha de inicio.', form.errors['__all__'])

    def test_form_curso_optional(self):
        form_data = {
            'titulo': 'Evento Sin Curso',
            'descripcion': 'Evento general sin curso asociado',
            'tipo': TipoEvento.EVENTO_GENERAL,
            'fecha_inicio': self.fecha_inicio.strftime('%Y-%m-%dT%H:%M'),
            'fecha_fin': self.fecha_fin.strftime('%Y-%m-%dT%H:%M'),
            'color': '#22c55e'
        }
        form = EventoCalendarioForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertNotIn('curso', form.errors)

    def test_form_color_default(self):
        form_data = {
            'titulo': 'Evento con Color Default',
            'tipo': TipoEvento.CLASE_DEADLINE,
            'fecha_inicio': self.fecha_inicio.strftime('%Y-%m-%dT%H:%M'),
            'fecha_fin': self.fecha_fin.strftime('%Y-%m-%dT%H:%M'),
        }
        form = EventoCalendarioForm(data=form_data)
        self.assertTrue(form.is_valid())
        evento = form.save(commit=False)
        evento.creado_por = self.docente
        evento.save()
        self.assertEqual(evento.color, '#6366f1')


class CalendarioViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='22222222-2'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='33333333-3'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripcion',
            docente_creador=self.docente
        )
        InscripcionCurso.objects.create(
            usuario=self.colaborador,
            curso=self.curso,
            estado='asignado'
        )
        self.evento = EventoCalendario.objects.create(
            titulo='Evento Test',
            descripcion='Descripcion',
            tipo=TipoEvento.EVENTO_GENERAL,
            fecha_inicio=timezone.now(),
            fecha_fin=timezone.now() + timedelta(hours=1),
            curso=self.curso,
            creado_por=self.docente,
            color='#6366f1'
        )

    def test_calendario_requires_login(self):
        response = self.client.get(reverse('calendario:calendario'))
        self.assertEqual(response.status_code, 302)

    def test_calendario_admin_access(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('calendario:calendario'))
        self.assertEqual(response.status_code, 200)

    def test_calendario_colaborador_access(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('calendario:calendario'))
        self.assertEqual(response.status_code, 200)


class EventoCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='22222222-2'
        )

    def test_evento_create_requires_login(self):
        response = self.client.get(reverse('calendario:evento_create'))
        self.assertEqual(response.status_code, 302)

    def test_evento_create_colaborador_forbidden(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('calendario:evento_create'))
        self.assertEqual(response.status_code, 403)

    def test_evento_create_admin_access(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('calendario:evento_create'))
        self.assertEqual(response.status_code, 200)

    def test_evento_create_post(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.post(reverse('calendario:evento_create'), {
            'titulo': 'Nuevo Evento',
            'descripcion': 'Descripcion',
            'tipo': TipoEvento.EVENTO_GENERAL,
            'fecha_inicio': '2026-04-15T10:00',
            'fecha_fin': '2026-04-15T11:00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(EventoCalendario.objects.filter(titulo='Nuevo Evento').exists())


class EventoEditViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='22222222-2'
        )
        self.evento = EventoCalendario.objects.create(
            titulo='Evento Test',
            tipo=TipoEvento.EVENTO_GENERAL,
            fecha_inicio=timezone.now(),
            fecha_fin=timezone.now() + timedelta(hours=1),
            creado_por=self.docente,
            color='#6366f1'
        )

    def test_evento_edit_admin_access(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('calendario:evento_edit', kwargs={'pk': self.evento.pk}))
        self.assertEqual(response.status_code, 200)


class IcalExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        EventoCalendario.objects.create(
            titulo='Evento Test',
            tipo=TipoEvento.EVENTO_GENERAL,
            fecha_inicio=timezone.now(),
            fecha_fin=timezone.now() + timedelta(hours=1),
            creado_por=self.admin,
            color='#6366f1'
        )

    def test_ical_export_requires_login(self):
        response = self.client.get(reverse('calendario:calendario_ical_export'))
        self.assertEqual(response.status_code, 302)

    def test_ical_export_returns_ics(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('calendario:calendario_ical_export'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/calendar', response['Content-Type'])
