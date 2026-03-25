import json
import os
import uuid

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import Autor, Genero, Intercambio, Libro


User = get_user_model()


def index(request):
    return render(request, 'web/index.html')


def chats(request):
    return render(request, 'web/chats.html')


@ensure_csrf_cookie
def crear_cuenta(request):
    return render(request, 'web/crear_cuenta.html')


def dashboard_admin(request):
    return render(request, 'web/dashboard_admin.html')


@login_required(login_url='login')
def dashboard_usuario(request):
    libros_recomendados = (
        Libro.objects.filter(activo=True)
        .exclude(usuario_propietario=request.user)
        .exclude(usuario_propietario__isnull=True)
        .select_related('usuario_propietario')
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )
    total_libros_sistema = (
        Libro.objects.filter(activo=True)
        .exclude(usuario_propietario__isnull=True)
        .count()
    )
    libros_serializados = [_serialize_book(libro) for libro in libros_recomendados]
    return render(
        request,
        'web/dashboard_usuario.html',
        {
            'libros_recomendados': libros_serializados[:8],
            'libros_generos': libros_serializados[:8],
            'total_libros_sistema': total_libros_sistema,
            'total_libros_ajenos': len(libros_serializados),
        },
    )


def forgot_password(request):
    return render(request, 'web/forgot-password.html')


def inventario_admi(request):
    if request.user.is_authenticated and request.user.rol != User.Rol.ADMIN:
        return redirect('inventario')
    return render(request, 'web/inventario_admi.html')


@ensure_csrf_cookie
def inventario(request):
    if request.user.is_authenticated and request.user.rol == User.Rol.ADMIN:
        return redirect('inventario_admi')
    return render(request, 'web/inventario.html')


@ensure_csrf_cookie
def login(request):
    return render(request, 'web/login.html')


def notificaciones(request):
    return render(request, 'web/notificaciones.html')


def novedades_usuarios(request):
    return render(request, 'web/novedades_usuarios.html')


def perfil_admin(request):
    return render(request, 'web/perfil_admin.html')


def perfil(request):
    return render(request, 'web/perfil.html')


@ensure_csrf_cookie
def registrar_libro(request):
    return render(request, 'web/registrar_libro.html')


def reporte_libros(request):
    return render(request, 'web/reporte_libros.html')


def reset_password(request):
    return render(request, 'web/reset_password.html')


def _read_json_body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def _unauthorized_response():
    return JsonResponse({'message': 'Debes iniciar sesion.'}, status=401)


def _split_author_name(author_name):
    author_name = (author_name or '').strip()
    if not author_name:
        return '', None, '', None

    parts = [part for part in author_name.split() if part]
    if len(parts) == 1:
        return parts[0], None, parts[0], None
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


def _serialize_book(libro):
    autores = list(libro.autores.all())
    generos = list(libro.generos.all())
    autor_nombre = str(autores[0]) if autores else ''
    propietario = libro.usuario_propietario

    return {
        'id': libro.id,
        'idLibro': libro.id,
        'titulo': libro.titulo,
        'sinopsis': libro.sinopsis,
        'estado': libro.estado,
        'urlImagen': libro.url_imagen,
        'url_imagen': libro.url_imagen,
        'autor': autor_nombre,
        'autores': [str(autor) for autor in autores],
        'genero': generos[0].nombre if generos else '',
        'generos': [genero.nombre for genero in generos],
        'usuarioPropietarioId': libro.usuario_propietario_id,
        'usuario': str(propietario) if propietario else 'Usuario desconocido',
    }


