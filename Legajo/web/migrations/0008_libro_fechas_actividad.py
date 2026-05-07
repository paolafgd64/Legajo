from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0007_reporteusuario_libro_reportado'),
    ]

    operations = [
        migrations.AddField(
            model_name='libro',
            name='fecha_creacion',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='libro',
            name='fecha_actualizacion',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='libro',
            name='fecha_creacion',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='libro',
            name='fecha_actualizacion',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
