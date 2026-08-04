from django.test import TestCase, RequestFactory, Client
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.messages import get_messages
from usuarios.decorators import role_required, admin_required, docente_or_admin_required, course_owner_or_admin
from usuarios.models import AreaCargo, Recordatorio
from usuarios.views import UsuarioForm
from cursos.models import Curso

Usuario = get_user_model()


def dummy_view(request, **kwargs):
    return HttpResponse('OK')


class RoleRequiredDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='22222222-2'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='33333333-3'
        )

    def test_admin_can_access_admin_view(self):
        request = self.factory.get('/test/')
        request.user = self.admin
        decorated_view = role_required('admin')(dummy_view)
        response = decorated_view(request)
        self.assertEqual(response.status_code, 200)

    def test_docente_cannot_access_admin_view(self):
        request = self.factory.get('/test/')
        request.user = self.docente
        decorated_view = role_required('admin')(dummy_view)
        response = decorated_view(request)
        self.assertEqual(response.status_code, 403)

    def test_colaborador_cannot_access_admin_view(self):
        request = self.factory.get('/test/')
        request.user = self.colaborador
        decorated_view = role_required('admin')(dummy_view)
        response = decorated_view(request)
        self.assertEqual(response.status_code, 403)

    def test_docente_can_access_docente_or_admin_view(self):
        request = self.factory.get('/test/')
        request.user = self.docente
        decorated_view = docente_or_admin_required(dummy_view)
        response = decorated_view(request)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_docente_or_admin_view(self):
        request = self.factory.get('/test/')
        request.user = self.admin
        decorated_view = docente_or_admin_required(dummy_view)
        response = decorated_view(request)
        self.assertEqual(response.status_code, 200)

    def test_colaborador_cannot_access_docente_or_admin_view(self):
        request = self.factory.get('/test/')
        request.user = self.colaborador
        decorated_view = docente_or_admin_required(dummy_view)
        response = decorated_view(request)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_gets_403(self):
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        decorated_view = role_required('admin')(dummy_view)
        response = decorated_view(request)
        self.assertEqual(response.status_code, 403)


class CourseOwnerOrAdminDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='44444444-4'
        )
        self.docente_owner = Usuario.objects.create_user(
            username='docente_owner', password='testpass', rol='docente', rut='55555555-5'
        )
        self.docente_other = Usuario.objects.create_user(
            username='docente_other', password='testpass', rol='docente', rut='66666666-6'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='77777777-7'
        )
        self.curso = Curso.objects.create(
            titulo='Test Curso',
            descripcion='Test',
            docente_creador=self.docente_owner
        )

    def test_admin_can_access_any_course(self):
        request = self.factory.get('/test/')
        request.user = self.admin
        decorated_view = course_owner_or_admin(dummy_view)
        response = decorated_view(request, pk=self.curso.pk)
        self.assertEqual(response.status_code, 200)

    def test_owner_can_access_own_course(self):
        request = self.factory.get('/test/')
        request.user = self.docente_owner
        decorated_view = course_owner_or_admin(dummy_view)
        response = decorated_view(request, pk=self.curso.pk)
        self.assertEqual(response.status_code, 200)

    def test_other_docente_cannot_access_course(self):
        request = self.factory.get('/test/')
        request.user = self.docente_other
        decorated_view = course_owner_or_admin(dummy_view)
        response = decorated_view(request, pk=self.curso.pk)
        self.assertEqual(response.status_code, 403)

    def test_colaborador_cannot_access_course(self):
        request = self.factory.get('/test/')
        request.user = self.colaborador
        decorated_view = course_owner_or_admin(dummy_view)
        response = decorated_view(request, pk=self.curso.pk)
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_course_returns_403(self):
        request = self.factory.get('/test/')
        request.user = self.docente_owner
        decorated_view = course_owner_or_admin(dummy_view)
        response = decorated_view(request, pk=9999)
        self.assertEqual(response.status_code, 403)


