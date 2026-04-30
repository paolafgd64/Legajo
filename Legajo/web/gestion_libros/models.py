"""Modelos del dominio de libros."""

from django.conf import settings
from django.db import models


class Libro(models.Model):
    class Estado(models.TextChoices):
        PUBLICADO = 'Publicado', 'Publicado'
        LEYENDO = 'Leyendo', 'Leyendo'

    titulo = models.CharField(max_length=100)
    sinopsis = models.TextField()
    estado = models.CharField(max_length=20, choices=Estado.choices)
    url_imagen = models.CharField(max_length=255)
    usuario_propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    autores = models.ManyToManyField('Autor')
    generos = models.ManyToManyField('Genero')
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo


class Genero(models.Model):
    nombre = models.CharField(max_length=45)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Autor(models.Model):
    nombre1 = models.CharField(max_length=30)
    nombre2 = models.CharField(max_length=30, null=True, blank=True)
    apellido1 = models.CharField(max_length=30)
    apellido2 = models.CharField(max_length=30, null=True, blank=True)
    apodo = models.CharField(max_length=50, null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre1} {self.apellido1}"


class CalificacionLibro(models.Model):
    calificacion = models.IntegerField()
    comentario = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    libro = models.ForeignKey(
        Libro,
        on_delete=models.CASCADE,
    )
    activo = models.BooleanField(default=True)