@require_http_methods(["POST"])
def api_usuarios(request):
    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    password = (data.get('clave') or '').strip()
    email = (data.get('correo') or '').strip().lower()

    required_fields = {
        'primerNombre': 'El primer nombre es obligatorio.',
        'primerApellido': 'El primer apellido es obligatorio.',
        'correo': 'El correo es obligatorio.',
        'clave': 'La contrasena es obligatoria.',
        'direccion': 'La direccion es obligatoria.',
        'ciudad': 'La ciudad es obligatoria.',
        'telefono': 'El telefono es obligatorio.',
    }

    for field, message in required_fields.items():
        value = data.get(field)
        if value is None or str(value).strip() == '':
            return JsonResponse({'message': message}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({'message': 'Ya existe un usuario registrado con ese correo.'}, status=400)

    telefono = str(data.get('telefono')).strip()
    if not telefono.isdigit():
        return JsonResponse({'message': 'El telefono debe contener solo numeros.'}, status=400)

    user = User(
        email=email,
        nombre1=data.get('primerNombre', '').strip(),
        nombre2=(data.get('segundoNombre') or '').strip() or None,
        apellido1=data.get('primerApellido', '').strip(),
        apellido2=(data.get('segundoApellido') or '').strip() or None,
        direccion=data.get('direccion', '').strip(),
        ciudad=data.get('ciudad', '').strip(),
        telefono=int(telefono),
        rol=User.Rol.USUARIO,
    )

    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return JsonResponse({'message': ' '.join(exc.messages)}, status=400)

    user.set_password(password)
    user.save()

    return JsonResponse({'mensaje': 'Usuario registrado correctamente'})


@require_http_methods(["POST"])
def api_login(request):
    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    email = (data.get('correo') or '').strip().lower()
    password = data.get('clave') or ''

    if not email or not password:
        return JsonResponse({'message': 'Correo y contrasena son obligatorios.'}, status=400)

    user = authenticate(request, email=email, password=password)
    if user is None:
        return JsonResponse({'message': 'Credenciales invalidas.'}, status=401)

    if not user.is_active or not getattr(user, 'activo', True):
        return JsonResponse({'message': 'Tu cuenta esta inactiva.'}, status=403)

    auth_login(request, user)

    redirect_url = '/dashboard_admin/' if user.rol == User.Rol.ADMIN else '/dashboard_usuario/'
    return JsonResponse({
        'message': 'Inicio de sesion exitoso.',
        'role': user.rol,
        'redirect_url': redirect_url,
        'token': 'session-authenticated',
    })


@require_http_methods(["GET"])
def api_me(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    user = request.user
    return JsonResponse({
        'id': user.id,
        'idUsuario': user.id,
        'email': user.email,
        'primerNombre': user.nombre1,
        'segundoNombre': user.nombre2,
        'primerApellido': user.apellido1,
        'segundoApellido': user.apellido2,
        'direccion': user.direccion,
        'ciudad': user.ciudad,
        'telefono': user.telefono,
        'rol': user.rol,
    })


@require_http_methods(["GET", "POST"])
def api_libros(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    if request.method == 'GET':
        libros = (
            Libro.objects.filter(usuario_propietario=request.user, activo=True)
            .prefetch_related('autores', 'generos')
            .order_by('-id')
        )
        return JsonResponse([_serialize_book(libro) for libro in libros], safe=False)

    titulo = (request.POST.get('titulo') or '').strip()
    autor_nombre = (request.POST.get('autor') or '').strip()
    sinopsis = (request.POST.get('sinopsis') or '').strip()
    genero_nombre = (request.POST.get('genero') or '').strip()
    estado = (request.POST.get('estado') or Libro.Estado.PUBLICADO).strip()

    if not titulo or not autor_nombre or not genero_nombre:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            return render(
                request,
                'web/registrar_libro.html',
                {'error_registro_libro': 'Titulo, autor y genero son obligatorios.'},
                status=400,
            )
        return JsonResponse({'message': 'Titulo, autor y genero son obligatorios.'}, status=400)

    if estado not in Libro.Estado.values:
        estado = Libro.Estado.PUBLICADO

    image_file = request.FILES.get('imagen')
    if image_file:
        url_imagen = _save_uploaded_image(image_file)
    else:
        url_imagen = '/static/web/imgs/libro_de_la_selva.jpg'

    libro = Libro.objects.create(
        titulo=titulo,
        sinopsis=sinopsis,
        estado=estado,
        url_imagen=url_imagen,
        usuario_propietario=request.user,
    )

    autor = _get_or_create_author(autor_nombre)
    genero, _ = Genero.objects.get_or_create(nombre=genero_nombre.title())
    libro.autores.add(autor)
    libro.generos.add(genero)

    if request.content_type and request.content_type.startswith('multipart/form-data'):
        destino = 'inventario_admi' if request.user.rol == User.Rol.ADMIN else 'inventario'
        return redirect(destino)

    return JsonResponse(_serialize_book(libro), status=201)


@require_http_methods(["GET"])
def api_libros_recomendados(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    libros = (
        Libro.objects.filter(activo=True)
        .exclude(usuario_propietario=request.user)
        .exclude(usuario_propietario__isnull=True)
        .select_related('usuario_propietario')
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )
    return JsonResponse([_serialize_book(libro) for libro in libros], safe=False)


@require_http_methods(["GET", "DELETE"])
def api_libro_detalle(request, libro_id):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    try:
        libro = Libro.objects.prefetch_related('autores', 'generos').get(id=libro_id, activo=True)
    except Libro.DoesNotExist:
        return JsonResponse({'message': 'Libro no encontrado.'}, status=404)

    if libro.usuario_propietario_id != request.user.id and request.user.rol != User.Rol.ADMIN:
        return JsonResponse({'message': 'No tienes permiso para este libro.'}, status=403)

    if request.method == 'GET':
        return JsonResponse(_serialize_book(libro))

    libro.activo = False
    libro.save(update_fields=['activo'])
    return JsonResponse({'message': 'Libro eliminado correctamente.'})


@require_http_methods(["POST"])
def api_solicitar_intercambio(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    libro_id = data.get('libroId')
    if not libro_id:
        return JsonResponse({'message': 'Debes indicar el libro solicitado.'}, status=400)

    try:
        libro = Libro.objects.select_related('usuario_propietario').get(id=libro_id, activo=True)
    except Libro.DoesNotExist:
        return JsonResponse({'message': 'El libro solicitado no existe.'}, status=404)

    if libro.usuario_propietario_id == request.user.id:
        return JsonResponse({'message': 'No puedes solicitar intercambio por tu propio libro.'}, status=400)

    existente = Intercambio.objects.filter(
        usuario_solicitante=request.user,
        libro_solicitado=libro,
        estado=Intercambio.Estado.PENDIENTE,
        activo=True,
    ).exists()
    if existente:
        return JsonResponse({'message': 'Ya tienes una solicitud pendiente para este libro.'}, status=400)

    intercambio = Intercambio.objects.create(
        estado=Intercambio.Estado.PENDIENTE,
        usuario_solicitante=request.user,
        usuario_receptor=libro.usuario_propietario,
        libro_solicitado=libro,
        libro_cambio=None,
    )

    return JsonResponse({
        'message': 'Solicitud de intercambio enviada correctamente.',
        'idIntercambio': intercambio.id,
    }, status=201)
