from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from calendario.models import EventoCalendario, TipoEvento
from tareas.models import Tarea, EntregaTarea
from tareas.forms import TareaForm, CalificacionForm
from cursos.models import Curso
from cursos.models import InscripcionCurso

Usuario = get_user_model()


class TareaModelTests(TestCase):
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
        self.fecha_limite = timezone.now() + timedelta(days=7)
        self.tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea de Prueba',
            descripcion='Descripción de la tarea',
            fecha_limite=self.fecha_limite,
            puntaje_maximo=100,
            creado_por=self.docente
        )

    def test_tarea_creation(self):
        """Test that a Tarea can be created with all required fields"""
        self.assertEqual(self.tarea.curso, self.curso)
        self.assertEqual(self.tarea.titulo, 'Tarea de Prueba')
        self.assertEqual(self.tarea.descripcion, 'Descripción de la tarea')
        self.assertEqual(self.tarea.puntaje_maximo, 100)
        self.assertEqual(self.tarea.creado_por, self.docente)

    def test_tarea_str_method(self):
        """Test the __str__ method of Tarea"""
        expected = "Tarea de Prueba - Curso de Primeros Auxilios"
        self.assertEqual(str(self.tarea), expected)

    def test_tarea_ordering(self):
        """Test that Tareas are ordered by fecha_limite"""
        # Delete existing tareas
        Tarea.objects.all().delete()
        
        fecha_temprana = timezone.now() + timedelta(days=3)
        fecha_tardia = timezone.now() + timedelta(days=10)
        
        tarea_tardia = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea Tardía',
            fecha_limite=fecha_tardia,
            creado_por=self.docente
        )
        tarea_temprana = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea Temprana',
            fecha_limite=fecha_temprana,
            creado_por=self.docente
        )
        
        tareas = list(Tarea.objects.all())
        self.assertEqual(tareas[0].titulo, 'Tarea Temprana')
        self.assertEqual(tareas[1].titulo, 'Tarea Tardía')

    def test_tarea_default_puntaje(self):
        """Test that puntaje_maximo defaults to 100"""
        tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea sin puntaje especificado',
            fecha_limite=self.fecha_limite,
            creado_por=self.docente
        )
        self.assertEqual(tarea.puntaje_maximo, 100)

    def test_tarea_descripcion_blank(self):
        """Test that descripcion can be blank"""
        tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea sin descripción',
            fecha_limite=self.fecha_limite,
            creado_por=self.docente
        )
        self.assertEqual(tarea.descripcion, '')

    def test_tarea_related_names(self):
        """Test related names for ForeignKey relationships"""
        self.assertEqual(self.curso.tareas.count(), 1)
        self.assertEqual(self.docente.tareas_creadas.count(), 1)

    def test_tarea_verbose_names(self):
        """Test verbose names for the model"""
        self.assertEqual(Tarea._meta.verbose_name, 'Tarea')
        self.assertEqual(Tarea._meta.verbose_name_plural, 'Tareas')

    def test_tarea_fecha_creacion_auto(self):
        """Test that fecha_creacion is automatically set"""
        self.assertIsNotNone(self.tarea.fecha_creacion)


class EntregaTareaModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='22222222-2'
        )
        self.curso = Curso.objects.create(
            titulo='Curso de Primeros Auxilios',
            descripcion='Aprende primeros auxilios básicos',
            docente_creador=self.docente,
            estado='publicado'
        )
        self.fecha_limite = timezone.now() + timedelta(days=7)
        self.tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea de Prueba',
            fecha_limite=self.fecha_limite,
            creado_por=self.docente
        )
        self.entrega = EntregaTarea.objects.create(
            tarea=self.tarea,
            estudiante=self.colaborador,
            comentario='Aquí está mi tarea',
            estado='enviado'
        )

    def test_entrega_tarea_creation(self):
        """Test that an EntregaTarea can be created with all fields"""
        self.assertEqual(self.entrega.tarea, self.tarea)
        self.assertEqual(self.entrega.estudiante, self.colaborador)
        self.assertEqual(self.entrega.comentario, 'Aquí está mi tarea')
        self.assertEqual(self.entrega.estado, 'enviado')

    def test_entrega_tarea_str_method(self):
        """Test the __str__ method of EntregaTarea"""
        expected = f"{self.colaborador} - Tarea de Prueba (Enviado)"
        self.assertEqual(str(self.entrega), expected)

    def test_entrega_tarea_estado_choices(self):
        """Test that estado has the correct choices"""
        choices = dict(EntregaTarea.ESTADO_CHOICES)
        self.assertIn('enviado', choices)
        self.assertIn('calificado', choices)
        self.assertIn('devuelto', choices)
        self.assertEqual(choices['enviado'], 'Enviado')
        self.assertEqual(choices['calificado'], 'Calificado')
        self.assertEqual(choices['devuelto'], 'Devuelto')

    def test_entrega_tarea_default_estado(self):
        """Test that estado defaults to 'enviado'"""
        entrega = EntregaTarea.objects.create(
            tarea=self.tarea,
            estudiante=self.docente  # Use docente as another student
        )
        self.assertEqual(entrega.estado, 'enviado')

    def test_entrega_tarea_unique_together(self):
        """Test that a student can only submit one delivery per task"""
        with self.assertRaises(Exception):
            EntregaTarea.objects.create(
                tarea=self.tarea,
                estudiante=self.colaborador,
                estado='enviado'
            )

    def test_entrega_tarea_related_names(self):
        """Test related names for ForeignKey relationships"""
        self.assertEqual(self.tarea.entregas.count(), 1)
        self.assertEqual(self.colaborador.entregas.count(), 1)

    def test_entrega_tarea_puntaje_nullable(self):
        """Test that puntaje_obtenido can be null"""
        self.assertIsNone(self.entrega.puntaje_obtenido)
        
        # Test setting a value
        self.entrega.puntaje_obtenido = 85
        self.entrega.save()
        self.assertEqual(self.entrega.puntaje_obtenido, 85)

    def test_entrega_tarea_calificado_por_nullable(self):
        """Test that calificado_por can be null"""
        self.assertIsNone(self.entrega.calificado_por)
        
        # Test setting a value
        self.entrega.calificado_por = self.docente
        self.entrega.save()
        self.assertEqual(self.entrega.calificado_por, self.docente)

    def test_entrega_tarea_fecha_entrega_auto(self):
        """Test that fecha_entrega is automatically set"""
        self.assertIsNotNone(self.entrega.fecha_entrega)

    def test_entrega_tarea_fecha_calificacion_nullable(self):
        """Test that fecha_calificacion can be null"""
        self.assertIsNone(self.entrega.fecha_calificacion)
        
        # Test setting a value
        fecha_calif = timezone.now()
        self.entrega.fecha_calificacion = fecha_calif
        self.entrega.save()
        self.assertEqual(self.entrega.fecha_calificacion, fecha_calif)

    def test_entrega_tarea_archivo_blank(self):
        """Test that archivo can be blank"""
        self.assertFalse(self.entrega.archivo)

    def test_entrega_tarea_retroalimentacion_blank(self):
        """Test that retroalimentacion can be blank"""
        self.assertEqual(self.entrega.retroalimentacion, '')

    def test_entrega_tarea_comentario_blank(self):
        """Test that comentario can be blank"""
        entrega = EntregaTarea.objects.create(
            tarea=self.tarea,
            estudiante=self.docente
        )
        self.assertEqual(entrega.comentario, '')

    def test_entrega_tarea_verbose_names(self):
        """Test verbose names for the model"""
        self.assertEqual(EntregaTarea._meta.verbose_name, 'Entrega de Tarea')
        self.assertEqual(EntregaTarea._meta.verbose_name_plural, 'Entregas de Tareas')

    def test_entrega_tarea_different_students_same_task(self):
        """Test that different students can submit the same task"""
        colaborador2 = Usuario.objects.create_user(
            username='colaborador2', password='testpass', rol='colaborador', rut='33333333-3'
        )
        entrega2 = EntregaTarea.objects.create(
            tarea=self.tarea,
            estudiante=colaborador2,
            estado='enviado'
        )
        self.assertEqual(self.tarea.entregas.count(), 2)
        self.assertIn(self.entrega, self.tarea.entregas.all())
        self.assertIn(entrega2, self.tarea.entregas.all())

    def test_entrega_tarea_get_estado_display(self):
        """Test that get_estado_display returns correct human-readable text"""
        self.assertEqual(self.entrega.get_estado_display(), 'Enviado')
        
        self.entrega.estado = 'calificado'
        self.entrega.save()
        self.assertEqual(self.entrega.get_estado_display(), 'Calificado')
        
        self.entrega.estado = 'devuelto'
        self.entrega.save()
        self.assertEqual(self.entrega.get_estado_display(), 'Devuelto')


