from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json
from evaluaciones.models import Evaluacion, Pregunta, Alternativa, IntentoEvaluacion
from evaluaciones.forms import EvaluacionForm
from cursos.models import Curso, InscripcionCurso

Usuario = get_user_model()


class EvaluacionModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripcion',
            docente_creador=self.docente
        )
        self.evaluacion = Evaluacion.objects.create(
            curso=self.curso,
            titulo='Evaluacion Final',
            porcentaje_aprobacion=70
        )

    def test_evaluacion_creation(self):
        self.assertEqual(self.evaluacion.curso, self.curso)
        self.assertEqual(self.evaluacion.titulo, 'Evaluacion Final')
        self.assertEqual(self.evaluacion.porcentaje_aprobacion, 70)

    def test_evaluacion_str_method(self):
        self.assertEqual(str(self.evaluacion), 'Evaluacion Final - Curso Test')

    def test_evaluacion_default_porcentaje(self):
        evaluacion = Evaluacion.objects.create(
            curso=self.curso,
            titulo='Otra Evaluacion'
        )
        self.assertEqual(evaluacion.porcentaje_aprobacion, 70)

    def test_evaluacion_default_max_intentos(self):
        evaluacion = Evaluacion.objects.create(
            curso=self.curso,
            titulo='Otra Evaluacion'
        )
        self.assertEqual(evaluacion.max_intentos, 0)

    def test_evaluacion_related_name(self):
        self.assertEqual(self.curso.evaluaciones.count(), 1)


class PreguntaModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripcion',
            docente_creador=self.docente
        )
        self.evaluacion = Evaluacion.objects.create(
            curso=self.curso,
            titulo='Evaluacion Test'
        )
        self.pregunta = Pregunta.objects.create(
            evaluacion=self.evaluacion,
            texto='Cual es la respuesta correcta?'
        )

    def test_pregunta_creation(self):
        self.assertEqual(self.pregunta.evaluacion, self.evaluacion)
        self.assertEqual(self.pregunta.texto, 'Cual es la respuesta correcta?')

    def test_pregunta_str_method(self):
        self.assertEqual(str(self.pregunta), 'Cual es la respuesta correcta?')

    def test_pregunta_related_name(self):
        self.assertEqual(self.evaluacion.preguntas.count(), 1)


class AlternativaModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripcion',
            docente_creador=self.docente
        )
        self.evaluacion = Evaluacion.objects.create(
            curso=self.curso,
            titulo='Evaluacion Test'
        )
        self.pregunta = Pregunta.objects.create(
            evaluacion=self.evaluacion,
            texto='Cual es la respuesta?'
        )
        self.alt_correcta = Alternativa.objects.create(
            pregunta=self.pregunta,
            texto='Opcion A',
            es_correcta=True
        )
        self.alt_incorrecta = Alternativa.objects.create(
            pregunta=self.pregunta,
            texto='Opcion B',
            es_correcta=False
        )

    def test_alternativa_creation(self):
        self.assertEqual(self.alt_correcta.pregunta, self.pregunta)
        self.assertTrue(self.alt_correcta.es_correcta)
        self.assertFalse(self.alt_incorrecta.es_correcta)

    def test_alternativa_related_name(self):
        self.assertEqual(self.pregunta.alternativas.count(), 2)


class IntentoEvaluacionModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='22222222-2'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripcion',
            docente_creador=self.docente
        )
        self.evaluacion = Evaluacion.objects.create(
            curso=self.curso,
            titulo='Evaluacion Test',
            porcentaje_aprobacion=70
        )
        self.intento = IntentoEvaluacion.objects.create(
            usuario=self.colaborador,
            evaluacion=self.evaluacion,
            puntaje_obtenido=85,
            aprobado=True
        )

    def test_intento_creation(self):
        self.assertEqual(self.intento.usuario, self.colaborador)
        self.assertEqual(self.intento.evaluacion, self.evaluacion)
        self.assertEqual(self.intento.puntaje_obtenido, 85)
        self.assertTrue(self.intento.aprobado)

    def test_intento_str_method(self):
        expected = f'{self.colaborador} - Evaluacion Test (85%)'
        self.assertEqual(str(self.intento), expected)

    def test_intento_related_names(self):
        self.assertEqual(self.colaborador.intentos_evaluacion.count(), 1)
        self.assertEqual(self.evaluacion.intentos.count(), 1)


class EvaluacionFormTests(TestCase):
    def setUp(self):
        self.valid_data = {
            'titulo': 'Nueva Evaluacion',
            'porcentaje_aprobacion': 70
        }

    def test_form_valid_data(self):
        form = EvaluacionForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_form_includes_max_intentos(self):
        form = EvaluacionForm()
        self.assertIn('max_intentos', form.fields)

    def test_form_porcentaje_min(self):
        data = self.valid_data.copy()
        data['porcentaje_aprobacion'] = -1
        form = EvaluacionForm(data=data)
        self.assertFalse(form.is_valid())

    def test_form_porcentaje_max(self):
        data = self.valid_data.copy()
        data['porcentaje_aprobacion'] = 101
        form = EvaluacionForm(data=data)
        self.assertFalse(form.is_valid())

    def test_form_porcentaje_boundary(self):
        data = self.valid_data.copy()
        data['porcentaje_aprobacion'] = 0
        form = EvaluacionForm(data=data)
        self.assertTrue(form.is_valid())
        data['porcentaje_aprobacion'] = 100
        form = EvaluacionForm(data=data)
        self.assertTrue(form.is_valid())


class EvaluacionListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='22222222-2'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripcion',
            docente_creador=self.docente
        )
        self.evaluacion = Evaluacion.objects.create(
            curso=self.curso,
            titulo='Evaluacion Test'
        )
        InscripcionCurso.objects.create(
            usuario=self.colaborador,
            curso=self.curso,
            estado='asignado'
        )

    def test_evaluacion_list_requires_login(self):
        response = self.client.get(reverse('evaluaciones:evaluacion_list', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 302)

    def test_evaluacion_list_accessible(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('evaluaciones:evaluacion_list', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)


class EvaluacionCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.docente2 = Usuario.objects.create_user(
            username='docente2', password='testpass', rol='docente', rut='22222222-2'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='33333333-3'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripcion',
            docente_creador=self.docente
        )

    def test_evaluacion_create_requires_docente_or_admin(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('evaluaciones:evaluacion_create', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 403)

    def test_evaluacion_create_only_owner_or_admin(self):
        self.client.login(username='docente2', password='testpass')
        response = self.client.get(reverse('evaluaciones:evaluacion_create', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 403)

    def test_evaluacion_create_get_form(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('evaluaciones:evaluacion_create', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)

    def test_evaluacion_create_post_valid(self):
        self.client.login(username='docente', password='testpass')
        preguntas_data = [{
            'texto': 'Pregunta 1',
            'alternativas': [{'texto': 'Alt 1'}, {'texto': 'Alt 2'}],
            'correctaIndex': 0
        }]
        response = self.client.post(
            reverse('evaluaciones:evaluacion_create', kwargs={'curso_pk': self.curso.pk}),
            {'titulo': 'Nueva Evaluacion', 'porcentaje_aprobacion': 70, 'preguntas': json.dumps(preguntas_data)}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Evaluacion.objects.filter(titulo='Nueva Evaluacion').exists())


class TomarEvaluacionViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='22222222-2'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripcion',
            docente_creador=self.docente
        )
        self.evaluacion = Evaluacion.objects.create(
            curso=self.curso,
            titulo='Evaluacion Test',
            porcentaje_aprobacion=70
        )
        self.pregunta1 = Pregunta.objects.create(
            evaluacion=self.evaluacion,
            texto='Pregunta 1'
        )
        self.alt1_p1 = Alternativa.objects.create(
            pregunta=self.pregunta1,
            texto='Correcta',
            es_correcta=True
        )
        self.alt2_p1 = Alternativa.objects.create(
            pregunta=self.pregunta1,
            texto='Incorrecta',
            es_correcta=False
        )
        InscripcionCurso.objects.create(
            usuario=self.colaborador,
            curso=self.curso,
            estado='asignado'
        )

    def test_tomar_evaluacion_requires_login(self):
        response = self.client.get(reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': self.evaluacion.pk}))
        self.assertEqual(response.status_code, 302)

    def test_tomar_evaluacion_requires_inscripcion(self):
        otro_curso = Curso.objects.create(
            titulo='Otro Curso',
            descripcion='Descripcion',
            docente_creador=self.docente
        )
        otra_evaluacion = Evaluacion.objects.create(
            curso=otro_curso,
            titulo='Otra Evaluacion',
            porcentaje_aprobacion=70
        )
        self.client.login(username='colaborador', password='testpass')
        response = self.client.post(
            reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': otra_evaluacion.pk}),
            {'respuestas': json.dumps({str(self.pregunta1.pk): str(self.alt1_p1.pk)})}
        )
        self.assertEqual(response.status_code, 302)

    def test_tomar_evaluacion_post_aprobado(self):
        self.client.login(username='colaborador', password='testpass')
        respuestas = {str(self.pregunta1.pk): str(self.alt1_p1.pk)}
        response = self.client.post(
            reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': self.evaluacion.pk}),
            {'respuestas': json.dumps(respuestas)}
        )
        self.assertEqual(response.status_code, 302)
        intento = IntentoEvaluacion.objects.filter(usuario=self.colaborador, evaluacion=self.evaluacion).first()
        self.assertIsNotNone(intento)
        self.assertEqual(intento.puntaje_obtenido, 100)
        self.assertTrue(intento.aprobado)

    def test_tomar_evaluacion_post_reprobado(self):
        self.client.login(username='colaborador', password='testpass')
        respuestas = {str(self.pregunta1.pk): str(self.alt2_p1.pk)}
        response = self.client.post(
            reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': self.evaluacion.pk}),
            {'respuestas': json.dumps(respuestas)}
        )
        self.assertEqual(response.status_code, 302)
        intento = IntentoEvaluacion.objects.filter(usuario=self.colaborador, evaluacion=self.evaluacion).first()
        self.assertIsNotNone(intento)
        self.assertEqual(intento.puntaje_obtenido, 0)
        self.assertFalse(intento.aprobado)

    def test_tomar_evaluacion_creates_intento_on_pass(self):
        self.client.login(username='colaborador', password='testpass')
        respuestas = {str(self.pregunta1.pk): str(self.alt1_p1.pk)}
        response = self.client.post(
            reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': self.evaluacion.pk}),
            {'respuestas': json.dumps(respuestas)}
        )
        self.assertEqual(response.status_code, 302)
        intento = IntentoEvaluacion.objects.filter(usuario=self.colaborador, evaluacion=self.evaluacion).first()
        self.assertIsNotNone(intento)
        self.assertEqual(intento.respuestas, respuestas)

    def test_tomar_evaluacion_marks_inscripcion_completado_when_all_evals_passed(self):
        self.client.login(username='colaborador', password='testpass')
        respuestas = {str(self.pregunta1.pk): str(self.alt1_p1.pk)}
        self.client.post(
            reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': self.evaluacion.pk}),
            {'respuestas': json.dumps(respuestas)}
        )
        inscripcion = InscripcionCurso.objects.get(usuario=self.colaborador, curso=self.curso)
        self.assertEqual(inscripcion.estado, 'completado')

    def test_certificado_auto_created_on_all_evals_passed(self):
        self.client.login(username='colaborador', password='testpass')
        respuestas = {str(self.pregunta1.pk): str(self.alt1_p1.pk)}
        self.client.post(
            reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': self.evaluacion.pk}),
            {'respuestas': json.dumps(respuestas)}
        )
        from certificados.models import Certificado
        cert = Certificado.objects.filter(usuario=self.colaborador, curso=self.curso).first()
        self.assertIsNotNone(cert)
        self.assertEqual(cert.estado, 'pendiente')

    def test_tomar_evaluacion_blocks_when_max_intentos_reached(self):
        self.evaluacion.max_intentos = 1
        self.evaluacion.save()
        IntentoEvaluacion.objects.create(
            usuario=self.colaborador,
            evaluacion=self.evaluacion,
            puntaje_obtenido=100,
            aprobado=True,
            respuestas={str(self.pregunta1.pk): str(self.alt1_p1.pk)}
        )
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': self.evaluacion.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(IntentoEvaluacion.objects.filter(usuario=self.colaborador, evaluacion=self.evaluacion).count(), 1)

    def test_resultado_evaluacion_shows_answer_summary(self):
        self.client.login(username='colaborador', password='testpass')
        respuestas = {str(self.pregunta1.pk): str(self.alt1_p1.pk)}
        self.client.post(
            reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': self.evaluacion.pk}),
            {'respuestas': json.dumps(respuestas)}
        )
        intento = IntentoEvaluacion.objects.get(usuario=self.colaborador, evaluacion=self.evaluacion)
        response = self.client.get(
            reverse('evaluaciones:resultado_evaluacion', kwargs={'pk': self.evaluacion.pk, 'intento_pk': intento.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pregunta1.texto)

    def test_resultado_evaluacion_shows_correct_alternatives(self):
        self.client.login(username='colaborador', password='testpass')
        respuestas = {str(self.pregunta1.pk): str(self.alt2_p1.pk)}
        self.client.post(
            reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': self.evaluacion.pk}),
            {'respuestas': json.dumps(respuestas)}
        )
        intento = IntentoEvaluacion.objects.get(usuario=self.colaborador, evaluacion=self.evaluacion)
        response = self.client.get(
            reverse('evaluaciones:resultado_evaluacion', kwargs={'pk': self.evaluacion.pk, 'intento_pk': intento.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.alt1_p1.texto)

    def test_resultado_evaluacion_defensive_redirect(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(
            reverse('evaluaciones:resultado_evaluacion', kwargs={'pk': self.evaluacion.pk, 'intento_pk': 9999}),
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'evaluaciones/evaluacion_list.html')

    def test_tomar_evaluacion_redirects_to_resultado_and_user_remains_authenticated(self):
        self.client.login(username='colaborador', password='testpass')
        respuestas = {str(self.pregunta1.pk): str(self.alt1_p1.pk)}
        response = self.client.post(
            reverse('evaluaciones:tomar_evaluacion', kwargs={'pk': self.evaluacion.pk}),
            {'respuestas': json.dumps(respuestas)},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'evaluaciones/resultado_evaluacion.html')
        self.assertTrue(response.context['user'].is_authenticated)

    def test_responder_pregunta_htmx_removed(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.post(
            f'/evaluacion/{self.evaluacion.pk}/respuesta/',
            data=json.dumps({'pregunta_pk': self.pregunta1.pk, 'alternativa_pk': self.alt1_p1.pk}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
