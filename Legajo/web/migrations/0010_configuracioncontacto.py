from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0009_usuario_suspension_hasta'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionContacto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telefono', models.CharField(default='+57 300 0000000', max_length=30)),
                ('whatsapp', models.CharField(default='+57 300 0000000', max_length=30)),
                ('correo', models.EmailField(default='administracionlegajo@gmail.com', max_length=254)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Configuracion de contacto',
                'verbose_name_plural': 'Configuracion de contacto',
            },
        ),
    ]
