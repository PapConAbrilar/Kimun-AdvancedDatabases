#!/usr/bin/env python
"""
Management command to clear database and setup initial cargos.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from usuarios.models import Usuario, AreaCargo
from cursos.models import Curso, Categoria, Material, Clase
from evaluaciones.models import Evaluacion, BancoPreguntas, Pregunta, Alternativa
from tareas.models import Tarea, EntregaTarea
from certificados.models import Certificado
from calendario.models import EventoCalendario
from anuncios.models import Anuncio


class Command(BaseCommand):
    help = 'Clear database keeping only admin user and create initial cargos'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write('Starting database cleanup...')
            
            try:
                admin = Usuario.objects.get(rol='admin')
                admin_id = admin.id
                self.stdout.write(f'Found admin user: {admin.username}')
            except Usuario.DoesNotExist:
                self.stdout.write(self.style.ERROR('No admin user found! Please create one first.'))
                return
            except Usuario.MultipleObjectsReturned:
                admin = Usuario.objects.filter(rol='admin').first()
                admin_id = admin.id
                self.stdout.write(f'Found admin user: {admin.username}')
            self.stdout.write('Deleting recordatorios...')
            from usuarios.models import Recordatorio
            Recordatorio.objects.all().delete()
            
            self.stdout.write('Deleting certificados...')
            Certificado.objects.all().delete()
            
            self.stdout.write('Deleting entregas...')
            EntregaTarea.objects.all().delete()
            
            self.stdout.write('Deleting tareas...')
            Tarea.objects.all().delete()
            
            self.stdout.write('Deleting evaluaciones...')
            Evaluacion.objects.all().delete()
            
            self.stdout.write('Deleting preguntas and alternativas...')
            Alternativa.objects.all().delete()
            Pregunta.objects.all().delete()
            
            self.stdout.write('Deleting bancos de preguntas...')
            BancoPreguntas.objects.all().delete()
            
            self.stdout.write('Deleting materiales and clases...')
            Material.objects.all().delete()
            Clase.objects.all().delete()
            
            self.stdout.write('Deleting inscripciones...')
            from cursos.models import InscripcionCurso
            InscripcionCurso.objects.all().delete()
            
            self.stdout.write('Deleting cursos...')
            Curso.objects.all().delete()
            
            self.stdout.write('Deleting categorias...')
            Categoria.objects.all().delete()
            
            self.stdout.write('Deleting eventos de calendario...')
            EventoCalendario.objects.all().delete()
            
            self.stdout.write('Deleting anuncios...')
            Anuncio.objects.all().delete()
            
            self.stdout.write('Deleting non-admin users...')
            Usuario.objects.exclude(id=admin_id).delete()
            
            self.stdout.write('Deleting existing cargos...')
            AreaCargo.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS('Database cleared successfully!'))
            
            self.stdout.write('Creating cargos...')
            
            colaborador_cargos = [
                'Profesional de Atención Directa',
                'Técnico de Atención Directa',
                'Asistente de Trato Directo',
                'Auxiliares de Servicio',
                'Manipuladores de Alimento',
            ]
            
            admin_cargos = [
                'Administración y Apoyo',
                'Directivos',
            ]
            
            docente_cargos = [
                'Docente Interno',
                'Docente Externo',
            ]
            
            all_cargos = colaborador_cargos + admin_cargos + docente_cargos
            
            for cargo_nombre in all_cargos:
                AreaCargo.objects.create(nombre=cargo_nombre)
                self.stdout.write(f'  Created: {cargo_nombre}')
            
            self.stdout.write(self.style.SUCCESS(f'\nCreated {len(all_cargos)} cargos successfully!'))
            self.stdout.write(self.style.SUCCESS('\nSummary:'))
            self.stdout.write(f'  - Colaborador cargos: {len(colaborador_cargos)}')
            self.stdout.write(f'  - Administrador cargos: {len(admin_cargos)}')
            self.stdout.write(f'  - Docente cargos: {len(docente_cargos)}')
            self.stdout.write(f'\nAdmin user preserved: {admin.username}')
