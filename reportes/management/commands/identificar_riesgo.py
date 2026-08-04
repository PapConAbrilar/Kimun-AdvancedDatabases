from django.core.management.base import BaseCommand
from reportes.views import get_at_risk_students


class Command(BaseCommand):
    help = 'Identify at-risk students'

    def handle(self, *args, **options):
        at_risk = get_at_risk_students()

        if not at_risk:
            self.stdout.write('No students at risk found.')
            return

        self.stdout.write(f'Found {len(at_risk)} at-risk students:')
        for item in at_risk:
            self.stdout.write(f"  - {item['usuario'].get_full_name()} ({item['usuario'].username})")
            self.stdout.write(f"    Curso: {item['curso'].titulo}")
            self.stdout.write(f"    Razón: {item['razon']}")
