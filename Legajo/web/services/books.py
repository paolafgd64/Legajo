"""Servicios de negocio para libros.

Las views delegan aqui validaciones, consultas y operaciones de escritura para
mantener los endpoints mas pequeños y faciles de entender.
"""

from django.db import DatabaseError, transaction
from django.db.models import Avg, Count, Q

from ..models import Autor, Genero, Libro, Usuario
from ..validators import (
    DatabaseServiceError,
    ExternalServiceError,
    NotFoundServiceError,
    PermissionDeniedServiceError,
    ValidationServiceError,
    validate_book_payload,
)
from .cloudinary import is_cloudinary_configured, upload_image_to_cloudinary
from .serialization import serialize_book


def _extract_books_payload(payload):
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ('libros', 'books', 'items', 'data', 'resultado'):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return candidate

    raise ValidationServiceError('El archivo JSON debe contener una lista de libros.')


# Normaliza nombre completo de autor a la estructura del modelo (nombre/apellido separados).
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


# Busca autor existente por combinacion de nombres o lo crea si no existe.
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


# Guarda imagen en Cloudinary si esta configurado; si no, usa almacenamiento local.
def _save_uploaded_image(uploaded_file):
    if not is_cloudinary_configured():
        raise ValidationServiceError(
            'Cloudinary no esta configurado. Agrega tus credenciales en el archivo .env para subir imagenes.'
        )

    try:
        return upload_image_to_cloudinary(uploaded_file)
    except ExternalServiceError:
        raise


# Queryset base reutilizable para mantener consistencia en listados de libros activos.
def _books_queryset():
    return (
        Libro.objects.filter(activo=True)
        .select_related('usuario_propietario')
        .prefetch_related('autores', 'generos')
        .annotate(
            promedio_calificacion=Avg(
                'calificacionlibro__calificacion',
                filter=Q(calificacionlibro__activo=True),
                distinct=True,
            ),
            total_calificaciones=Count(
                'calificacionlibro',
                filter=Q(calificacionlibro__activo=True),
                distinct=True,
            ),
        )
    )


# Obtiene libro y valida permisos (propietario o admin).
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


# Lista libros aplicando filtros de busqueda y visibilidad por rol.
def list_books(user, filters):
    try:
        libros = _books_queryset()
        if user.rol != Usuario.Rol.ADMIN:
            libros = libros.filter(usuario_propietario=user)

        search = (filters.get('q') or '').strip()
        titulo = (filters.get('titulo') or '').strip()
        autor = (filters.get('autor') or '').strip()
        usuario = (filters.get('usuario') or '').strip()
        genero = (filters.get('genero') or '').strip()
        estado = (filters.get('estado') or '').strip()

        if search:
            libros = libros.filter(
                Q(titulo__icontains=search) |
                Q(autores__nombre1__icontains=search) |
                Q(autores__nombre2__icontains=search) |
                Q(autores__apellido1__icontains=search) |
                Q(autores__apellido2__icontains=search) |
                Q(autores__apodo__icontains=search)
            )
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


# Lista libros de otros usuarios para el dashboard de recomendaciones.
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


# Detalle de un libro con control de acceso por usuario.
def get_book_detail(user, libro_id):
    libro = _get_book_for_user(user, libro_id)
    return serialize_book(libro)


# Crea libro + relaciones (autor/genero) en una transaccion atomica.
def create_book(user, data, image_file=None):
    payload = validate_book_payload(data)
    url_imagen = payload['url_imagen'] or '/static/gestion_libros/imgs/libropredeterminado1.png'
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


# Normaliza y valida cada item de importacion masiva de libros.
def _normalize_import_book_payload(item, indice, default_url_imagen=''):
    if not isinstance(item, dict):
        raise ValidationServiceError(f'El libro en la posicion {indice} no es un objeto JSON valido.')

    usuario = item.get('usuario') or item.get('owner') or item.get('propietario')
    usuario_email = item.get('usuario_email') or item.get('email_usuario') or item.get('correo_usuario') or item.get('usuarioCorreo')
    if not usuario_email and isinstance(usuario, dict):
        usuario_email = (
            usuario.get('email') or
            usuario.get('correo') or
            usuario.get('usuario_email') or
            usuario.get('correo_usuario')
        )
    elif not usuario_email and isinstance(usuario, str):
        usuario_email = usuario

    usuario_email = str(usuario_email or item.get('email') or item.get('correo') or '').strip().lower()

    if not usuario_email:
        raise ValidationServiceError(f'El libro en la posicion {indice} no tiene el correo del usuario propietario.')

    usuario = Usuario.objects.filter(email=usuario_email, activo=True, is_active=True).first()
    if not usuario:
        raise ValidationServiceError(f'No existe un usuario activo con el correo {usuario_email}.')

    estado = str(item.get('estado') or Libro.Estado.PUBLICADO).strip()
    estados_validos = {valor.lower(): valor for valor in Libro.Estado.values}
    estado = estados_validos.get(estado.lower(), estado)

    payload = validate_book_payload(
        {
            'titulo': item.get('titulo') or item.get('nombre') or item.get('title'),
            'autor': item.get('autor') or item.get('autores') or item.get('author'),
            'sinopsis': item.get('sinopsis') or item.get('descripcion') or item.get('resumen') or item.get('synopsis'),
            'genero': item.get('genero') or item.get('categoria') or item.get('genre'),
            'estado': estado,
            'url_imagen': (
                item.get('url_imagen') or
                item.get('urlImagen') or
                item.get('imagen') or
                item.get('imagen_url') or
                item.get('portada') or
                item.get('cover') or
                default_url_imagen
            ),
        }
    )

    return usuario, payload


# Importa libros en lote y evita duplicados por usuario/titulo.
def import_books_from_payload(payload, default_url_imagen=''):
    books_payload = _extract_books_payload(payload)

    creados = 0
    omitidos = 0

    with transaction.atomic():
        for indice, item in enumerate(books_payload, start=1):
            usuario, libro_payload = _normalize_import_book_payload(item, indice, default_url_imagen=default_url_imagen)

            existe = Libro.objects.filter(
                activo=True,
                usuario_propietario=usuario,
                titulo__iexact=libro_payload['titulo'],
            ).exists()
            if existe:
                omitidos += 1
                continue

            create_book(usuario, libro_payload)
            creados += 1

    return {
        'creados': creados,
        'actualizados': 0,
        'omitidos': omitidos,
    }


# Actualiza datos del libro y sincroniza sus relaciones principales.
def update_book(user, libro_id, data, image_file=None):
    payload = validate_book_payload(data)
    libro = _get_book_for_user(user, libro_id)

    try:
        with transaction.atomic():
            libro.titulo = payload['titulo']
            libro.sinopsis = payload['sinopsis']
            libro.estado = payload['estado']
            if image_file:
                libro.url_imagen = _save_uploaded_image(image_file)
            elif payload['url_imagen']:
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


# Borrado logico: conserva historial y evita eliminar fisicamente.
def soft_delete_book(user, libro_id):
    libro = _get_book_for_user(user, libro_id)

    try:
        libro.activo = False
        libro.save(update_fields=['activo'])
    except DatabaseError as exc:
        raise DatabaseServiceError() from exc
