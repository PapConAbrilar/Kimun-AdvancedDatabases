from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from cursos.models import Curso, InscripcionCurso
from evaluaciones.models import Evaluacion, IntentoEvaluacion
from certificados.models import Certificado
from reportes.views import dashboard_reportes, reporte_curso, reporte_usuario

Usuario = get_user_model()


class DashboardReportesViewTests(TestCase):
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
            estado='completado'
        )

    def test_dashboard_reportes_requires_login(self):
        response = self.client.get(reverse('reportes:dashboard_reportes'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_reportes_requires_admin(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('reportes:dashboard_reportes'))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_reportes_accessible_by_admin(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('reportes:dashboard_reportes'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_usuarios', response.context)
        self.assertIn('total_cursos', response.context)
        self.assertIn('total_inscripciones', response.context)
        self.assertIn('total_certificados', response.context)


class ReporteCursoViewTests(TestCase):
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
            estado='completado'
        )

    def test_reporte_curso_requires_login(self):
        response = self.client.get(reverse('reportes:reporte_curso', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 302)

    def test_reporte_curso_requires_admin(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('reportes:reporte_curso', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 403)

    def test_reporte_curso_accessible_by_admin(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('reportes:reporte_curso', kwargs={'curso_pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('curso', response.context)
        self.assertIn('inscripciones', response.context)


class ReporteUsuarioViewTests(TestCase):
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
            estado='completado'
        )

    def test_reporte_usuario_requires_login(self):
        response = self.client.get(reverse('reportes:reporte_usuario', kwargs={'usuario_pk': self.colaborador.pk}))
        self.assertEqual(response.status_code, 302)

    def test_reporte_usuario_requires_admin(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('reportes:reporte_usuario', kwargs={'usuario_pk': self.colaborador.pk}))
        self.assertEqual(response.status_code, 403)

    def test_reporte_usuario_accessible_by_admin(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('reportes:reporte_usuario', kwargs={'usuario_pk': self.colaborador.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('usuario', response.context)
        self.assertIn('inscripciones', response.context)
        self.assertIn('intentos', response.context)
        self.assertIn('certificados', response.context)


class ReportesRBACTests(TestCase):
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

    def test_all_reportes_views_require_admin(self):
        views_to_test = [
            reverse('reportes:dashboard_reportes'),
            reverse('reportes:reporte_curso', kwargs={'curso_pk': self.curso.pk}),
            reverse('reportes:reporte_usuario', kwargs={'usuario_pk': self.colaborador.pk}),
        ]
        
        for view_url in views_to_test:
            self.client.login(username='docente', password='testpass')
            response = self.client.get(view_url)
            self.assertEqual(response.status_code, 403, f"View {view_url} should require admin")
            
            self.client.login(username='colaborador', password='testpass')
            response = self.client.get(view_url)
            self.assertEqual(response.status_code, 403, f"View {view_url} should require admin")
            
            self.client.login(username='admin', password='testpass')
            response = self.client.get(view_url)
            self.assertEqual(response.status_code, 200, f"View {view_url} should be accessible to admin")
