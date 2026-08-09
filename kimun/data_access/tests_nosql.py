from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from anuncios.repository import AnuncioRepository
from calendario.repository import CalendarioRepository
from certificados.repository import CertificadoRepository
from cursos.repository import (
    CategoriaRepository,
    ClaseRepository,
    CursoRepository,
    InscripcionRepository,
    MaterialRepository,
    ProgresoClaseRepository,
)
from evaluaciones.repository import (
    BancoPreguntasRepository,
    EvaluacionRepository,
    save_question_with_alternatives,
)
from kimun.data_access.dynamodb_client import DynamoDBClient
from reportes.repository import ReporteRepository
from tareas.repository import EntregaTareaRepository, TareaRepository
from usuarios.repository import UsuarioRepository
from usuarios.auth_backend import DynamoDBUser


class DynamoDBEnMemoria:
    """Implementación mínima para probar repositorios sin acceder a AWS."""

    def __init__(self):
        self.items = {}

    def put_item(self, item):
        self.items[(item["PK"], item["SK"])] = deepcopy(item)
        return item

    def get_item(self, pk, sk):
        item = self.items.get((pk, sk))
        return deepcopy(item) if item else None

    def delete_item(self, pk, sk):
        self.items.pop((pk, sk), None)
        return True

    def query_by_pk(self, pk, sk_prefix=None):
        return [
            deepcopy(item)
            for (item_pk, item_sk), item in self.items.items()
            if item_pk == pk and (not sk_prefix or item_sk.startswith(sk_prefix))
        ]

    def query_gsi1(self, gsi1pk, gsi1sk_prefix=None):
        return [
            deepcopy(item)
            for item in self.items.values()
            if item.get("GSI1PK") == gsi1pk
            and (
                not gsi1sk_prefix
                or str(item.get("GSI1SK", "")).startswith(gsi1sk_prefix)
            )
        ]

    def delete_partition(self, pk, sk_prefix=None):
        items = self.query_by_pk(pk, sk_prefix)
        for item in items:
            self.delete_item(item["PK"], item["SK"])
        return len(items)


