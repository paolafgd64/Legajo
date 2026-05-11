from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0011_intercambio_notificacion_leida'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intercambio',
            name='estado',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('aceptado', 'Aceptado'),
                    ('rechazado', 'Rechazado'),
                    ('cancelado', 'Cancelado'),
                    ('completado', 'Completado'),
                ],
                max_length=20,
            ),
        ),
    ]
