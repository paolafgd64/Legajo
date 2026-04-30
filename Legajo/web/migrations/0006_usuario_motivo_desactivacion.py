# Generated manually for admin user deactivation reasons.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0005_intercambio_confirmaciones'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='motivo_desactivacion',
            field=models.TextField(blank=True, default=''),
        ),
    ]
