from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
from cursos.models import Categoria, Curso, Material, InscripcionCurso, Clase, ClaseCompletado
from cursos.forms import CursoForm, MaterialForm, CategoriaForm, ClaseForm
from cursos.views import curso_list, curso_create, curso_detail, material_create, categoria_create

Usuario = get_user_model()


class CategoriaModelTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nombre='Seguridad Laboral',
            color='#ff0000',
            descripcion='Cursos de seguridad en el trabajo'
        )

    def test_categoria_creation(self):
        self.assertEqual(self.categoria.nombre, 'Seguridad Laboral')
        self.assertEqual(self.categoria.color, '#ff0000')
        self.assertEqual(self.categoria.descripcion, 'Cursos de seguridad en el trabajo')

    def test_categoria_str_method(self):
        self.assertEqual(str(self.categoria), 'Seguridad Laboral')

    def test_categoria_unique_constraint(self):
        with self.assertRaises(Exception):
            Categoria.objects.create(nombre='Seguridad Laboral')

    def test_categoria_ordering(self):
        cat2 = Categoria.objects.create(nombre='Administración', color='#00ff00')
        cat3 = Categoria.objects.create(nombre='Tecnología', color='#0000ff')
        categorias = list(Categoria.objects.all())
        self.assertEqual(categorias[0].nombre, 'Administración')
        self.assertEqual(categorias[1].nombre, 'Seguridad Laboral')
        self.assertEqual(categorias[2].nombre, 'Tecnología')

    def test_categoria_verbose_names(self):
        self.assertEqual(Categoria._meta.verbose_name, 'Categoría')
        self.assertEqual(Categoria._meta.verbose_name_plural, 'Categorías')


class CursoModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.categoria = Categoria.objects.create(nombre='Test Categoria', color='#000000')
        self.curso = Curso.objects.create(
            titulo='Curso de Primeros Auxilios',
            descripcion='Aprende primeros auxilios básicos',
            docente_creador=self.docente,
            categoria=self.categoria,
            estado='publicado'
        )

    def test_curso_creation(self):
        self.assertEqual(self.curso.titulo, 'Curso de Primeros Auxilios')
        self.assertEqual(self.curso.descripcion, 'Aprende primeros auxilios básicos')
        self.assertEqual(self.curso.docente_creador, self.docente)
        self.assertEqual(self.curso.categoria, self.categoria)
        self.assertEqual(self.curso.estado, 'publicado')

    def test_curso_str_method(self):
        self.assertEqual(str(self.curso), 'Curso de Primeros Auxilios')

    def test_curso_estado_choices(self):
        choices = dict(Curso.ESTADO_CHOICES)
        self.assertIn('borrador', choices)
        self.assertIn('publicado', choices)
        self.assertEqual(choices['borrador'], 'Borrador')
        self.assertEqual(choices['publicado'], 'Publicado')

    def test_curso_default_estado(self):
        curso = Curso.objects.create(
            titulo='Nuevo Curso',
            descripcion='Descripción',
            docente_creador=self.docente
        )
        self.assertEqual(curso.estado, 'borrador')

    def test_curso_related_names(self):
        self.assertEqual(self.docente.cursos_creados.count(), 1)
        self.assertEqual(self.categoria.cursos.count(), 1)

    def test_curso_fecha_limite(self):
        future_date = timezone.now() + timedelta(days=30)
        curso = Curso.objects.create(
            titulo='Curso con Fecha',
            descripcion='Descripción',
            docente_creador=self.docente,
            fecha_limite=future_date
        )
        self.assertIsNotNone(curso.fecha_limite)


class MaterialModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripción',
            docente_creador=self.docente
        )
        self.material_pdf = Material.objects.create(
            curso=self.curso,
            titulo='Manual PDF',
            tipo='pdf',
            archivo='materiales/test.pdf'
        )
        self.material_video = Material.objects.create(
            curso=self.curso,
            titulo='Video Tutorial',
            tipo='video',
            url='https://www.youtube.com/watch?v=test'
        )

    def test_material_pdf_creation(self):
        self.assertEqual(self.material_pdf.titulo, 'Manual PDF')
        self.assertEqual(self.material_pdf.tipo, 'pdf')
        self.assertEqual(self.material_pdf.archivo, 'materiales/test.pdf')

    def test_material_video_creation(self):
        self.assertEqual(self.material_video.titulo, 'Video Tutorial')
        self.assertEqual(self.material_video.tipo, 'video')
        self.assertEqual(self.material_video.url, 'https://www.youtube.com/watch?v=test')

    def test_material_str_method(self):
        self.assertEqual(str(self.material_pdf), 'Manual PDF (PDF)')
        self.assertEqual(str(self.material_video), 'Video Tutorial (Video URL)')

    def test_material_tipo_choices(self):
        choices = dict(Material.TIPO_CHOICES)
        self.assertIn('pdf', choices)
        self.assertIn('video', choices)
        self.assertEqual(choices['pdf'], 'PDF')
        self.assertEqual(choices['video'], 'Video URL')

    def test_material_related_name(self):
        self.assertEqual(self.curso.materiales.count(), 2)


class InscripcionCursoModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='22222222-2'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripción',
            docente_creador=self.docente
        )
        self.inscripcion = InscripcionCurso.objects.create(
            usuario=self.colaborador,
            curso=self.curso,
            estado='asignado'
        )

    def test_inscripcion_creation(self):
        self.assertEqual(self.inscripcion.usuario, self.colaborador)
        self.assertEqual(self.inscripcion.curso, self.curso)
        self.assertEqual(self.inscripcion.estado, 'asignado')

    def test_inscripcion_str_method(self):
        expected = f'{self.colaborador} - Curso Test (Asignado)'
        self.assertEqual(str(self.inscripcion), expected)

    def test_inscripcion_estado_choices(self):
        choices = dict(InscripcionCurso.ESTADO_CHOICES)
        self.assertIn('asignado', choices)
        self.assertIn('en_progreso', choices)
        self.assertIn('completado', choices)

    def test_inscripcion_unique_together(self):
        with self.assertRaises(Exception):
            InscripcionCurso.objects.create(
                usuario=self.colaborador,
                curso=self.curso,
                estado='en_progreso'
            )

    def test_inscripcion_related_names(self):
        self.assertEqual(self.colaborador.inscripciones.count(), 1)
        self.assertEqual(self.curso.inscripciones.count(), 1)

    def test_inscripcion_default_estado(self):
        colaborador2 = Usuario.objects.create_user(
            username='colab2', password='testpass', rol='colaborador', rut='33333333-3'
        )
        inscripcion = InscripcionCurso.objects.create(
            usuario=colaborador2,
            curso=self.curso
        )
        self.assertEqual(inscripcion.estado, 'asignado')


class ClaseModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripción',
            docente_creador=self.docente
        )
        self.clase1 = Clase.objects.create(
            curso=self.curso,
            titulo='Introducción',
            contenido='<p>Contenido de introducción</p>',
            orden=1
        )
        self.clase2 = Clase.objects.create(
            curso=self.curso,
            titulo='Tema Avanzado',
            contenido='<p>Contenido avanzado</p>',
            orden=2
        )

    def test_clase_creation(self):
        self.assertEqual(self.clase1.titulo, 'Introducción')
        self.assertEqual(self.clase1.orden, 1)
        self.assertEqual(self.clase1.contenido, '<p>Contenido de introducción</p>')

    def test_clase_str_method(self):
        self.assertEqual(str(self.clase1), '1. Introducción')
        self.assertEqual(str(self.clase2), '2. Tema Avanzado')

    def test_clase_ordering(self):
        clases = list(Clase.objects.filter(curso=self.curso))
        self.assertEqual(clases[0].titulo, 'Introducción')
        self.assertEqual(clases[1].titulo, 'Tema Avanzado')

    def test_clase_get_clase_anterior(self):
        anterior = self.clase2.get_clase_anterior()
        self.assertEqual(anterior, self.clase1)
        self.assertIsNone(self.clase1.get_clase_anterior())

    def test_clase_get_siguiente_clase(self):
        siguiente = self.clase1.get_siguiente_clase()
        self.assertEqual(siguiente, self.clase2)
        self.assertIsNone(self.clase2.get_siguiente_clase())

    def test_clase_unique_constraint(self):
        with self.assertRaises(Exception):
            Clase.objects.create(
                curso=self.curso,
                titulo='Otra Introducción',
                orden=1
            )

    def test_clase_orden_validation(self):
        from django.core.exceptions import ValidationError
        clase = Clase(curso=self.curso, titulo='Test', orden=0)
        with self.assertRaises(ValidationError):
            clase.clean()


class ClaseCompletadoModelTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='22222222-2'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripción',
            docente_creador=self.docente
        )
        self.clase = Clase.objects.create(
            curso=self.curso,
            titulo='Clase 1',
            contenido='<p>Contenido</p>',
            orden=1
        )
        self.completado = ClaseCompletado.objects.create(
            usuario=self.colaborador,
            clase=self.clase
        )

    def test_clase_completado_creation(self):
        self.assertEqual(self.completado.usuario, self.colaborador)
        self.assertEqual(self.completado.clase, self.clase)
        self.assertIsNotNone(self.completado.fecha_completado)

    def test_clase_completado_str_method(self):
        fecha_str = self.completado.fecha_completado.strftime('%d/%m/%Y')
        expected = f'{self.colaborador} - Clase 1 ({fecha_str})'
        self.assertEqual(str(self.completado), expected)

    def test_clase_completado_unique_together(self):
        with self.assertRaises(Exception):
            ClaseCompletado.objects.create(
                usuario=self.colaborador,
                clase=self.clase
            )

    def test_clase_completado_related_names(self):
        self.assertEqual(self.colaborador.clases_completadas.count(), 1)
        self.assertEqual(self.clase.completados.count(), 1)


class CursoFormTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre='Test Categoria', color='#000000')
        self.valid_data = {
            'titulo': 'Nuevo Curso',
            'descripcion': 'Descripción del curso',
            'categoria': self.categoria.pk,
            'estado': 'publicado',
            'fecha_limite': ''
        }

    def test_form_valid_data(self):
        form = CursoForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

    def test_form_categoria_optional(self):
        data = self.valid_data.copy()
        del data['categoria']
        form = CursoForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_fecha_limite_optional(self):
        data = self.valid_data.copy()
        del data['fecha_limite']
        form = CursoForm(data=data)
        self.assertTrue(form.is_valid())


class MaterialFormTests(TestCase):
    def setUp(self):
        self.valid_pdf_data = {
            'titulo': 'Manual PDF',
            'tipo': 'pdf',
            'url': ''
        }
        self.valid_video_data = {
            'titulo': 'Video Tutorial',
            'tipo': 'video',
            'url': 'https://www.youtube.com/watch?v=test'
        }

    def test_form_pdf_requires_archivo(self):
        form = MaterialForm(data=self.valid_pdf_data)
        self.assertFalse(form.is_valid())
        self.assertIn('archivo', form.errors)

    def test_form_video_requires_url(self):
        data = self.valid_video_data.copy()
        data['url'] = ''
        form = MaterialForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('url', form.errors)

    def test_form_pdf_with_archivo(self):
        pdf_file = SimpleUploadedFile("test.pdf", b"file content", content_type="application/pdf")
        data = self.valid_pdf_data.copy()
        form = MaterialForm(data=data, files={'archivo': pdf_file})
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

    def test_form_video_valid(self):
        form = MaterialForm(data=self.valid_video_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")


class CategoriaFormTests(TestCase):
    def setUp(self):
        self.valid_data = {
            'nombre': 'Nueva Categoría',
            'color': '#ff5733',
            'descripcion': 'Descripción de la categoría'
        }

    def test_form_valid_data(self):
        form = CategoriaForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

    def test_form_descripcion_optional(self):
        data = self.valid_data.copy()
        del data['descripcion']
        form = CategoriaForm(data=data)
        self.assertTrue(form.is_valid())


class ClaseFormTests(TestCase):
    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripción',
            docente_creador=self.docente
        )
        self.valid_data = {
            'titulo': 'Nueva Clase',
            'contenido': '<p>Contenido de la clase</p>',
            'orden': 1
        }

    def test_form_valid_data(self):
        form = ClaseForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

    def test_form_orden_validation(self):
        data = self.valid_data.copy()
        data['orden'] = 0
        form = ClaseForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('orden', form.errors)

    def test_form_orden_negative(self):
        data = self.valid_data.copy()
        data['orden'] = -1
        form = ClaseForm(data=data)
        self.assertFalse(form.is_valid())


