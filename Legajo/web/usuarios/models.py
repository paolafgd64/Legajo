"""Modelos del dominio de usuarios y autenticacion."""

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('El correo electronico es obligatorio')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', Usuario.Rol.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    # El correo reemplaza al username como identificador de login.
    username = None

    nombre1 = models.CharField(max_length=30)
    nombre2 = models.CharField(max_length=30, blank=True, null=True)
    apellido1 = models.CharField(max_length=30)
    apellido2 = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(unique=True)
    direccion = models.CharField(max_length=50)
    ciudad = models.CharField(max_length=20)
    telefono = models.BigIntegerField()

    class Rol(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        USUARIO = 'usuario', 'Usuario'

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.USUARIO,
    )
    activo = models.BooleanField(default=True)
    motivo_desactivacion = models.TextField(blank=True, default='')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    def delete(self, *args, **kwargs):
        self.activo = False
        self.is_active = False
        if not self.motivo_desactivacion:
            self.motivo_desactivacion = 'Cuenta desactivada por administracion.'
        self.save()

    def __str__(self):
        return f"{self.nombre1} {self.apellido1}"
