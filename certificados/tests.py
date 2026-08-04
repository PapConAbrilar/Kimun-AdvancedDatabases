from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from certificados.models import Certificado
from cursos.models import Curso, InscripcionCurso

Usuario = get_user_model()


class CertificadoModelTests(TestCase):
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
        pdf_content = SimpleUploadedFile("certificado.pdf", b"PDF content", content_type="application/pdf")
        self.certificado = Certificado.objects.create(
            usuario=self.colaborador,
            curso=self.curso,
            archivo_pdf=pdf_content
        )

    def test_certificado_creation(self):
        self.assertEqual(self.certificado.usuario, self.colaborador)
        self.assertEqual(self.certificado.curso, self.curso)
        self.assertIsNotNone(self.certificado.codigo_verificacion)
        self.assertIsNotNone(self.certificado.fecha_emision)

    def test_certificado_str_method(self):
        expected = f'Certificado {self.colaborador} - Curso Test (Pendiente)'
        self.assertEqual(str(self.certificado), expected)

    def test_certificado_codigo_unico(self):
        certificado2 = Certificado.objects.create(
            usuario=self.docente,
            curso=self.curso
        )
        self.assertNotEqual(self.certificado.codigo_verificacion, certificado2.codigo_verificacion)

    def test_certificado_related_names(self):
        self.assertEqual(self.colaborador.certificados.count(), 1)
        self.assertEqual(self.curso.certificados.count(), 1)

    def test_certificado_default_estado(self):
        cert = Certificado.objects.create(usuario=self.colaborador, curso=self.curso)
        self.assertEqual(cert.estado, 'pendiente')

    def test_certificado_estado_choices(self):
        choices = dict(Certificado.ESTADO_CHOICES)
        self.assertIn('pendiente', choices)
        self.assertIn('aprobado', choices)
        self.assertIn('rechazado', choices)

    def test_certificado_str_includes_estado(self):
        cert = Certificado.objects.create(usuario=self.colaborador, curso=self.curso)
        self.assertIn('Pendiente', str(cert))


class CertificadoListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='22222222-2'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripcion',
            docente_creador=self.docente
        )

    def test_certificado_list_requires_admin(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('certificados:certificado_list'))
        self.assertEqual(response.status_code, 403)

    def test_certificado_list_accessible_by_admin(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('certificados:certificado_list'))
        self.assertEqual(response.status_code, 200)


class MisCertificadosViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='22222222-2'
        )
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='33333333-3'
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

    def test_mis_certificados_requires_login(self):
        response = self.client.get(reverse('certificados:mis_certificados'))
        self.assertEqual(response.status_code, 302)

    def test_mis_certificados_admin_redirects(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('certificados:mis_certificados'))
        self.assertEqual(response.status_code, 302)

    def test_mis_certificados_colaborador(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('certificados:mis_certificados'))
        self.assertEqual(response.status_code, 200)


class DescargarCertificadoViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='22222222-2'
        )
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='33333333-3'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripcion',
            docente_creador=self.docente
        )
        pdf_content = SimpleUploadedFile("certificado.pdf", b"PDF content", content_type="application/pdf")
        self.certificado = Certificado.objects.create(
            usuario=self.colaborador,
            curso=self.curso,
            archivo_pdf=pdf_content,
            estado='aprobado'
        )

    def test_descargar_requires_login(self):
        response = self.client.get(reverse('certificados:descargar_certificado', kwargs={'pk': self.certificado.pk}))
        self.assertEqual(response.status_code, 302)

    def test_descargar_owner_can_access(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('certificados:descargar_certificado', kwargs={'pk': self.certificado.pk}))
        self.assertEqual(response.status_code, 200)

    def test_descargar_admin_can_access(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('certificados:descargar_certificado', kwargs={'pk': self.certificado.pk}))
        self.assertEqual(response.status_code, 200)

    def test_descargar_other_user_cannot_access(self):
        colaborador2 = Usuario.objects.create_user(
            username='colab2', password='testpass', rol='colaborador', rut='44444444-4'
        )
        self.client.login(username='colab2', password='testpass')
        response = self.client.get(reverse('certificados:descargar_certificado', kwargs={'pk': self.certificado.pk}))
        self.assertEqual(response.status_code, 302)

    def test_descargar_pending_certificado_blocked(self):
        cert = Certificado.objects.create(usuario=self.colaborador, curso=self.curso, estado='pendiente')
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('certificados:descargar_certificado', args=[cert.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('certificados:mis_certificados'))

    def test_descargar_rejected_certificado_blocked(self):
        cert = Certificado.objects.create(usuario=self.colaborador, curso=self.curso, estado='rechazado')
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('certificados:descargar_certificado', args=[cert.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('certificados:mis_certificados'))


class VerificarCertificadoViewTests(TestCase):
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
        self.certificado = Certificado.objects.create(
            usuario=self.colaborador,
            curso=self.curso
        )

    def test_verificar_certificado_valid(self):
        from django.test import Client
        client = Client()
        response = client.get(reverse('certificados:verificar_certificado', kwargs={
            'codigo': self.certificado.codigo_verificacion
        }))
        self.assertEqual(response.status_code, 200)


class CertificadosPendientesViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(username='admin', password='testpass', rol='admin', rut='11111111-1')
        self.docente = Usuario.objects.create_user(username='docente', password='testpass', rol='docente', rut='22222222-2')
        self.colaborador = Usuario.objects.create_user(username='colaborador', password='testpass', rol='colaborador', rut='33333333-3')
        self.curso = Curso.objects.create(titulo='Test Curso', descripcion='...', estado='publicado', docente_creador=self.docente)

    def test_admin_sees_all_pending(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('certificados:certificados_pendientes'))
        self.assertEqual(response.status_code, 200)

    def test_docente_sees_own_pending(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('certificados:certificados_pendientes'))
        self.assertEqual(response.status_code, 200)

    def test_colaborador_blocked(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('certificados:certificados_pendientes'))
        self.assertEqual(response.status_code, 403)

    def test_aprobar_changes_estado(self):
        cert = Certificado.objects.create(usuario=self.colaborador, curso=self.curso, estado='pendiente')
        self.client.login(username='docente', password='testpass')
        response = self.client.post(reverse('certificados:aprobar_certificado', args=[cert.pk]))
        cert.refresh_from_db()
        self.assertEqual(cert.estado, 'aprobado')

    def test_rechazar_changes_estado(self):
        cert = Certificado.objects.create(usuario=self.colaborador, curso=self.curso, estado='pendiente')
        self.client.login(username='docente', password='testpass')
        response = self.client.post(reverse('certificados:rechazar_certificado', args=[cert.pk]))
        cert.refresh_from_db()
        self.assertEqual(cert.estado, 'rechazado')
