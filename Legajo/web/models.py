from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager

# Create your models here.


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
        blank=True
    )

    autores = models.ManyToManyField('Autor')
    generos = models.ManyToManyField('Genero')

    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo

class Usuario(AbstractUser):

    # 🔹 Sobrescribimos username si quieres usar correo
    username = None

    # 🔹 Nombres y apellidos 
    nombre1 = models.CharField(max_length=30)
    nombre2 = models.CharField(max_length=30, blank=True, null=True)

    apellido1 = models.CharField(max_length=30)
    apellido2 = models.CharField(max_length=30, blank=True, null=True)

    # 🔹 Email (único)
    email = models.EmailField(unique=True)

    # 🔹 Datos adicionales
    direccion = models.CharField(max_length=50)
    ciudad = models.CharField(max_length=20)
    telefono = models.BigIntegerField()

    class Rol(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        USUARIO = 'usuario', 'Usuario'

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.USUARIO
    )

    # 🔹 Soft delete
    activo = models.BooleanField(default=True)

    # 🔥 CLAVES IMPORTANTES
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # ya no pedimos username
    objects = UsuarioManager()

    def delete(self, *args, **kwargs):
        self.activo = False
        self.is_active = False  # importante para login
        self.save()

    def __str__(self):
        return f"{self.nombre1} {self.apellido1}"

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
        null=True
    )

    libro = models.ForeignKey(
        Libro,
        on_delete=models.CASCADE
    )

    activo = models.BooleanField(default=True)

class Intercambio(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        ACEPTADO = 'aceptado', 'Aceptado'
        RECHAZADO = 'rechazado', 'Rechazado'
        COMPLETADO = 'completado', 'Completado'

    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    pin_validacion = models.CharField(max_length=6, null=True, blank=True)
    confirmacion_solicitante = models.BooleanField(default=False)
    confirmacion_receptor = models.BooleanField(default=False)

    estado = models.CharField(max_length=20, choices=Estado.choices)

    usuario_solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='solicitudes'
    )

    usuario_receptor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recepciones'
    )

    libro_solicitado = models.ForeignKey(
        Libro,
        on_delete=models.SET_NULL,
        null=True,
        related_name='solicitudes_recibidas'
    )

    libro_cambio = models.ForeignKey(
        Libro,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ofrecidos_en_intercambio'
    )

    activo = models.BooleanField(default=True)

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
        related_name='reportes_hechos'
    )

    usuario_reportado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reportes_recibidos'
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
        related_name='notificaciones'
    )

    reporte_relacionado = models.ForeignKey(
        ReporteUsuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificaciones_generadas'
    )
