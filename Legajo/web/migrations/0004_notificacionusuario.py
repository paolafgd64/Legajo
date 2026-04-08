from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0003_intercambio_pin_validacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificacionUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('mensaje', models.TextField()),
                ('leida', models.BooleanField(default=False)),
                ('activo', models.BooleanField(default=True)),
                ('reporte_relacionado', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notificaciones_generadas', to='web.reporteusuario')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
