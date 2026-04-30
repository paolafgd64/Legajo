# Generated manually to link user reports with the reported book.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0006_usuario_motivo_desactivacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporteusuario',
            name='libro_reportado',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reportes_usuario',
                to='web.libro',
            ),
        ),
    ]
