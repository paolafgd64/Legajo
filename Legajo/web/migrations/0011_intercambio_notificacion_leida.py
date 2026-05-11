from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0010_configuracioncontacto'),
    ]

    operations = [
        migrations.AddField(
            model_name='intercambio',
            name='notificacion_leida',
            field=models.BooleanField(default=False),
        ),
    ]