class AreaCargoModelTests(TestCase):
    def setUp(self):
        self.area = AreaCargo.objects.create(nombre='Recursos Humanos')

    def test_area_cargo_creation(self):
        self.assertEqual(self.area.nombre, 'Recursos Humanos')
        self.assertEqual(str(self.area), 'Recursos Humanos')

    def test_area_cargo_unique_constraint(self):
        with self.assertRaises(Exception):
            AreaCargo.objects.create(nombre='Recursos Humanos')

    def test_area_cargo_verbose_names(self):
        self.assertEqual(AreaCargo._meta.verbose_name, 'Área/Cargo')
        self.assertEqual(AreaCargo._meta.verbose_name_plural, 'Áreas/Cargos')


class UsuarioModelTests(TestCase):
    def setUp(self):
        self.area = AreaCargo.objects.create(nombre='Tecnología')
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User',
            email='test@example.com',
            rut='12345678-9',
            rol='colaborador',
            cargo=self.area
        )

    def test_usuario_creation(self):
        self.assertEqual(self.usuario.username, 'testuser')
        self.assertEqual(self.usuario.first_name, 'Test')
        self.assertEqual(self.usuario.last_name, 'User')
        self.assertEqual(self.usuario.email, 'test@example.com')
        self.assertEqual(self.usuario.rut, '12345678-9')
        self.assertEqual(self.usuario.rol, 'colaborador')
        self.assertEqual(self.usuario.cargo, self.area)

    def test_usuario_str_method(self):
        expected = 'Test User (Colaborador)'
        self.assertEqual(str(self.usuario), expected)

    def test_usuario_str_without_names(self):
        usuario = Usuario.objects.create_user(
            username='nonameuser',
            password='testpass123',
            rut='98765432-1'
        )
        self.assertEqual(str(usuario), 'nonameuser (Colaborador)')

    def test_usuario_rol_choices(self):
        choices = dict(Usuario.ROL_CHOICES)
        self.assertIn('admin', choices)
        self.assertIn('docente', choices)
        self.assertIn('colaborador', choices)
        self.assertEqual(choices['admin'], 'Administrador')
        self.assertEqual(choices['docente'], 'Docente')
        self.assertEqual(choices['colaborador'], 'Colaborador')

    def test_usuario_default_rol(self):
        usuario = Usuario.objects.create_user(
            username='defaultuser',
            password='testpass123',
            rut='11111111-1'
        )
        self.assertEqual(usuario.rol, 'colaborador')

    def test_usuario_rut_unique(self):
        with self.assertRaises(Exception):
            Usuario.objects.create_user(
                username='anotheruser',
                password='testpass123',
                rut='12345678-9'
            )

    def test_usuario_get_rol_display(self):
        self.assertEqual(self.usuario.get_rol_display(), 'Colaborador')
        self.usuario.rol = 'admin'
        self.usuario.save()
        self.assertEqual(self.usuario.get_rol_display(), 'Administrador')

    def test_usuario_verbose_names(self):
        self.assertEqual(Usuario._meta.verbose_name, 'Usuario')
        self.assertEqual(Usuario._meta.verbose_name_plural, 'Usuarios')


class RecordatorioModelTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            password='testpass123',
            rut='12345678-9'
        )
        self.curso = Curso.objects.create(
            titulo='Curso de Prueba',
            descripcion='Descripción del curso',
            docente_creador=self.usuario
        )
        self.recordatorio = Recordatorio.objects.create(
            usuario=self.usuario,
            curso=self.curso,
            tipo='7_dias'
        )

    def test_recordatorio_creation(self):
        self.assertEqual(self.recordatorio.usuario, self.usuario)
        self.assertEqual(self.recordatorio.curso, self.curso)
        self.assertEqual(self.recordatorio.tipo, '7_dias')

    def test_recordatorio_str_method(self):
        expected = f'{self.usuario} - Curso de Prueba (7 días antes)'
        self.assertEqual(str(self.recordatorio), expected)

    def test_recordatorio_tipo_choices(self):
        choices = dict(Recordatorio.TIPO_CHOICES)
        self.assertIn('7_dias', choices)
        self.assertIn('3_dias', choices)
        self.assertIn('1_dia', choices)
        self.assertIn('vencimiento', choices)

    def test_recordatorio_unique_together(self):
        with self.assertRaises(Exception):
            Recordatorio.objects.create(
                usuario=self.usuario,
                curso=self.curso,
                tipo='7_dias'
            )

    def test_recordatorio_related_names(self):
        self.assertEqual(self.usuario.recordatorios.count(), 1)
        self.assertEqual(self.curso.recordatorios.count(), 1)


