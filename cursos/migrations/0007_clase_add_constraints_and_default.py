import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cursos', '0006_normalize_clase_orden_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clase',
            name='orden',
            field=models.PositiveIntegerField(default=1, help_text='Orden de la clase en el curso'),
        ),
        migrations.AddConstraint(
            model_name='clase',
            constraint=models.UniqueConstraint(
                fields=('curso', 'orden'),
                name='clase_curso_orden_uniq'
            ),
        ),
        migrations.AddConstraint(
            model_name='clase',
            constraint=models.CheckConstraint(
                condition=models.Q(orden__gte=1),
                name='clase_orden_minimo'
            ),
        ),
    ]
