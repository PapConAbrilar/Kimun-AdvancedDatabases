from django.db import IntegrityError
from django.test import TestCase

from anuncios.models import Anuncio, LecturaAnuncio
from cursos.models import Curso
from usuarios.models import Usuario


class AnuncioModelTest(TestCase):
    def setUp(self):
        self.user = Usuario._default_manager.create_user(username='docente', rut='11111111-1', password='pass12345')

    def test_anuncio_creation_and_str(self):
        anuncio = Anuncio._default_manager.create(
            titulo='Aviso importante',
            contenido='Contenido del anuncio',
            creado_por=self.user,
        )

        self.assertEqual(str(anuncio), 'Aviso importante')
        self.assertEqual(anuncio.prioridad, 'info')


class LecturaAnuncioModelTest(TestCase):
    def setUp(self):
        self.user = Usuario._default_manager.create_user(username='estudiante', rut='22222222-2', password='pass12345')
        self.docente = Usuario._default_manager.create_user(username='docente2', rut='33333333-3', password='pass12345')
        self.curso = Curso._default_manager.create(
            titulo='Curso demo',
            descripcion='Descripción',
            docente_creador=self.docente,
        )
        self.anuncio = Anuncio._default_manager.create(
            titulo='Anuncio demo',
            contenido='Contenido',
            curso=self.curso,
            creado_por=self.docente,
        )

    def test_lectura_anuncio_creation_and_str(self):
        lectura = LecturaAnuncio._default_manager.create(anuncio=self.anuncio, usuario=self.user)

        self.assertEqual(str(lectura), f'{self.user} - {self.anuncio}')

    def test_unique_together(self):
        LecturaAnuncio._default_manager.create(anuncio=self.anuncio, usuario=self.user)

        with self.assertRaises(IntegrityError):
            LecturaAnuncio._default_manager.create(anuncio=self.anuncio, usuario=self.user)