class UsuarioFormTests(TestCase):
    def setUp(self):
        self.area = AreaCargo.objects.create(nombre='Tecnología')
        self.valid_data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'rut': '11111111-1',
            'rol': 'colaborador',
            'cargo': self.area.pk,
            'password': 'newpassword123'
        }

    def test_form_valid_data(self):
        form = UsuarioForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

    def test_form_required_fields(self):
        form = UsuarioForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('rut', form.errors)

    def test_form_save_with_password(self):
        form = UsuarioForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.check_password('newpassword123'))

    def test_form_save_without_password(self):
        data = self.valid_data.copy()
        data['password'] = ''
        form = UsuarioForm(data=data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")
        user = form.save()
        self.assertTrue(user.has_usable_password() or not user.password)

    def test_form_update_without_changing_password(self):
        user = Usuario.objects.create_user(
            username='existinguser',
            password='oldpassword',
            rut='22222222-2'
        )
        data = {
            'username': 'existinguser',
            'first_name': 'Updated',
            'last_name': 'User',
            'email': 'test@test.com',
            'rut': '22222222-2',
            'rol': 'colaborador',
        }
        form = UsuarioForm(data=data, instance=user)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")
        updated_user = form.save()
        self.assertTrue(updated_user.check_password('oldpassword'))


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            password='testpass123',
            rut='12345678-9'
        )

    def test_login_get_request(self):
        response = self.client.get(reverse('usuarios:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_valid_credentials(self):
        response = self.client.post(reverse('usuarios:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('usuarios:login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any('incorrectos' in str(m) for m in messages_list))


class LogoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            password='testpass123',
            rut='12345678-9'
        )

    def test_logout_redirects_to_login(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuarios:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('usuarios:login'), response.url)


class InicioViewTests(TestCase):
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

    def test_inicio_requires_login(self):
        response = self.client.get(reverse('usuarios:inicio'))
        self.assertEqual(response.status_code, 302)

    def test_inicio_admin_context(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('usuarios:inicio'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_usuarios', response.context)
        self.assertIn('total_cursos', response.context)

    def test_inicio_docente_context(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('usuarios:inicio'))
        self.assertEqual(response.status_code, 200)

    def test_inicio_colaborador_context(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('usuarios:inicio'))
        self.assertEqual(response.status_code, 200)


class UsuarioListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='22222222-2'
        )

    def test_usuario_list_requires_admin(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('usuarios:usuario_list'))
        self.assertEqual(response.status_code, 403)

    def test_usuario_list_accessible_by_admin(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('usuarios:usuario_list'))
        self.assertEqual(response.status_code, 200)


class UsuarioCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.area = AreaCargo.objects.create(nombre='Tecnología')

    def test_usuario_create_requires_admin(self):
        docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='22222222-2'
        )
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('usuarios:usuario_create'))
        self.assertEqual(response.status_code, 403)

    def test_usuario_create_get_form(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('usuarios:usuario_create'))
        self.assertEqual(response.status_code, 200)

    def test_usuario_create_post_valid(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.post(reverse('usuarios:usuario_create'), {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'rut': '44444444-4',
            'rol': 'colaborador',
            'password': 'newpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Usuario.objects.filter(username='newuser').exists())


class UsuarioEditViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.usuario = Usuario.objects.create_user(
            username='toedit', password='testpass', rut='22222222-2',
            first_name='Original', last_name='Name'
        )

    def test_usuario_edit_requires_admin(self):
        docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='33333333-3'
        )
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('usuarios:usuario_edit', kwargs={'pk': self.usuario.pk}))
        self.assertEqual(response.status_code, 403)

    def test_usuario_edit_get_form(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('usuarios:usuario_edit', kwargs={'pk': self.usuario.pk}))
        self.assertEqual(response.status_code, 200)

    def test_usuario_edit_post_valid(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.post(reverse('usuarios:usuario_edit', kwargs={'pk': self.usuario.pk}), {
            'username': 'toedit',
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@test.com',
            'rut': '22222222-2',
            'rol': 'colaborador'
        })
        self.assertEqual(response.status_code, 302)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.first_name, 'Updated')


class UsuarioDeleteViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.usuario = Usuario.objects.create_user(
            username='todelete', password='testpass', rut='22222222-2'
        )

    def test_usuario_delete_requires_admin(self):
        docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='33333333-3'
        )
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('usuarios:usuario_delete', kwargs={'pk': self.usuario.pk}))
        self.assertEqual(response.status_code, 403)

    def test_usuario_cannot_delete_self(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.post(reverse('usuarios:usuario_delete', kwargs={'pk': self.admin.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Usuario.objects.filter(pk=self.admin.pk).exists())

    def test_usuario_delete_other_user(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.post(reverse('usuarios:usuario_delete', kwargs={'pk': self.usuario.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Usuario.objects.filter(pk=self.usuario.pk).exists())


class InscribirCursoViewTests(TestCase):
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
            titulo='Test Curso',
            descripcion='Test',
            docente_creador=self.docente
        )

    def test_inscribir_curso_requires_admin(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('usuarios:inscribir_curso', kwargs={'curso_id': self.curso.pk}))
        self.assertEqual(response.status_code, 403)

    def test_inscribir_curso_get_form(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('usuarios:inscribir_curso', kwargs={'curso_id': self.curso.pk}))
        self.assertEqual(response.status_code, 200)

    def test_inscribir_curso_post_valid(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.post(reverse('usuarios:inscribir_curso', kwargs={'curso_id': self.curso.pk}), {
            'usuario_id': self.colaborador.pk
        })
        self.assertEqual(response.status_code, 302)
        from cursos.models import InscripcionCurso
        self.assertTrue(InscripcionCurso.objects.filter(usuario=self.colaborador, curso=self.curso).exists())


class InscribirCursoBulkViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='11111111-1'
        )
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='22222222-2'
        )
        self.colaborador1 = Usuario.objects.create_user(
            username='colab1', password='testpass', rol='colaborador', rut='33333333-3'
        )
        self.colaborador2 = Usuario.objects.create_user(
            username='colab2', password='testpass', rol='colaborador', rut='44444444-4'
        )
        self.curso = Curso.objects.create(
            titulo='Test Curso',
            descripcion='Test',
            docente_creador=self.docente
        )

    def test_inscribir_bulk_requires_admin(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('usuarios:inscribir_curso_bulk', kwargs={'curso_id': self.curso.pk}))
        self.assertEqual(response.status_code, 403)

    def test_inscribir_bulk_post_valid(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.post(reverse('usuarios:inscribir_curso_bulk', kwargs={'curso_id': self.curso.pk}), {
            'usuarios': [self.colaborador1.pk, self.colaborador2.pk]
        })
        self.assertEqual(response.status_code, 302)
        from cursos.models import InscripcionCurso
        self.assertEqual(InscripcionCurso.objects.filter(curso=self.curso).count(), 2)

    def test_inscribir_bulk_no_users_selected(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.post(reverse('usuarios:inscribir_curso_bulk', kwargs={'curso_id': self.curso.pk}), {
            'usuarios': []
        })
        self.assertEqual(response.status_code, 302)


class MisCursosViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin', password='testpass', rol='admin', rut='00000000-0'
        )
        self.docente = Usuario.objects.create_user(
            username='docente', password='testpass', rol='docente', rut='11111111-1'
        )
        self.colaborador = Usuario.objects.create_user(
            username='colaborador', password='testpass', rol='colaborador', rut='22222222-2'
        )
        self.curso = Curso.objects.create(
            titulo='Test Curso',
            descripcion='Test',
            docente_creador=self.docente
        )
        from cursos.models import InscripcionCurso
        InscripcionCurso.objects.create(
            usuario=self.colaborador,
            curso=self.curso,
            estado='asignado'
        )

    def test_mis_cursos_requires_login(self):
        response = self.client.get(reverse('usuarios:mis_cursos'))
        self.assertEqual(response.status_code, 302)

    def test_mis_cursos_docente_sees_own_courses(self):
        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('usuarios:mis_cursos'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['es_docente'])

    def test_mis_cursos_colaborador_sees_inscripciones(self):
        self.client.login(username='colaborador', password='testpass')
        response = self.client.get(reverse('usuarios:mis_cursos'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('inscripciones', response.context)

    def test_mis_cursos_admin_sees_all_cursos(self):
        """Admin should see all courses in mis_cursos"""
        self.client.login(username='admin', password='testpass')
        response = self.client.get(reverse('usuarios:mis_cursos'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['es_admin'])
        # Admin should see all cursos, not inscripciones
        self.assertIn('cursos', response.context)

    def test_mis_cursos_docente_only_sees_own(self):
        """Docente should only see courses they created"""
        # Create second docente with separate course
        docente2 = Usuario.objects.create_user(
            username='docente2', password='testpass',
            rol='docente', rut='99999999-9'
        )
        Curso.objects.create(titulo='Other Course', descripcion='...', estado='publicado', docente_creador=docente2)

        self.client.login(username='docente', password='testpass')
        response = self.client.get(reverse('usuarios:mis_cursos'))
        self.assertEqual(response.status_code, 200)
        # Should only see their own curso, not docente2's
        self.assertIn('cursos', response.context)
        cursos = response.context['cursos']
        self.assertEqual(cursos.count(), 1)
        self.assertEqual(cursos.first().docente_creador, self.docente)


class PerfilViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(
            username='testuser', password='testpass', rol='colaborador', rut='11111111-1'
        )

    def test_perfil_requires_login(self):
        response = self.client.get(reverse('usuarios:perfil'))
        self.assertEqual(response.status_code, 302)

    def test_perfil_get_context(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('usuarios:perfil'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('intentos', response.context)
        self.assertIn('certificados', response.context)
        self.assertIn('total_enrolled', response.context)


class PasswordChangeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(
            username='testuser', password='oldpassword', rut='11111111-1'
        )

    def test_password_change_requires_login(self):
        response = self.client.get(reverse('usuarios:password_change'))
        self.assertEqual(response.status_code, 302)

    def test_password_change_get_form(self):
        self.client.login(username='testuser', password='oldpassword')
        response = self.client.get(reverse('usuarios:password_change'))
        self.assertEqual(response.status_code, 200)

    def test_password_change_post_valid(self):
        self.client.login(username='testuser', password='oldpassword')
        response = self.client.post(reverse('usuarios:password_change'), {
            'old_password': 'oldpassword',
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('newpassword123'))

    def test_password_change_post_invalid(self):
        self.client.login(username='testuser', password='oldpassword')
        response = self.client.post(reverse('usuarios:password_change'), {
            'old_password': 'wrongpassword',
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, 200)