class RepositoriosNoSQLTest(TestCase):
    def setUp(self):
        self.database = DynamoDBEnMemoria()
        self.patchers = [
            patch.object(DynamoDBClient, "put_item", self.database.put_item),
            patch.object(DynamoDBClient, "get_item", self.database.get_item),
            patch.object(DynamoDBClient, "delete_item", self.database.delete_item),
            patch.object(DynamoDBClient, "query_by_pk", self.database.query_by_pk),
            patch.object(DynamoDBClient, "query_gsi1", self.database.query_gsi1),
            patch.object(
                DynamoDBClient, "delete_partition", self.database.delete_partition
            ),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.docente = UsuarioRepository.create_user(
            "docente@kimun.cl",
            make_password("clave-segura"),
            rol="docente",
            nombre="Docente Kimün",
        )
        self.estudiante = UsuarioRepository.create_user(
            "estudiante@kimun.cl",
            make_password("clave-segura"),
            rol="colaborador",
            nombre="Estudiante Kimün",
        )
        self.categoria = CategoriaRepository.save(
            {"nombre": "Bases de datos", "color": "#6366f1"}, "datos"
        )
        self.curso = CursoRepository.create_course(
            {
                "titulo": "DynamoDB avanzado",
                "descripcion": "Curso de prueba",
                "docente_creador_id": self.docente["email"],
                "categoria_id": self.categoria["id"],
                "estado": "publicado",
                "fecha_limite": timezone.now() + timezone.timedelta(days=30),
            },
            "curso-prueba",
        )

    def test_flujo_academico_completo(self):
        inscripcion = InscripcionRepository.save(
            self.estudiante["email"], self.curso["id"], "en_progreso"
        )
        clase = ClaseRepository.save_class(
            {
                "curso_id": self.curso["id"],
                "titulo": "Modelado Single-Table",
                "contenido": "Contenido",
                "orden": 1,
            }
        )
        ProgresoClaseRepository.complete(self.estudiante["email"], clase)
        MaterialRepository.save_material(
            {
                "curso_id": self.curso["id"],
                "titulo": "Guía",
                "tipo": "pdf",
                "archivo": "materiales/guia.pdf",
                "url": "",
            }
        )

        evaluacion = EvaluacionRepository.save_evaluation(
            {
                "curso_id": self.curso["id"],
                "titulo": "Evaluación final",
                "porcentaje_aprobacion": 60,
                "max_intentos": 2,
                "creado_por_id": self.docente["email"],
            },
            "evaluacion-prueba",
        )
        pregunta = save_question_with_alternatives(
            {
                "evaluacion_id": evaluacion["id"],
                "texto": "¿Qué clave agrupa una partición?",
            },
            [
                {"texto": "PK", "es_correcta": True},
                {"texto": "TTL", "es_correcta": False},
            ],
        )
        intento = EvaluacionRepository.guardar_intento(
            self.estudiante["email"],
            evaluacion["id"],
            100,
            True,
            {pregunta["id"]: pregunta["alternativas"][0]["id"]},
        )

        tarea = TareaRepository.save_task(
            {
                "curso_id": self.curso["id"],
                "titulo": "Diseño de claves",
                "descripcion": "Entregar propuesta",
                "fecha_limite": timezone.now() + timezone.timedelta(days=7),
                "creado_por_id": self.docente["email"],
            }
        )
        entrega = EntregaTareaRepository.save(
            {
                "tarea_id": tarea["id"],
                "estudiante_id": self.estudiante["email"],
                "comentario": "Trabajo final",
                "archivo": "entregas/trabajo.pdf",
            }
        )
        certificado, creado = CertificadoRepository.create(
            self.estudiante["email"], self.curso["id"], "aprobado"
        )

        self.assertEqual(inscripcion["curso"]["id"], self.curso["id"])
        self.assertEqual(len(EvaluacionRepository.get_evaluation(evaluacion["id"])["preguntas"]), 1)
        self.assertTrue(intento["aprobado"])
        self.assertEqual(entrega["tarea"]["id"], tarea["id"])
        self.assertTrue(creado)
        self.assertEqual(certificado["estado"], "aprobado")

    def test_calendario_anuncios_bancos_y_reportes(self):
        InscripcionRepository.save(self.estudiante["email"], self.curso["id"])
        CalendarioRepository.sync_course(self.curso)
        anuncio = AnuncioRepository.save(
            {
                "titulo": "Recordatorio",
                "contenido": "Revisar el material",
                "publicado": True,
                "fecha_publicacion": timezone.now(),
                "fecha_expiracion": timezone.now() + timezone.timedelta(days=2),
                "curso_id": self.curso["id"],
                "creado_por_id": self.docente["email"],
                "prioridad": "aviso",
            },
            "anuncio-prueba",
        )
        CalendarioRepository.sync_announcement(anuncio)
        banco = BancoPreguntasRepository.save(
            {
                "nombre": "Banco general",
                "descripcion": "Preguntas compartidas",
                "creado_por_id": self.docente["email"],
                "es_publico": True,
            },
            "banco-prueba",
        )
        save_question_with_alternatives(
            {"banco_id": banco["id"], "texto": "Pregunta del banco"},
            [{"texto": "Respuesta", "es_correcta": True}],
        )

        eventos = CalendarioRepository.list_events()
        visibles = AnuncioRepository.list_visible(
            self.estudiante["email"], "colaborador", [self.curso["id"]]
        )
        resumen = ReporteRepository.dashboard()
        BancoPreguntasRepository.delete_bank(banco["id"])

        self.assertGreaterEqual(len(eventos), 2)
        self.assertEqual(visibles[0]["id"], anuncio["id"])
        self.assertEqual(resumen["total_usuarios"], 2)
        self.assertEqual(resumen["total_cursos"], 1)
        self.assertIsNone(BancoPreguntasRepository.get_bank(banco["id"]))

    def test_rutas_aceptan_identificadores_dynamodb(self):
        identifier = "0f7d8e9a-dynamodb-id"
        self.assertIn(identifier, reverse("cursos:curso_detail", args=[identifier]))
        self.assertIn(identifier, reverse("tareas:tarea_detail", args=[identifier]))
        self.assertIn(
            identifier, reverse("evaluaciones:evaluacion_edit", args=[identifier])
        )

    def test_navegacion_principal_sin_base_relacional(self):
        InscripcionRepository.save(
            self.estudiante["email"], self.curso["id"], "en_progreso"
        )
        client = Client()
        client.force_login(
            DynamoDBUser(self.estudiante),
            backend="usuarios.auth_backend.DynamoDBAuthBackend",
        )
        urls = [
            reverse("inicio"),
            reverse("usuarios:mis_cursos"),
            reverse("cursos:curso_list"),
            reverse("cursos:curso_detail", args=[self.curso["id"]]),
            reverse("tareas:tarea_list", args=[self.curso["id"]]),
            reverse("evaluaciones:evaluacion_list", args=[self.curso["id"]]),
            reverse("calendario:calendario"),
            reverse("anuncios:anuncio_list"),
            reverse("certificados:mis_certificados"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_inicio_de_sesion_con_correo_en_dynamodb(self):
        client = Client()
        response = client.post(
            reverse("usuarios:login"),
            {"username": self.estudiante["email"], "password": "clave-segura"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("inicio"))
        self.assertEqual(client.get(reverse("usuarios:perfil")).status_code, 200)

    def test_navegacion_administrativa_y_de_gestion(self):
        admin = UsuarioRepository.create_user(
            "admin@kimun.cl",
            make_password("clave-segura"),
            rol="admin",
            nombre="Administración Kimün",
        )
        clase = ClaseRepository.save_class(
            {
                "curso_id": self.curso["id"],
                "titulo": "Clase administrativa",
                "contenido": "Contenido",
                "orden": 1,
            }
        )
        tarea = TareaRepository.save_task(
            {
                "curso_id": self.curso["id"],
                "titulo": "Tarea administrativa",
                "descripcion": "Descripción",
                "fecha_limite": timezone.now() + timezone.timedelta(days=3),
                "creado_por_id": self.docente["email"],
            }
        )
        evaluacion = EvaluacionRepository.save_evaluation(
            {
                "curso_id": self.curso["id"],
                "titulo": "Evaluación administrativa",
                "porcentaje_aprobacion": 60,
                "max_intentos": 1,
                "creado_por_id": self.docente["email"],
            }
        )
        banco = BancoPreguntasRepository.save(
            {
                "nombre": "Banco administrativo",
                "descripcion": "Descripción",
                "creado_por_id": self.docente["email"],
                "es_publico": True,
            }
        )
        anuncio = AnuncioRepository.save(
            {
                "titulo": "Anuncio administrativo",
                "contenido": "Contenido",
                "publicado": True,
                "curso_id": self.curso["id"],
                "creado_por_id": self.docente["email"],
                "prioridad": "info",
            }
        )
        evento = CalendarioRepository.save(
            {
                "titulo": "Evento administrativo",
                "descripcion": "Descripción",
                "tipo": "evento_general",
                "fecha_inicio": timezone.now(),
                "fecha_fin": timezone.now() + timezone.timedelta(hours=1),
                "curso_id": self.curso["id"],
                "creado_por_id": self.docente["email"],
                "color": "#6366f1",
            }
        )

        client = Client()
        client.force_login(
            DynamoDBUser(admin), backend="usuarios.auth_backend.DynamoDBAuthBackend"
        )
        urls = [
            reverse("usuarios:usuario_list"),
            reverse("usuarios:usuario_create"),
            reverse("cursos:curso_create"),
            reverse("cursos:curso_edit", args=[self.curso["id"]]),
            reverse("cursos:categoria_list"),
            reverse("cursos:categoria_create"),
            reverse("cursos:material_create", args=[self.curso["id"]]),
            reverse("cursos:clase_list", args=[self.curso["id"]]),
            reverse("cursos:clase_detail", args=[clase["id"]]),
            reverse("cursos:clase_create", args=[self.curso["id"]]),
            reverse("tareas:tarea_detail", args=[tarea["id"]]),
            reverse("tareas:tarea_create", args=[self.curso["id"]]),
            reverse("tareas:tarea_edit", args=[tarea["id"]]),
            reverse("evaluaciones:evaluacion_create", args=[self.curso["id"]]),
            reverse("evaluaciones:evaluacion_edit", args=[evaluacion["id"]]),
            reverse("evaluaciones:banco_list"),
            reverse("evaluaciones:banco_detail", args=[banco["id"]]),
            reverse("evaluaciones:banco_create"),
            reverse("anuncios:anuncio_detail", args=[anuncio["id"]]),
            reverse("anuncios:anuncio_create"),
            reverse("anuncios:anuncio_edit", args=[anuncio["id"]]),
            reverse("calendario:evento_create"),
            reverse("calendario:evento_edit", args=[evento["id"]]),
            reverse("certificados:certificado_list"),
            reverse("certificados:certificados_pendientes"),
            reverse("reportes:dashboard_reportes"),
            reverse("reportes:reporte_curso", args=[self.curso["id"]]),
            reverse("reportes:reporte_usuario", args=[self.estudiante["email"]]),
            reverse("reportes:progreso_heatmap"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, 200)
