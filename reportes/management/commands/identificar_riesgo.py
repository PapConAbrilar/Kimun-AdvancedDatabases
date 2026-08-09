from django.core.management.base import BaseCommand

from reportes.views import get_at_risk_students


class Command(BaseCommand):
    help = "Identifica estudiantes en riesgo utilizando datos de DynamoDB"

    def handle(self, *args, **options):
        estudiantes = get_at_risk_students()
        if not estudiantes:
            self.stdout.write("No se encontraron estudiantes en riesgo.")
            return

        self.stdout.write(f"Se encontraron {len(estudiantes)} estudiantes en riesgo:")
        for item in estudiantes:
            usuario = item["usuario"]
            self.stdout.write(f"  - {usuario['nombre']} ({usuario['email']})")
            self.stdout.write(f"    Estado: {item['estado']}")
            self.stdout.write(f"    Razón: {item['riesgo']}")
