from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0008_libro_fechas_actividad'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='suspension_hasta',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
