# Data migration: normalize orden values before adding constraints
from django.db import migrations


def normalize_clase_orden(apps, schema_editor):
    Clase = apps.get_model('cursos', 'Clase')
    for curso_id in Clase.objects.values_list('curso_id', flat=True).distinct():
        clases = Clase.objects.filter(curso_id=curso_id).order_by('orden', 'pk')
        for new_orden, clase in enumerate(clases, start=1):
            if clase.orden != new_orden:
                clase.orden = new_orden
                clase.save(update_fields=['orden'])


def reverse_normalize(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cursos', '0005_clase_clasecompletado'),
    ]

    operations = [
        migrations.RunPython(normalize_clase_orden, reverse_normalize),
    ]
