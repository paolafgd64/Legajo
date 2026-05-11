"""Modelos del dominio de intercambios entre usuarios."""

from django.conf import settings
from django.db import models

from ..gestion_libros.models import Libro


class Intercambio(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        ACEPTADO = 'aceptado', 'Aceptado'
        RECHAZADO = 'rechazado', 'Rechazado'
        CANCELADO = 'cancelado', 'Cancelado'
        COMPLETADO = 'completado', 'Completado'

    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    pin_validacion = models.CharField(max_length=6, null=True, blank=True)
    confirmacion_solicitante = models.BooleanField(default=False)
    confirmacion_receptor = models.BooleanField(default=False)
    notificacion_leida = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=Estado.choices)
    usuario_solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='solicitudes',
    )
    usuario_receptor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recepciones',
    )
    cancelado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intercambios_cancelados',
    )
    libro_solicitado = models.ForeignKey(
        Libro,
        on_delete=models.SET_NULL,
        null=True,
        related_name='solicitudes_recibidas',
    )
    libro_cambio = models.ForeignKey(
        Libro,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ofrecidos_en_intercambio',
    )
    activo = models.BooleanField(default=True)
