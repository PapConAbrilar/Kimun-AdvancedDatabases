"""Management command: exporta datos a S3 y ejecuta KPIs en Athena."""

from django.core.management.base import BaseCommand

from bigdata.export_to_s3 import export_to_s3
from bigdata.kpi_cache import guardar_cache, obtener_kpis


class Command(BaseCommand):
    help = "Exporta los datos de DynamoDB a S3 y ejecuta los KPIs de Athena."

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-export",
            action="store_true",
            help="Solo exporta a S3 sin ejecutar KPIs.",
        )
        parser.add_argument(
            "--solo-kpis",
            action="store_true",
            help="Solo ejecuta KPIs (asume que ya hay datos en S3).",
        )
        parser.add_argument(
            "--bucket",
            default=None,
            help="Nombre del bucket S3 de analytics.",
        )
        parser.add_argument(
            "--region",
            default=None,
            help="Región AWS (default: us-east-1).",
        )

    def handle(self, *args, **options):
        if not options["solo_kpis"]:
            self.stdout.write(self.style.SUCCESS("▶ Fase 1: Exportando DynamoDB → S3"))
            counts = export_to_s3(
                bucket=options.get("bucket"),
                region=options.get("region"),
            )
            total = sum(counts.values())
            self.stdout.write(
                self.style.SUCCESS(
                    f"✔ Exportación completada: {total} items en {len(counts)} tipos"
                )
            )

        if not options["solo_export"]:
            self.stdout.write(self.style.SUCCESS("▶ Fase 2: Ejecutando KPIs via Athena"))
            try:
                kpis = obtener_kpis(forzar_athena=True)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✔ KPIs ejecutados y cacheados ({len(kpis.get('kpis', {}))} consultas)"
                    )
                )
            except Exception as exc:
                self.stderr.write(
                    self.style.WARNING(
                        f"⚠ No se pudieron ejecutar los KPIs vía Athena: {exc}\n"
                        f"  El dashboard usará datos simulados."
                    )
                )
                kpis = obtener_kpis(forzar_athena=False)

        self.stdout.write(self.style.SUCCESS("✔ Pipeline Big Data completado."))