class TareaFormTests(TestCase):
    def setUp(self):
        self.valid_data = {
            'titulo': 'Tarea Formulario',
            'descripcion': 'Descripción opcional',
            'fecha_limite': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
            'puntaje_maximo': 100,
        }

    def test_tarea_form_valid(self):
        form = TareaForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), msg=f'Errors: {form.errors}')

    def test_tarea_form_required_fields(self):
        data = self.valid_data.copy()
        data.pop('titulo')
        data.pop('fecha_limite')
        form = TareaForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('titulo', form.errors)
        self.assertIn('fecha_limite', form.errors)

    def test_tarea_form_fecha_limite_past(self):
        data = self.valid_data.copy()
        data['fecha_limite'] = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        form = TareaForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn('La fecha límite no puede estar en el pasado.', form.errors['__all__'])

    def test_tarea_form_fecha_limite_future(self):
        data = self.valid_data.copy()
        data['fecha_limite'] = (timezone.now() + timedelta(days=10)).strftime('%Y-%m-%dT%H:%M')
        form = TareaForm(data=data)
        self.assertTrue(form.is_valid(), msg=f'Errors: {form.errors}')


class CalificacionFormTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente_calif', password='testpass', rol='docente', rut='44444444-4'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Calificación',
            descripcion='Descripción',
            docente_creador=self.docente,
            estado='publicado'
        )
        self.tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea Calificable',
            fecha_limite=timezone.now() + timedelta(days=5),
            puntaje_maximo=100,
            creado_por=self.docente,
        )
        self.valid_data = {
            'puntaje_obtenido': 80,
            'retroalimentacion': 'Buen trabajo',
        }

    def test_calificacion_form_valid(self):
        form = CalificacionForm(data=self.valid_data, tarea=self.tarea)
        self.assertTrue(form.is_valid(), msg=f'Errors: {form.errors}')

    def test_calificacion_form_puntaje_exceeds_max(self):
        data = self.valid_data.copy()
        data['puntaje_obtenido'] = 101
        form = CalificacionForm(data=data, tarea=self.tarea)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn('El puntaje obtenido no puede ser mayor al puntaje máximo de la tarea.', form.errors['__all__'])

    def test_calificacion_form_zero_puntaje(self):
        data = self.valid_data.copy()
        data['puntaje_obtenido'] = 0
        form = CalificacionForm(data=data, tarea=self.tarea)
        self.assertTrue(form.is_valid(), msg=f'Errors: {form.errors}')


class TareaListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin_tareas', password='testpass', rol='admin', rut='55555555-5'
        )
        self.docente = Usuario.objects.create_user(
            username='docente_tareas', password='testpass', rol='docente', rut='66666666-6'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador_tareas', password='testpass', rol='colaborador', rut='77777777-7'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Listado',
            descripcion='Descripción',
            docente_creador=self.docente,
            estado='publicado'
        )
        self.tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea Listada',
            fecha_limite=timezone.now() + timedelta(days=5),
            creado_por=self.docente,
        )

    def test_tarea_list_requires_login(self):
        response = self.client.get(reverse('tareas:tarea_list', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 302)

    def test_tarea_list_colaborador_not_enrolled(self):
        self.client.login(username='colaborador_tareas', password='testpass')
        response = self.client.get(reverse('tareas:tarea_list', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No estás inscrito en este curso.' in str(m) for m in messages))

    def test_tarea_list_colaborador_enrolled(self):
        InscripcionCurso.objects.create(usuario=self.colaborador, curso=self.curso, estado='asignado')
        self.client.login(username='colaborador_tareas', password='testpass')
        response = self.client.get(reverse('tareas:tarea_list', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tarea Listada')

    def test_tarea_list_docente(self):
        self.client.login(username='docente_tareas', password='testpass')
        response = self.client.get(reverse('tareas:tarea_list', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tarea Listada')

    def test_tarea_list_admin(self):
        self.client.login(username='admin_tareas', password='testpass')
        response = self.client.get(reverse('tareas:tarea_list', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tarea Listada')


class TareaCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin_create', password='testpass', rol='admin', rut='88888888-8'
        )
        self.docente = Usuario.objects.create_user(
            username='docente_create', password='testpass', rol='docente', rut='99999999-9'
        )
        self.otro_docente = Usuario.objects.create_user(
            username='docente_otro', password='testpass', rol='docente', rut='10101010-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Creación',
            descripcion='Descripción',
            docente_creador=self.docente,
            estado='publicado'
        )
        self.otro_curso = Curso.objects.create(
            titulo='Curso Ajeno',
            descripcion='Descripción',
            docente_creador=self.otro_docente,
            estado='publicado'
        )
        self.form_data = {
            'titulo': 'Nueva tarea',
            'descripcion': 'Detalle',
            'fecha_limite': (timezone.now() + timedelta(days=4)).strftime('%Y-%m-%dT%H:%M'),
            'puntaje_maximo': 90,
        }

    def test_tarea_create_requires_login(self):
        response = self.client.get(reverse('tareas:tarea_create', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 302)

    def test_tarea_create_colaborador_forbidden(self):
        colaborador = Usuario.objects.create_user(
            username='colaborador_create', password='testpass', rol='colaborador', rut='12121212-1'
        )
        self.client.login(username='colaborador_create', password='testpass')
        response = self.client.get(reverse('tareas:tarea_create', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 403)

    def test_tarea_create_docente_own_course(self):
        self.client.login(username='docente_create', password='testpass')
        response = self.client.post(reverse('tareas:tarea_create', kwargs={'curso_pk': self.curso.pk}), self.form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tarea.objects.filter(titulo='Nueva tarea', curso=self.curso, creado_por=self.docente).exists())

    def test_tarea_create_admin(self):
        self.client.login(username='admin_create', password='testpass')
        response = self.client.post(reverse('tareas:tarea_create', kwargs={'curso_pk': self.curso.pk}), self.form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tarea.objects.filter(titulo='Nueva tarea', curso=self.curso, creado_por=self.admin).exists())

    def test_tarea_create_docente_wrong_course(self):
        self.client.login(username='docente_create', password='testpass')
        response = self.client.get(reverse('tareas:tarea_create', kwargs={'curso_pk': self.otro_curso.pk}))
        self.assertEqual(response.status_code, 403)


class EntregaCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.docente = Usuario.objects.create_user(
            username='docente_entrega', password='testpass', rol='docente', rut='13131313-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador_entrega', password='testpass', rol='colaborador', rut='14141414-1'
        )
        self.otro_colaborador = Usuario.objects.create_user(
            username='otro_colaborador_entrega', password='testpass', rol='colaborador', rut='15151515-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Entrega',
            descripcion='Descripción',
            docente_creador=self.docente,
            estado='publicado'
        )
        self.tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea Entrega',
            fecha_limite=timezone.now() + timedelta(days=5),
            creado_por=self.docente,
        )
        InscripcionCurso.objects.create(usuario=self.colaborador, curso=self.curso, estado='asignado')

    def test_entrega_create_requires_login(self):
        response = self.client.get(reverse('tareas:entrega_create', kwargs={'tarea_pk': self.tarea.pk}))
        self.assertEqual(response.status_code, 302)

    def test_entrega_create_not_enrolled(self):
        self.client.login(username='otro_colaborador_entrega', password='testpass')
        response = self.client.get(reverse('tareas:entrega_create', kwargs={'tarea_pk': self.tarea.pk}))
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No estás inscrito en este curso.' in str(m) for m in messages))

    def test_entrega_create_already_submitted(self):
        EntregaTarea.objects.create(tarea=self.tarea, estudiante=self.colaborador, comentario='Ya enviada')
        self.client.login(username='colaborador_entrega', password='testpass')
        response = self.client.get(reverse('tareas:entrega_create', kwargs={'tarea_pk': self.tarea.pk}))
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Ya entregaste esta tarea.' in str(m) for m in messages))

    def test_entrega_create_valid(self):
        self.client.login(username='colaborador_entrega', password='testpass')
        response = self.client.post(
            reverse('tareas:entrega_create', kwargs={'tarea_pk': self.tarea.pk}),
            {'comentario': 'Mi entrega'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(EntregaTarea.objects.filter(tarea=self.tarea, estudiante=self.colaborador, comentario='Mi entrega').exists())

    def test_entrega_create_with_file(self):
        self.client.login(username='colaborador_entrega', password='testpass')
        archivo = SimpleUploadedFile('entrega.txt', b'contenido de prueba', content_type='text/plain')
        response = self.client.post(
            reverse('tareas:entrega_create', kwargs={'tarea_pk': self.tarea.pk}),
            {'comentario': 'Con archivo', 'archivo': archivo}
        )
        self.assertEqual(response.status_code, 302)
        entrega = EntregaTarea.objects.get(tarea=self.tarea, estudiante=self.colaborador)
        self.assertTrue(entrega.archivo.name.startswith('entregas/'))
        self.assertTrue(entrega.archivo.name.endswith('.txt'))


class EntregaGradeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin_grade', password='testpass', rol='admin', rut='16161616-1'
        )
        self.docente = Usuario.objects.create_user(
            username='docente_grade', password='testpass', rol='docente', rut='17171717-1'
        )
        self.otro_docente = Usuario.objects.create_user(
            username='docente_otro_grade', password='testpass', rol='docente', rut='18181818-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador_grade', password='testpass', rol='colaborador', rut='19191919-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Calificar',
            descripcion='Descripción',
            docente_creador=self.docente,
            estado='publicado'
        )
        self.otro_curso = Curso.objects.create(
            titulo='Curso Otro Calificar',
            descripcion='Descripción',
            docente_creador=self.otro_docente,
            estado='publicado'
        )
        self.tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea Calificable',
            fecha_limite=timezone.now() + timedelta(days=5),
            creado_por=self.docente,
        )
        self.entrega = EntregaTarea.objects.create(tarea=self.tarea, estudiante=self.colaborador, comentario='Entrega')
        self.otra_tarea = Tarea.objects.create(
            curso=self.otro_curso,
            titulo='Tarea Ajena',
            fecha_limite=timezone.now() + timedelta(days=5),
            creado_por=self.otro_docente,
        )
        self.otra_entrega = EntregaTarea.objects.create(tarea=self.otra_tarea, estudiante=self.colaborador, comentario='Entrega ajena')

    def test_entrega_grade_requires_login(self):
        response = self.client.get(reverse('tareas:entrega_grade', kwargs={'pk': self.entrega.pk}))
        self.assertEqual(response.status_code, 302)

    def test_entrega_grade_colaborador_forbidden(self):
        self.client.login(username='colaborador_grade', password='testpass')
        response = self.client.get(reverse('tareas:entrega_grade', kwargs={'pk': self.entrega.pk}))
        self.assertEqual(response.status_code, 403)

    def test_entrega_grade_docente_own_course(self):
        self.client.login(username='docente_grade', password='testpass')
        with patch('tareas.views.render', return_value=HttpResponse('ok', status=200)):
            response = self.client.get(reverse('tareas:entrega_grade', kwargs={'pk': self.entrega.pk}))
        self.assertEqual(response.status_code, 200)

    def test_entrega_grade_admin(self):
        self.client.login(username='admin_grade', password='testpass')
        with patch('tareas.views.render', return_value=HttpResponse('ok', status=200)):
            response = self.client.get(reverse('tareas:entrega_grade', kwargs={'pk': self.entrega.pk}))
        self.assertEqual(response.status_code, 200)

    def test_entrega_grade_post_calificar(self):
        self.client.login(username='docente_grade', password='testpass')
        response = self.client.post(
            reverse('tareas:entrega_grade', kwargs={'pk': self.entrega.pk}),
            {'puntaje_obtenido': 95, 'retroalimentacion': 'Muy bien'}
        )
        self.assertEqual(response.status_code, 302)
        self.entrega.refresh_from_db()
        self.assertEqual(self.entrega.estado, 'calificado')
        self.assertEqual(self.entrega.puntaje_obtenido, 95)
        self.assertEqual(self.entrega.calificado_por, self.docente)
        self.assertIsNotNone(self.entrega.fecha_calificacion)


class SignalTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente_signal_tareas', password='testpass', rol='docente', rut='20202020-2'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Señales Tareas',
            descripcion='Descripción',
            docente_creador=self.docente,
            estado='publicado'
        )

    def test_tarea_creates_calendar_event(self):
        tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea con Evento',
            descripcion='Descripción',
            fecha_limite=timezone.now() + timedelta(days=2),
            creado_por=self.docente,
        )
        evento = EventoCalendario.objects.filter(curso=self.curso, tipo=TipoEvento.CLASE_DEADLINE, titulo='Tarea: Tarea con Evento').first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.fecha_inicio, tarea.fecha_limite)
        self.assertEqual(evento.creado_por, self.docente)

    def test_tarea_update_updates_calendar_event(self):
        tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea Original',
            descripcion='Original',
            fecha_limite=timezone.now() + timedelta(days=2),
            creado_por=self.docente,
        )
        nueva_fecha = timezone.now() + timedelta(days=10)
        tarea.titulo = 'Tarea Actualizada'
        tarea.descripcion = 'Actualizada'
        tarea.fecha_limite = nueva_fecha
        tarea.save()

        eventos = EventoCalendario.objects.filter(curso=self.curso, tipo=TipoEvento.CLASE_DEADLINE)
        self.assertEqual(eventos.count(), 1)
        evento = eventos.first()
        self.assertEqual(evento.titulo, 'Tarea: Tarea Actualizada')
        self.assertEqual(evento.descripcion, 'Actualizada')
        self.assertEqual(evento.fecha_inicio, nueva_fecha)

    def test_tarea_delete_removes_calendar_event(self):
        tarea = Tarea.objects.create(
            curso=self.curso,
            titulo='Tarea Borrar',
            descripcion='Borrar',
            fecha_limite=timezone.now() + timedelta(days=2),
            creado_por=self.docente,
        )
        self.assertTrue(EventoCalendario.objects.filter(curso=self.curso, tipo=TipoEvento.CLASE_DEADLINE, titulo='Tarea: Tarea Borrar').exists())
        tarea.delete()
        self.assertFalse(EventoCalendario.objects.filter(curso=self.curso, tipo=TipoEvento.CLASE_DEADLINE, titulo='Tarea: Tarea Borrar').exists())
