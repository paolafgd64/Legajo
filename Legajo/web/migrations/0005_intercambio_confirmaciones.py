from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0004_notificacionusuario'),
    ]

    operations = [
        migrations.AddField(
            model_name='intercambio',
            name='confirmacion_receptor',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='intercambio',
            name='confirmacion_solicitante',
            field=models.BooleanField(default=False),
        ),
    ]