class CursoListViewTests(TestCase):
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
        self.curso_publicado = Curso.objects.create(
            titulo='Curso Publicado',
            descripcion='Descripción',
            docente_creador=self.docente,
            estado='publicado'
        )
        self.curso_borrador = Curso.objects.create(
            titulo='Curso Borrador',
            descripcion='Descripción',
            docente_creador=self.docente,
            estado='borrador'
        )

    def test_curso_list_requires_login(self):
        response = self.client.get(reverse('cursos:curso_list'))
        self.assertEqual(response.status_code, 302)

    def test_curso_list_admin_sees_all(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('cursos:curso_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Curso Publicado')
        self.assertContains(response, 'Curso Borrador')

    def test_curso_list_docente_sees_all(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('cursos:curso_list'))
        self.assertEqual(response.status_code, 200)

    def test_curso_list_colaborador_only_publicados(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('cursos:curso_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('usuarios:mis_cursos'))

    def test_curso_list_search_filter(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('cursos:curso_list') + '?q=Publicado')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Curso Publicado')

    def test_curso_list_colaborador_redirected(self):
        """Colaborador should be redirected to mis_cursos"""
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('cursos:curso_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('usuarios:mis_cursos'))

    def test_curso_list_admin_not_redirected(self):
        """Admin should see curso_list normally"""
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('cursos:curso_list'))
        self.assertEqual(response.status_code, 200)

    def test_curso_list_docente_not_redirected(self):
        """Docente should see curso_list normally"""
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('cursos:curso_list'))
        self.assertEqual(response.status_code, 200)


class CursoDetailViewTests(TestCase):
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
            descripcion='Descripción',
            docente_creador=self.docente,
            estado='publicado'
        )

    def test_curso_detail_requires_login(self):
        response = self.client.get(reverse('cursos:curso_detail', kwargs={'pk': self.curso.pk}))
        self.assertEqual(response.status_code, 302)

    def test_curso_detail_accessible(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('cursos:curso_detail', kwargs={'pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Curso Test')

    def test_curso_borrador_docente_can_access(self):
        borrador = Curso.objects.create(
            titulo='Borrador Test',
            descripcion='Descripción',
            docente_creador=self.docente,
            estado='borrador'
        )
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('cursos:curso_detail', kwargs={'pk': borrador.pk}))
        self.assertEqual(response.status_code, 200)


class CursoCreateViewTests(TestCase):
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

    def test_curso_create_requires_docente_or_admin(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('cursos:curso_create'))
        self.assertEqual(response.status_code, 403)

    def test_curso_create_get_form(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('cursos:curso_create'))
        self.assertEqual(response.status_code, 200)

    def test_curso_create_post_valid(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.post(reverse('cursos:curso_create'), {
            'titulo': 'Nuevo Curso',
            'descripcion': 'Descripción del curso',
            'estado': 'borrador'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Curso.objects.filter(titulo='Nuevo Curso').exists())


class CursoEditViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.docente2 = Usuario.objects.create_user(
            username='docente2', password='testpass', rol='docente', rut='22222222-2'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripción',
            docente_creador=self.docente
        )

    def test_curso_edit_only_by_owner_or_admin(self):
        self.client.login(username='docente2', password='testpass')
        response = self.client.get(reverse('cursos:curso_edit', kwargs={'pk': self.curso.pk}))
        self.assertEqual(response.status_code, 403)

    def test_curso_edit_owner_can_access(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('cursos:curso_edit', kwargs={'pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)

    def test_curso_edit_post_valid(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.post(reverse('cursos:curso_edit', kwargs={'pk': self.curso.pk}), {
            'titulo': 'Curso Actualizado',
            'descripcion': 'Nueva descripción',
            'estado': 'publicado'
        })
        self.assertEqual(response.status_code, 302)
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.titulo, 'Curso Actualizado')


class MaterialCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.curso = Curso.objects.create(
            titulo='Curso Test',
            descripcion='Descripción',
            docente_creador=self.docente
        )

    def test_material_create_requires_owner_or_admin(self):
        docente2 = Usuario.objects.create_user(
            username='docente2', password='testpass', rol='docente', rut='22222222-2'
        )
        self.client.login(username='docente2', password='testpass')
        response = self.client.get(reverse('cursos:material_create', kwargs={'pk': self.curso.pk}))
        self.assertEqual(response.status_code, 403)

    def test_material_create_get_form(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('cursos:material_create', kwargs={'pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)


class CategoriaCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='22222222-2'
        )

    def test_categoria_create_requires_admin(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('cursos:categoria_create'))
        self.assertEqual(response.status_code, 403)

    def test_categoria_create_get_form(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('cursos:categoria_create'))
        self.assertEqual(response.status_code, 200)

    def test_categoria_create_post_valid(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.post(reverse('cursos:categoria_create'), {
            'nombre': 'Nueva Categoría',
            'color': '#ff5733',
            'descripcion': 'Descripción'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Categoria.objects.filter(nombre='Nueva Categoría').exists())


class ClaseViewTests(TestCase):
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
            descripcion='Descripción',
            docente_creador=self.docente
        )
        self.clase = Clase.objects.create(
            curso=self.curso,
            titulo='Clase 1',
            contenido='<p>Contenido</p>',
            orden=1
        )
        InscripcionCurso.objects.create(
            usuario=self.colaborador,
            curso=self.curso,
            estado='asignado'
        )

    def test_clase_list_requires_login(self):
        response = self.client.get(reverse('cursos:clase_list', kwargs={'pk': self.curso.pk}))
        self.assertEqual(response.status_code, 302)

    def test_clase_list_accessible_by_inscrito(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('cursos:clase_list', kwargs={'pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)

    def test_clase_detail_accessible(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('cursos:clase_detail', kwargs={'pk': self.clase.pk}))
        self.assertEqual(response.status_code, 200)

    def test_clase_create_requires_docente(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('cursos:clase_create', kwargs={'pk': self.curso.pk}))
        self.assertEqual(response.status_code, 403)

    def test_clase_create_get_form(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('cursos:clase_create', kwargs={'pk': self.curso.pk}))
        self.assertEqual(response.status_code, 200)


class ClaseCompletarViewTests(TestCase):
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
            descripcion='Descripción',
            docente_creador=self.docente
        )
        self.clase1 = Clase.objects.create(
            curso=self.curso,
            titulo='Clase 1',
            contenido='<p>Contenido 1</p>',
            orden=1
        )
        self.clase2 = Clase.objects.create(
            curso=self.curso,
            titulo='Clase 2',
            contenido='<p>Contenido 2</p>',
            orden=2
        )
        InscripcionCurso.objects.create(
            usuario=self.colaborador,
            curso=self.curso,
            estado='asignado'
        )

    def test_completar_clase_requires_post(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('cursos:clase_completar', kwargs={'pk': self.clase1.pk}))
        self.assertEqual(response.status_code, 302)

    def test_completar_clase_requires_colaborador(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.post(reverse('cursos:clase_completar', kwargs={'pk': self.clase1.pk}))
        self.assertEqual(response.status_code, 302)

    def test_completar_clase_requires_inscripcion(self):
        colaborador2 = Usuario.objects.create_user(
            username='colab2', password='testpass', rol='colaborador', rut='33333333-3'
        )
        self.client.login(username='colab2', password='testpass')
        response = self.client.post(reverse('cursos:clase_completar', kwargs={'pk': self.clase1.pk}))
        self.assertEqual(response.status_code, 302)

    def test_completar_clase_success(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.post(reverse('cursos:clase_completar', kwargs={'pk': self.clase1.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClaseCompletado.objects.filter(usuario=self.colaborador, clase=self.clase1).exists())

    def test_completar_clase_requires_previous(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.post(reverse('cursos:clase_completar', kwargs={'pk': self.clase2.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ClaseCompletado.objects.filter(usuario=self.colaborador, clase=self.clase2).exists())

    def test_completar_clase_already_completed(self):
        ClaseCompletado.objects.create(usuario=self.colaborador, clase=self.clase1)
        self.client.login(username='colaborador', password='testpass')
        response = self.client.post(reverse('cursos:clase_completar', kwargs={'pk': self.clase1.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ClaseCompletado.objects.filter(usuario=self.colaborador, clase=self.clase1).count(), 1)
