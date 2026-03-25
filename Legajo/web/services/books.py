import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import DatabaseError, transaction
from django.db.models import Q

from ..models import Autor, Genero, Libro, Usuario
from ..validators import (
    DatabaseServiceError,
    NotFoundServiceError,
    PermissionDeniedServiceError,
    validate_book_payload,
)
from .serialization import serialize_book


def _split_author_name(author_name):
    author_name = (author_name or '').strip()
    if not author_name:
        return '', None, '', None

    parts = [part for part in author_name.split() if part]
    if len(parts) == 1:
        return parts[0], None, '', None
    if len(parts) == 2:
        return parts[0], None, parts[1], None
    if len(parts) == 3:
        return parts[0], parts[1], parts[2], None

    return parts[0], parts[1], parts[2], ' '.join(parts[3:])


def _get_or_create_author(author_name):
    nombre1, nombre2, apellido1, apellido2 = _split_author_name(author_name)
    autor, _ = Autor.objects.get_or_create(
        nombre1=nombre1,
        nombre2=nombre2,
        apellido1=apellido1,
        apellido2=apellido2,
        defaults={'apodo': None},
    )
    return autor


def _save_uploaded_image(uploaded_file):
    extension = os.path.splitext(uploaded_file.name)[1] or '.jpg'
    filename = f"libros/{uuid.uuid4()}{extension}"
    saved_path = default_storage.save(filename, uploaded_file)
    return f"{settings.MEDIA_URL}{saved_path}".replace('\\', '/')


def _books_queryset():
    return Libro.objects.filter(activo=True).select_related('usuario_propietario').prefetch_related('autores', 'generos')


def _get_book_for_user(user, libro_id):
    try:
        libro = _books_queryset().get(id=libro_id)
    except Libro.DoesNotExist as exc:
        raise NotFoundServiceError('Libro no encontrado.') from exc
    except DatabaseError as exc:
        raise DatabaseServiceError() from exc

    if libro.usuario_propietario_id != user.id and user.rol != Usuario.Rol.ADMIN:
        raise PermissionDeniedServiceError('No tienes permiso para este libro.')

    return libro


def list_books(user, filters):
    try:
        libros = _books_queryset()
        if user.rol != Usuario.Rol.ADMIN:
            libros = libros.filter(usuario_propietario=user)

        titulo = (filters.get('titulo') or '').strip()
        autor = (filters.get('autor') or '').strip()
        usuario = (filters.get('usuario') or '').strip()
        genero = (filters.get('genero') or '').strip()
        estado = (filters.get('estado') or '').strip()

        if titulo:
            libros = libros.filter(titulo__icontains=titulo)
        if autor:
            libros = libros.filter(
                Q(autores__nombre1__icontains=autor) |
                Q(autores__nombre2__icontains=autor) |
                Q(autores__apellido1__icontains=autor) |
                Q(autores__apellido2__icontains=autor) |
                Q(autores__apodo__icontains=autor)
            )
        if usuario:
            libros = libros.filter(
                Q(usuario_propietario__nombre1__icontains=usuario) |
                Q(usuario_propietario__nombre2__icontains=usuario) |
                Q(usuario_propietario__apellido1__icontains=usuario) |
                Q(usuario_propietario__apellido2__icontains=usuario) |
                Q(usuario_propietario__email__icontains=usuario)
            )
        if genero:
            libros = libros.filter(generos__nombre__icontains=genero)
        if estado:
            libros = libros.filter(estado__iexact=estado)

        return [serialize_book(libro) for libro in libros.order_by('-id').distinct()]
    except DatabaseError as exc:
        raise DatabaseServiceError() from exc


def list_recommended_books(user):
    try:
        libros = (
            _books_queryset()
            .exclude(usuario_propietario=user)
            .exclude(usuario_propietario__isnull=True)
            .order_by('-id')
        )
        return [serialize_book(libro) for libro in libros]
    except DatabaseError as exc:
        raise DatabaseServiceError() from exc


def get_book_detail(user, libro_id):
    libro = _get_book_for_user(user, libro_id)
    return serialize_book(libro)


def create_book(user, data, image_file=None):
    payload = validate_book_payload(data)
    url_imagen = payload['url_imagen'] or '/static/web/imgs/libro_de_la_selva.jpg'
    if image_file:
        url_imagen = _save_uploaded_image(image_file)

    try:
        with transaction.atomic():
            libro = Libro.objects.create(
                titulo=payload['titulo'],
                sinopsis=payload['sinopsis'],
                estado=payload['estado'],
                url_imagen=url_imagen,
                usuario_propietario=user,
            )
            autor = _get_or_create_author(payload['autor'])
            genero, _ = Genero.objects.get_or_create(nombre=payload['genero'].title())
            libro.autores.add(autor)
            libro.generos.add(genero)
    except DatabaseError as exc:
        raise DatabaseServiceError() from exc

    return serialize_book(libro)


def update_book(user, libro_id, data):
    payload = validate_book_payload(data)
    libro = _get_book_for_user(user, libro_id)

    try:
        with transaction.atomic():
            libro.titulo = payload['titulo']
            libro.sinopsis = payload['sinopsis']
            libro.estado = payload['estado']
            if payload['url_imagen']:
                libro.url_imagen = payload['url_imagen']
            libro.save(update_fields=['titulo', 'sinopsis', 'estado', 'url_imagen'])

            autor = _get_or_create_author(payload['autor'])
            genero, _ = Genero.objects.get_or_create(nombre=payload['genero'].title())
            libro.autores.set([autor])
            libro.generos.set([genero])
    except DatabaseError as exc:
        raise DatabaseServiceError() from exc

    libro.refresh_from_db()
    return serialize_book(_books_queryset().get(id=libro.id))


def soft_delete_book(user, libro_id):
    libro = _get_book_for_user(user, libro_id)

    try:
        libro.activo = False
        libro.save(update_fields=['activo'])
    except DatabaseError as exc:
        raise DatabaseServiceError() from exc
