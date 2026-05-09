"""Modelos del modulo administrativo."""

from django.conf import settings
from django.db import models


class ReporteUsuario(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        REVISADO = 'revisado', 'Revisado'
        DESCARTADO = 'descartado', 'Descartado'

    motivo = models.CharField(max_length=100)
    descripcion = models.TextField()
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=Estado.choices)
    usuario_reportante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reportes_hechos',
    )
    usuario_reportado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reportes_recibidos',
    )
    libro_reportado = models.ForeignKey(
        'Libro',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reportes_usuario',
    )
    activo = models.BooleanField(default=True)


class NotificacionUsuario(models.Model):
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones',
    )
    reporte_relacionado = models.ForeignKey(
        ReporteUsuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificaciones_generadas',
    )


class ConfiguracionContacto(models.Model):
    telefono = models.CharField(max_length=30, default='+57 300 0000000')
    whatsapp = models.CharField(max_length=30, default='+57 300 0000000')
    correo = models.EmailField(default='administracionlegajo@gmail.com')
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuracion de contacto'
        verbose_name_plural = 'Configuracion de contacto'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config
