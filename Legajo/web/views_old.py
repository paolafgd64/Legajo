"""
ARCHIVO LEGACY / BACKUP

Este archivo conserva la version monolitica anterior de views.py.
No es el punto de entrada actual de las rutas.
Las rutas activas importan desde el paquete web/views/ (carpeta modular).

Se mantiene temporalmente como respaldo historico.
Si ya validaste estabilidad, puede eliminarse sin afectar las rutas actuales.
"""

import calendar
import datetime
import json
import random
import textwrap
import unicodedata
from json import JSONDecodeError

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from .models import Intercambio, Libro, ReporteUsuario
from .services import (
    create_book,
    get_book_detail,
    import_books_from_payload,
    import_users_from_payload,
    list_books,
    list_recommended_books,
    request_exchange,
    serialize_book,
    soft_delete_book,
    update_book,
)
from .validators import ControlledError


User = get_user_model()


# Helper: centraliza la validacion de acceso de administrador para vistas y APIs.
def _admin_required_response(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()
    if request.user.rol != User.Rol.ADMIN:
        return _forbidden_response()
    return None


# Helper: calcula el porcentaje de crecimiento entre dos periodos para tarjetas del dashboard.
def _format_trend(current_value, previous_value):
    if previous_value == 0:
        if current_value == 0:
            return {'value': '0.0%', 'positive': True}
        return {'value': '+100.0%', 'positive': True}

    change = ((current_value - previous_value) / previous_value) * 100
    return {
        'value': f'{change:+.1f}%',
        'positive': change >= 0,
    }


# Helper: construye una serie acumulada diaria del mes actual (grafica de linea).
def _build_monthly_cumulative_series(queryset, date_field):
    today = timezone.localdate()
    last_day = calendar.monthrange(today.year, today.month)[1]

    counts = (
        queryset.filter(
            **{
                f'{date_field}__year': today.year,
                f'{date_field}__month': today.month,
            }
        )
        .annotate(day=TruncDate(date_field))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )

    daily_totals = {item['day'].day: item['total'] for item in counts if item['day']}
    cumulative = []
    running_total = 0
    for day in range(1, last_day + 1):
        running_total += daily_totals.get(day, 0)
        cumulative.append(running_total)

    return {
        'labels': [str(day) for day in range(1, last_day + 1)],
        'data': cumulative,
    }


# Arma el contexto estadistico del dashboard admin reutilizando consultas agregadas.
def _get_admin_dashboard_context():
    today = timezone.localdate()
    current_month_start = today.replace(day=1)
    previous_month_end = current_month_start - datetime.timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    usuarios_total = User.objects.filter(activo=True).count()
    usuarios_mes = User.objects.filter(date_joined__date__gte=current_month_start, activo=True).count()
    usuarios_mes_anterior = User.objects.filter(
        date_joined__date__gte=previous_month_start,
        date_joined__date__lte=previous_month_end,
        activo=True,
    ).count()

    reportes_total = ReporteUsuario.objects.filter(activo=True).count()
    reportes_mes = ReporteUsuario.objects.filter(
        activo=True,
        fecha_reporte__date__gte=current_month_start,
    ).count()
    reportes_mes_anterior = ReporteUsuario.objects.filter(
        activo=True,
        fecha_reporte__date__gte=previous_month_start,
        fecha_reporte__date__lte=previous_month_end,
    ).count()

    return {
        'admin_stats': {
            'usuarios_total': usuarios_total,
            'usuarios_trend': _format_trend(usuarios_mes, usuarios_mes_anterior),
            'reportes_total': reportes_total,
            'reportes_trend': _format_trend(reportes_mes, reportes_mes_anterior),
        }
    }


# Serializer simple para devolver usuarios en JSON legible por el frontend admin.
def _serialize_admin_user(user):
    nombre_completo = ' '.join(filter(None, [user.nombre1, user.nombre2, user.apellido1, user.apellido2]))
    return {
        'id': user.id,
        'nombreCompleto': nombre_completo,
        'correo': user.email,
        'ciudad': user.ciudad,
        'telefono': str(user.telefono or ''),
        'rol': user.get_rol_display(),
        'rolValor': user.rol,
        'estado': 'Activo' if user.activo and user.is_active else 'Inactivo',
    }


def index(request):
    return render(request, 'web/index.html')


@login_required(login_url='login')
@never_cache
def chats(request):
    return render(request, 'web/chats.html')


@ensure_csrf_cookie
def crear_cuenta(request):
    # Solo renderiza la pagina de registro. La creacion real ocurre en api_usuarios.
    return render(request, 'web/crear_cuenta.html')


@login_required(login_url='login')
@never_cache
def dashboard_admin(request):
    if request.user.rol != User.Rol.ADMIN:
        return redirect('dashboard_usuario')

    context = _get_admin_dashboard_context()
    context['admin_name'] = request.user.nombre1 or 'Administrador'
    return render(request, 'web/dashboard_admin.html', context)


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
@require_http_methods(["GET", "POST"])
def carga_masiva_usuarios(request):
    admin_error = _admin_required_response(request)
    if admin_error:
        return redirect('dashboard_usuario') if request.user.is_authenticated else redirect('login')

    context = {
        'admin_name': request.user.nombre1 or 'Administrador',
    }

    if request.method == 'POST':
        archivo = request.FILES.get('archivo_usuarios')
        actualizar = request.POST.get('actualizar_existentes') == 'on'
        context['actualizar_existentes'] = actualizar

        if not archivo:
            context['error_message'] = 'Debes seleccionar un archivo JSON para importar.'
            return render(request, 'web/carga_masiva_usuarios.html', context, status=400)

        try:
            payload = json.loads(archivo.read().decode('utf-8-sig'))
            resultado = import_users_from_payload(payload, actualizar=actualizar)
        except UnicodeDecodeError:
            context['error_message'] = 'El archivo debe estar codificado en UTF-8.'
            return render(request, 'web/carga_masiva_usuarios.html', context, status=400)
        except JSONDecodeError as exc:
            context['error_message'] = f'El archivo no contiene JSON valido: {exc}'
            return render(request, 'web/carga_masiva_usuarios.html', context, status=400)
        except ControlledError as exc:
            context['error_message'] = exc.message
            return render(request, 'web/carga_masiva_usuarios.html', context, status=400)

        context['success_message'] = (
            f"Importacion completada. Creados: {resultado['creados']}, "
            f"actualizados: {resultado['actualizados']}, omitidos: {resultado['omitidos']}."
        )

    return render(request, 'web/carga_masiva_usuarios.html', context)


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
@require_http_methods(["GET", "POST"])
def usuarios_admin(request):
    admin_error = _admin_required_response(request)
    if admin_error:
        return redirect('dashboard_usuario') if request.user.is_authenticated else redirect('login')

    context = {
        'admin_name': request.user.nombre1 or 'Administrador',
    }

    mensaje_exito = request.session.pop('mensaje_exito_carga_usuarios', None)
    if mensaje_exito:
        context['mensaje_exito_carga'] = mensaje_exito

    if request.method == 'POST':
        archivo = request.FILES.get('archivo_usuarios')

        if not archivo:
            context['mensaje_error_carga'] = 'Debes seleccionar un archivo JSON para importar.'
            return render(request, 'web/usuarios_admin.html', context, status=400)

        try:
            payload = json.loads(archivo.read().decode('utf-8-sig'))
            resultado = import_users_from_payload(payload, actualizar=False)
        except UnicodeDecodeError:
            context['mensaje_error_carga'] = 'El archivo debe estar codificado en UTF-8.'
            return render(request, 'web/usuarios_admin.html', context, status=400)
        except JSONDecodeError as exc:
            context['mensaje_error_carga'] = f'El archivo no contiene JSON valido: {exc}'
            return render(request, 'web/usuarios_admin.html', context, status=400)
        except ControlledError as exc:
            context['mensaje_error_carga'] = exc.message
            return render(request, 'web/usuarios_admin.html', context, status=400)

        request.session['mensaje_exito_carga_usuarios'] = (
            f"Importacion completada. Creados: {resultado['creados']}, "
            f"actualizados: {resultado['actualizados']}, omitidos: {resultado['omitidos']}."
        )
        return redirect('usuarios_admin')

    return render(request, 'web/usuarios_admin.html', context)


@login_required(login_url='login')
@require_http_methods(["GET"])
def api_admin_reported_users(request):
    admin_error = _admin_required_response(request)
    if admin_error:
        return admin_error

    data = _build_monthly_cumulative_series(
        ReporteUsuario.objects.filter(activo=True),
        'fecha_reporte',
    )
    return JsonResponse(data)


@login_required(login_url='login')
@require_http_methods(["GET"])
def api_admin_completed_exchanges(request):
    admin_error = _admin_required_response(request)
    if admin_error:
        return admin_error

    data = _build_monthly_cumulative_series(
        Intercambio.objects.filter(
            activo=True,
            estado=Intercambio.Estado.COMPLETADO,
            fecha_completado__isnull=False,
        ),
        'fecha_completado',
    )
    return JsonResponse(data)


@login_required(login_url='login')
@require_http_methods(["GET"])
def api_admin_users(request):
    admin_error = _admin_required_response(request)
    if admin_error:
        return admin_error

    usuarios = User.objects.all().order_by('-id')

    nombre = (request.GET.get('nombre') or '').strip()
    correo = (request.GET.get('correo') or '').strip()
    ciudad = (request.GET.get('ciudad') or '').strip()
    rol = (request.GET.get('rol') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    if nombre:
        usuarios = usuarios.filter(
            Q(nombre1__icontains=nombre) |
            Q(nombre2__icontains=nombre) |
            Q(apellido1__icontains=nombre) |
            Q(apellido2__icontains=nombre)
        )
    if correo:
        usuarios = usuarios.filter(email__icontains=correo)
    if ciudad:
        usuarios = usuarios.filter(ciudad__icontains=ciudad)
    if rol:
        usuarios = usuarios.filter(rol=rol)
    if estado == 'activo':
        usuarios = usuarios.filter(activo=True, is_active=True)
    elif estado == 'inactivo':
        usuarios = usuarios.filter(Q(activo=False) | Q(is_active=False))

    return JsonResponse([_serialize_admin_user(usuario) for usuario in usuarios], safe=False)


@login_required(login_url='login')
@never_cache
def dashboard_usuario(request):
    libros_recomendados = (
        Libro.objects.filter(activo=True)
        .exclude(usuario_propietario=request.user)
        .exclude(usuario_propietario__isnull=True)
        .select_related('usuario_propietario')
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )
    libros_serializados = [serialize_book(libro) for libro in libros_recomendados]
    return render(
        request,
        'web/dashboard_usuario.html',
        {
            'libros_recomendados': libros_serializados[:8],
            'libros_generos': [],
            'total_libros_sistema': Libro.objects.filter(activo=True).count(),
            'total_libros_ajenos': libros_recomendados.count(),
        },
    )


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def forgot_password(request):
    context = {}

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        context['submitted_email'] = email

        if not email:
            context['error_message'] = 'Debes ingresar un correo electronico.'
            return render(request, 'web/forgot-password.html', context, status=400)

        try:
            user = User.objects.get(email=email, activo=True, is_active=True)
        except User.DoesNotExist:
            user = None

        context['success_message'] = 'Si el correo existe en Legajo, ya generamos un enlace para restablecer la contrasena.'
        if user and settings.DEBUG:
            context['reset_link'] = _build_password_reset_link(request, user)

    return render(request, 'web/forgot-password.html', context)


@login_required(login_url='login')
@never_cache
def inventario_admi(request):
    if request.user.rol != User.Rol.ADMIN:
        return redirect('dashboard_usuario')
    return render(request, 'web/inventario_admi.html')


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
def inventario(request):
    return render(request, 'web/inventario.html')


@ensure_csrf_cookie
def login(request):
    return render(request, 'web/login.html')


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
def notificaciones(request):
    return render(request, 'web/notificaciones.html')


def novedades_usuarios(request):
    return render(request, 'web/novedades_usuarios.html')


@login_required(login_url='login')
@never_cache
def perfil_admin(request):
    user = request.user
    return render(request, 'web/perfil_admin.html', {
        'perfil_usuario': user,
        'nombre_completo': ' '.join(filter(None, [user.nombre1, user.nombre2, user.apellido1, user.apellido2])),
    })


@login_required(login_url='login')
@never_cache
def perfil(request):
    user = request.user
    return render(request, 'web/perfil.html', {
        'perfil_usuario': user,
        'nombre_completo': ' '.join(filter(None, [user.nombre1, user.nombre2, user.apellido1, user.apellido2])),
    })


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
def registrar_libro(request, libro_id=None):
    source = (request.GET.get('source') or request.POST.get('source') or '').strip().lower()
    is_admin = request.user.is_authenticated and request.user.rol == User.Rol.ADMIN
    if is_admin and not source:
        source = 'admin'
    back_url_name = 'inventario_admi' if is_admin else 'inventario'
    context = {
        'source': source,
        'back_url_name': back_url_name,
    }

    if libro_id is not None:
        if not request.user.is_authenticated:
            return redirect('login')

        try:
            libro = Libro.objects.prefetch_related('autores', 'generos').get(id=libro_id, activo=True)
        except Libro.DoesNotExist:
            return redirect('inventario')

        if libro.usuario_propietario_id != request.user.id and request.user.rol != User.Rol.ADMIN:
            return redirect('inventario')

        autores = list(libro.autores.all())
        generos = list(libro.generos.all())
        context['modo_edicion'] = True
        context['libro_edicion'] = {
            'id': libro.id,
            'titulo': libro.titulo,
            'autor': str(autores[0]) if autores else '',
            'sinopsis': libro.sinopsis,
            'genero': generos[0].nombre if generos else '',
            'estado': libro.estado,
            'url_imagen': libro.url_imagen,
        }

    return render(request, 'web/registrar_libro.html', context)


@login_required(login_url='login')
@never_cache
@require_http_methods(["POST"])
def logout_view(request):
    auth_logout(request)
    response = redirect('index')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
@require_http_methods(["GET", "POST"])
def reporte_libros(request):
    admin_error = _admin_required_response(request)
    if admin_error:
        return redirect('dashboard_usuario') if request.user.is_authenticated else redirect('login')

    context = {
        'admin_name': request.user.nombre1 or 'Administrador',
        'url_portada_predeterminada': (
            'https://res.cloudinary.com/drc65wu6o/image/upload/v1775351180/legajo/libros/lysnrsy33skcmjojrk65.jpg'
        ),
    }

    mensaje_exito = request.session.pop('mensaje_exito_carga_libros', None)
    if mensaje_exito:
        context['mensaje_exito_carga'] = mensaje_exito

    if request.method == 'POST':
        archivo = request.FILES.get('archivo_libros')

        if not archivo:
            context['mensaje_error_carga'] = 'Debes seleccionar un archivo JSON para importar.'
            return render(request, 'web/reporte_libros.html', context, status=400)

        try:
            payload = json.loads(archivo.read().decode('utf-8-sig'))
            resultado = import_books_from_payload(
                payload,
                default_url_imagen=context['url_portada_predeterminada'],
            )
        except UnicodeDecodeError:
            context['mensaje_error_carga'] = 'El archivo debe estar codificado en UTF-8.'
            return render(request, 'web/reporte_libros.html', context, status=400)
        except JSONDecodeError as exc:
            context['mensaje_error_carga'] = f'El archivo no contiene JSON valido: {exc}'
            return render(request, 'web/reporte_libros.html', context, status=400)
        except ControlledError as exc:
            context['mensaje_error_carga'] = exc.message
            return render(request, 'web/reporte_libros.html', context, status=400)

        request.session['mensaje_exito_carga_libros'] = (
            f"Importacion completada. Creados: {resultado['creados']}, "
            f"actualizados: {resultado['actualizados']}, omitidos: {resultado['omitidos']}."
        )
        return redirect('reporte_libros')

    return render(request, 'web/reporte_libros.html', context)


@login_required(login_url='login')
@require_http_methods(["GET"])
def reporte_libros_pdf(request):
    if request.user.rol != User.Rol.ADMIN:
        return _forbidden_response()

    libros = (
        Libro.objects.filter(activo=True)
        .select_related('usuario_propietario')
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )

    titulo = (request.GET.get('titulo') or '').strip()
    autor = (request.GET.get('autor') or '').strip()
    usuario = (request.GET.get('usuario') or '').strip()
    genero = (request.GET.get('genero') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    if titulo:
        libros = libros.filter(titulo__icontains=titulo)
    if autor:
        libros = libros.filter(autores__nombre1__icontains=autor).distinct()
    if usuario:
        libros = libros.filter(usuario_propietario__nombre1__icontains=usuario).distinct()
    if genero:
        libros = libros.filter(generos__nombre__icontains=genero).distinct()
    if estado:
        libros = libros.filter(estado__icontains=estado)

    rows = []
    for libro in libros:
        serialized = serialize_book(libro)
        rows.append([
            serialized['usuario'],
            serialized['titulo'],
            serialized['autor'],
            serialized['genero'],
            serialized['estado'],
        ])

    return _build_pdf_response('Reporte de libros registrados', rows, 'reporte_libros.pdf')


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def reset_password(request):
    uid = (request.GET.get('uid') or request.POST.get('uid') or '').strip()
    token = (request.GET.get('token') or request.POST.get('token') or '').strip()
    user = _get_password_reset_user(uid) if uid else None
    token_is_valid = bool(user and token and default_token_generator.check_token(user, token))

    context = {
        'uid': uid,
        'token': token,
        'token_is_valid': token_is_valid,
    }

    if request.method == 'POST':
        if not token_is_valid:
            context['error_message'] = 'El enlace de recuperacion no es valido o ya vencio.'
            return render(request, 'web/reset_password.html', context, status=400)

        password = request.POST.get('password') or ''
        confirm_password = request.POST.get('confirmPassword') or ''

        if not password or not confirm_password:
            context['error_message'] = 'Debes completar ambos campos de contrasena.'
            return render(request, 'web/reset_password.html', context, status=400)

        if password != confirm_password:
            context['error_message'] = 'Las contrasenas no coinciden.'
            return render(request, 'web/reset_password.html', context, status=400)

        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            context['error_message'] = _normalize_validation_messages(exc.messages)
            return render(request, 'web/reset_password.html', context, status=400)

        user.set_password(password)
        user.save(update_fields=['password'])
        return redirect(f"{reverse('login')}?reset=success")

    return render(request, 'web/reset_password.html', context)


def _read_json_body(request):
    # Estandariza lectura de JSON para evitar repetir try/except en cada endpoint.
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def _unauthorized_response():
    return JsonResponse({'message': 'Debes iniciar sesion.'}, status=401)


def _forbidden_response():
    return JsonResponse({'message': 'No tienes permiso para esta accion.'}, status=403)


def _service_error_response(error):
    return JsonResponse({'message': error.message}, status=error.status_code)


def _normalize_validation_message(raw_message):
    if not raw_message:
        return 'No se pudo procesar la validacion.'

    replacements = {
        'This password is too short. It must contain at least 8 characters.': 'La contrasena debe tener al menos 8 caracteres.',
        'This password is too common.': 'La contrasena es demasiado comun. Elige una mas segura.',
        'This password is entirely numeric.': 'La contrasena no puede estar compuesta solo por numeros.',
        'The password is too similar to the email address.': 'La contrasena es demasiado parecida al correo electronico.',
        'The password is too similar to the first name.': 'La contrasena es demasiado parecida al primer nombre.',
        'The password is too similar to the last name.': 'La contrasena es demasiado parecida al apellido.',
        'The password is too similar to the username.': 'La contrasena es demasiado parecida a los datos del usuario.',
    }

    normalized = str(raw_message).strip()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    return normalized


def _normalize_validation_messages(messages):
    return ' '.join(_normalize_validation_message(message) for message in messages if message).strip()


def _build_password_reset_link(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = f"{reverse('reset_password')}?uid={uid}&token={token}"
    return request.build_absolute_uri(path)


def _get_password_reset_user(uidb64):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=user_id, activo=True, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def _normalize_pdf_text(value):
    normalized = unicodedata.normalize('NFKD', str(value or ''))
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    return ascii_text.replace('\r', ' ').replace('\n', ' ').strip()


def _pdf_escape(value):
    return (
        _normalize_pdf_text(value)
        .replace('\\', '\\\\')
        .replace('(', '\\(')
        .replace(')', '\\)')
    )


def _pdf_color(r, g, b, fill=True):
    operator = 'rg' if fill else 'RG'
    return f'{r / 255:.3f} {g / 255:.3f} {b / 255:.3f} {operator}'


def _pdf_rect(x, y, width, height, fill_color=None, stroke_color=None, line_width=1):
    commands = []
    if line_width:
        commands.append(f'{line_width} w')
    if fill_color:
        commands.append(_pdf_color(*fill_color, fill=True))
    if stroke_color:
        commands.append(_pdf_color(*stroke_color, fill=False))
    paint = 'B' if fill_color and stroke_color else 'f' if fill_color else 'S'
    commands.append(f'{x:.2f} {y:.2f} {width:.2f} {height:.2f} re {paint}')
    return '\n'.join(commands)


def _pdf_text_block(x, y, lines, font_key, size, color):
    if not lines:
        return ''
    commands = [
        'BT',
        f'/{font_key} {size} Tf',
        _pdf_color(*color, fill=True),
        f'1 0 0 1 {x:.2f} {y:.2f} Tm',
    ]
    for index, line in enumerate(lines):
        escaped_line = _pdf_escape(line)
        if index == 0:
            commands.append(f'({escaped_line}) Tj')
        else:
            commands.append(f'0 -{size + 3} Td')
            commands.append(f'({escaped_line}) Tj')
    commands.append('ET')
    return '\n'.join(commands)


def _wrap_pdf_cell(value, width, font_size):
    approx_chars = max(6, int(width / max(font_size * 0.52, 1)))
    normalized = _normalize_pdf_text(value) or '-'
    return textwrap.wrap(normalized, width=approx_chars) or ['-']


def _get_jpeg_size(image_bytes):
    if image_bytes[:2] != b'\xff\xd8':
        raise ValueError('Unsupported image format')
    index = 2
    while index < len(image_bytes):
        if image_bytes[index] != 0xFF:
            index += 1
            continue
        marker = image_bytes[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        length = int.from_bytes(image_bytes[index:index + 2], 'big')
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(image_bytes[index + 3:index + 5], 'big')
            width = int.from_bytes(image_bytes[index + 5:index + 7], 'big')
            return width, height
        index += length
    raise ValueError('JPEG size not found')


def _load_pdf_logo():
    logo_path = settings.BASE_DIR / 'web' / 'static' / 'web' / 'imgs' / 'logo_oscuro1.jpg'
    if not logo_path.exists():
        return None
    image_bytes = logo_path.read_bytes()
    width, height = _get_jpeg_size(image_bytes)
    return {
        'bytes': image_bytes,
        'width': width,
        'height': height,
    }


def _build_pdf_response(title, rows, filename):
    page_width = 612
    page_height = 792
    margin = 36
    header_height = 86
    footer_height = 28
    row_padding = 6
    cell_font_size = 8
    header_font_size = 10
    body_color = (20, 20, 20)
    white = (255, 255, 255)
    gold = (242, 174, 46)
    soft_gold = (255, 242, 214)
    navy = (9, 19, 38)
    light_border = (220, 220, 220)
    row_alt = (248, 248, 248)
    logo = _load_pdf_logo()

    columns = [
        ('Usuario', 120),
        ('Titulo', 150),
        ('Autor', 120),
        ('Genero', 90),
        ('Estado', 60),
    ]

    table_width = sum(width for _, width in columns)
    table_x = margin
    current_y = page_height - margin
    pages_commands = []
    current_commands = []
    page_number = 1

    def start_page():
        nonlocal current_y, current_commands, page_number
        current_commands = []
        current_commands.append(_pdf_rect(0, page_height - header_height, page_width, header_height, fill_color=navy))
        current_commands.append(_pdf_rect(0, page_height - header_height, page_width, 6, fill_color=gold))
        if logo:
            logo_width = 52
            logo_height = logo_width * logo['height'] / logo['width']
            logo_x = margin
            logo_y = page_height - header_height + 16
            current_commands.append(
                '\n'.join([
                    'q',
                    f'{logo_width:.2f} 0 0 {logo_height:.2f} {logo_x:.2f} {logo_y:.2f} cm',
                    '/Im1 Do',
                    'Q',
                ])
            )
        current_commands.append(_pdf_text_block(margin + 64, page_height - 42, ['LEGAJO'], 'F2', 22, gold))
        current_commands.append(_pdf_text_block(margin + 64, page_height - 60, [title], 'F1', 11, white))
        current_commands.append(
            _pdf_text_block(
                page_width - 180,
                page_height - 48,
                [f'Generado: {datetime.datetime.now():%Y-%m-%d %H:%M}', f'Pagina {page_number}'],
                'F1',
                9,
                white,
            )
        )

        table_top = page_height - header_height - 18
        current_commands.append(_pdf_rect(table_x, table_top - 26, table_width, 26, fill_color=gold))
        x_cursor = table_x
        for label, width in columns:
            current_commands.append(_pdf_text_block(x_cursor + 6, table_top - 17, [label], 'F2', header_font_size, navy))
            x_cursor += width
        current_y = table_top - 26
        page_number += 1

    def finish_page():
        footer_y = 12
        current_commands.append(_pdf_rect(0, footer_y + 12, page_width, 2, fill_color=gold))
        current_commands.append(_pdf_text_block(margin, footer_y, ['Legajo - Reporte administrativo'], 'F1', 8, body_color))
        pages_commands.append('\n'.join(command for command in current_commands if command))

    start_page()

    if not rows:
        row_height = 28
        current_commands.append(_pdf_rect(table_x, current_y - row_height, table_width, row_height, fill_color=soft_gold, stroke_color=light_border))
        current_commands.append(
            _pdf_text_block(table_x + 8, current_y - 18, ['No hay libros registrados con los filtros seleccionados.'], 'F1', 10, body_color)
        )
        current_y -= row_height
    else:
        for row_index, row in enumerate(rows):
            cell_lines = []
            max_lines = 1
            for (_, width), value in zip(columns, row):
                wrapped = _wrap_pdf_cell(value, width - 10, cell_font_size)
                cell_lines.append(wrapped)
                max_lines = max(max_lines, len(wrapped))

            row_height = max(24, max_lines * (cell_font_size + 3) + (row_padding * 2))
            if current_y - row_height < margin + footer_height:
                finish_page()
                start_page()

            fill = white if row_index % 2 == 0 else row_alt
            current_commands.append(_pdf_rect(table_x, current_y - row_height, table_width, row_height, fill_color=fill, stroke_color=light_border))

            x_cursor = table_x
            for column_index, ((_, width), wrapped_lines) in enumerate(zip(columns, cell_lines)):
                if column_index > 0:
                    current_commands.append(_pdf_rect(x_cursor, current_y - row_height, 0.7, row_height, fill_color=light_border))
                text_color = gold if column_index == 1 else body_color
                current_commands.append(
                    _pdf_text_block(
                        x_cursor + 6,
                        current_y - 14,
                        wrapped_lines,
                        'F2' if column_index == 1 else 'F1',
                        cell_font_size,
                        text_color,
                    )
                )
                x_cursor += width

            current_y -= row_height

    finish_page()

    objects = []

    def add_object(content):
        if isinstance(content, str):
            content = content.encode('latin-1', errors='replace')
        objects.append(content)
        return len(objects)

    catalog_obj = add_object('')
    pages_obj = add_object('')
    font_regular_obj = add_object('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    font_bold_obj = add_object('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>')
    image_obj = None
    if logo:
        image_obj = add_object(
            b'<< /Type /XObject /Subtype /Image /Width '
            + str(logo['width']).encode('ascii')
            + b' /Height '
            + str(logo['height']).encode('ascii')
            + b' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length '
            + str(len(logo['bytes'])).encode('ascii')
            + b' >>\nstream\n'
            + logo['bytes']
            + b'\nendstream'
        )

    page_object_numbers = []
    content_object_numbers = []
    for page_commands in pages_commands:
        stream_content = page_commands.encode('latin-1', errors='replace')
        content_obj = add_object(
            b'<< /Length ' + str(len(stream_content)).encode('ascii') + b' >>\nstream\n' + stream_content + b'\nendstream'
        )
        page_obj = add_object('')
        content_object_numbers.append(content_obj)
        page_object_numbers.append(page_obj)

    kids = ' '.join(f'{page_obj} 0 R' for page_obj in page_object_numbers)
    objects[catalog_obj - 1] = f'<< /Type /Catalog /Pages {pages_obj} 0 R >>'.encode('latin-1')
    objects[pages_obj - 1] = f'<< /Type /Pages /Kids [{kids}] /Count {len(page_object_numbers)} >>'.encode('latin-1')

    xobject_part = f'/XObject << /Im1 {image_obj} 0 R >> ' if image_obj else ''
    for page_obj, content_obj in zip(page_object_numbers, content_object_numbers):
        objects[page_obj - 1] = (
            f'<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {page_width} {page_height}] '
            f'/Resources << /Font << /F1 {font_regular_obj} 0 R /F2 {font_bold_obj} 0 R >> {xobject_part}>> '
            f'/Contents {content_obj} 0 R >>'
        ).encode('latin-1')

    pdf = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f'{index} 0 obj\n'.encode('ascii'))
        pdf.extend(obj)
        pdf.extend(b'\nendobj\n')

    xref_start = len(pdf)
    pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
    pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))

    pdf.extend(
        (
            f'trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n'
            f'startxref\n{xref_start}\n%%EOF'
        ).encode('ascii')
    )

    response = HttpResponse(bytes(pdf), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@require_http_methods(["POST"])
def api_usuarios(request):
    # Endpoint de registro: valida payload, crea usuario y guarda hash de contrasena.
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

    # Regla de unicidad: no se permiten correos duplicados.
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
        # Reutiliza validadores de Django (longitud, similitud, complejidad, etc.).
        validate_password(password, user=user)
    except ValidationError as exc:
        return JsonResponse({'message': _normalize_validation_messages(exc.messages)}, status=400)

    # Nunca se guarda texto plano: set_password aplica hashing seguro.
    user.set_password(password)
    user.save()

    return JsonResponse({'mensaje': 'Usuario registrado correctamente'})


@require_http_methods(["POST"])
def api_login(request):
    # Login por correo+contrasena usando el backend de autenticacion de Django.
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

    # Crea la sesion del usuario autenticado (cookie de sesion en respuesta).
    auth_login(request, user)

    redirect_url = '/dashboard_admin/' if user.rol == User.Rol.ADMIN else '/dashboard_usuario/'
    return JsonResponse({
        'message': 'Inicio de sesion exitoso.',
        'role': user.rol,
        'redirect_url': redirect_url,
        'token': 'session-authenticated',
    })


@require_http_methods(["GET", "PUT"])
def api_me(request):
    # Perfil del usuario logueado: GET consulta, PUT actualiza.
    if not request.user.is_authenticated:
        return _unauthorized_response()

    user = request.user
    if request.method == 'PUT':
        data = _read_json_body(request)
        if data is None:
            return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

        required_fields = {
            'primerNombre': 'El primer nombre es obligatorio.',
            'primerApellido': 'El primer apellido es obligatorio.',
            'correo': 'El correo es obligatorio.',
            'direccion': 'La direccion es obligatoria.',
            'ciudad': 'La ciudad es obligatoria.',
            'telefono': 'El telefono es obligatorio.',
        }

        for field, message in required_fields.items():
            value = data.get(field)
            if value is None or str(value).strip() == '':
                return JsonResponse({'message': message}, status=400)

        email = (data.get('correo') or '').strip().lower()
        telefono = str(data.get('telefono')).strip()

        if not telefono.isdigit():
            return JsonResponse({'message': 'El telefono debe contener solo numeros.'}, status=400)

        if User.objects.exclude(id=user.id).filter(email=email).exists():
            return JsonResponse({'message': 'Ya existe un usuario registrado con ese correo.'}, status=400)

        user.email = email
        user.nombre1 = (data.get('primerNombre') or '').strip()
        user.nombre2 = (data.get('segundoNombre') or '').strip() or None
        user.apellido1 = (data.get('primerApellido') or '').strip()
        user.apellido2 = (data.get('segundoApellido') or '').strip() or None
        user.direccion = (data.get('direccion') or '').strip()
        user.ciudad = (data.get('ciudad') or '').strip()
        user.telefono = int(telefono)
        user.save()

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
    # Libros del usuario: GET lista con filtros; POST registra un libro nuevo.
    if not request.user.is_authenticated:
        return _unauthorized_response()

    if request.method == 'GET':
        try:
            # La logica de negocio vive en services/books.py
            libros = list_books(request.user, request.GET)
        except ControlledError as error:
            return _service_error_response(error)
        return JsonResponse(libros, safe=False)

    try:
        # Para multipart/form-data se combinan campos POST + archivo de imagen.
        libro = create_book(
            request.user,
            request.POST,
            image_file=request.FILES.get('imagen'),
        )
    except ControlledError as error:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            return render(
                request,
                'web/registrar_libro.html',
                {'error_registro_libro': error.message},
                status=error.status_code,
            )
        return _service_error_response(error)

    return JsonResponse(libro, status=201)


@require_http_methods(["GET"])
def api_libros_recomendados(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    try:
        libros = list_recommended_books(request.user)
    except ControlledError as error:
        return _service_error_response(error)
    return JsonResponse(libros, safe=False)


@require_http_methods(["GET", "PUT", "DELETE"])
def api_libro_detalle(request, libro_id):
    # CRUD por id: GET detalle, PUT edicion, DELETE borrado logico.
    if not request.user.is_authenticated:
        return _unauthorized_response()

    if request.method == 'GET':
        try:
            libro = get_book_detail(request.user, libro_id)
        except ControlledError as error:
            return _service_error_response(error)
        return JsonResponse(libro)

    if request.method == 'PUT':
        data = _read_json_body(request)
        if data is None:
            return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

        try:
            libro = update_book(request.user, libro_id, data)
        except ControlledError as error:
            return _service_error_response(error)
        return JsonResponse(libro)

    try:
        soft_delete_book(request.user, libro_id)
    except ControlledError as error:
        return _service_error_response(error)
    return JsonResponse({'message': 'Libro eliminado correctamente.'})


@require_http_methods(["GET"])
def api_intercambios(request):
    # Lista intercambios donde participa el usuario (como solicitante o receptor).
    if not request.user.is_authenticated:
        return _unauthorized_response()

    intercambios = (
        Intercambio.objects.filter(
            Q(usuario_solicitante=request.user) | Q(usuario_receptor=request.user),
            activo=True,
        )
        .select_related(
            'usuario_solicitante',
            'usuario_receptor',
            'libro_solicitado',
            'libro_cambio',
        )
        .order_by('-fecha_solicitud')
    )

    resultado = []
    for intercambio in intercambios:
        # Traduce modelo a JSON de lectura simple para la UI.
        es_solicitante = intercambio.usuario_solicitante_id == request.user.id
        contraparte = intercambio.usuario_receptor if es_solicitante else intercambio.usuario_solicitante
        nombre_contraparte = str(contraparte) if contraparte else 'Usuario desconocido'
        libro_solicitado = intercambio.libro_solicitado.titulo if intercambio.libro_solicitado else 'Libro no disponible'
        libro_cambio = intercambio.libro_cambio.titulo if intercambio.libro_cambio else 'Sin seleccionar'

        if intercambio.estado == Intercambio.Estado.PENDIENTE:
            descripcion = f'Pendiente por "{libro_solicitado}".'
        elif intercambio.estado == Intercambio.Estado.ACEPTADO:
            descripcion = f'Aceptado: "{libro_solicitado}" por "{libro_cambio}".'
        elif intercambio.estado == Intercambio.Estado.COMPLETADO:
            descripcion = f'Completado: "{libro_solicitado}" por "{libro_cambio}".'
        else:
            descripcion = f'Estado: {intercambio.estado}.'

        resultado.append({
            'id': intercambio.id,
            'usuario': nombre_contraparte,
            'rolUsuario': 'Solicitante' if es_solicitante else 'Propietario',
            'estado': intercambio.estado,
            'descripcion': descripcion,
            'fecha': intercambio.fecha_solicitud.strftime('%Y-%m-%d %H:%M'),
            'libroSolicitado': libro_solicitado,
            'libroCambio': libro_cambio,
            'pinRequerido': intercambio.estado == Intercambio.Estado.ACEPTADO,
            'yaCompletado': intercambio.estado == Intercambio.Estado.COMPLETADO,
        })

    return JsonResponse(resultado, safe=False)


@require_http_methods(["GET"])
def api_notificaciones(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    notificaciones = (
        Intercambio.objects.filter(
            usuario_receptor=request.user,
            activo=True,
        )
        .select_related('usuario_solicitante', 'libro_solicitado')
        .order_by('-fecha_solicitud')
    )

    resultado = []
    for intercambio in notificaciones:
        solicitante = intercambio.usuario_solicitante
        libro = intercambio.libro_solicitado
        nombre_solicitante = str(solicitante) if solicitante else 'Usuario desconocido'
        titulo_libro = libro.titulo if libro else 'Libro sin titulo'

        if intercambio.estado == Intercambio.Estado.PENDIENTE:
            mensaje = f'{nombre_solicitante} solicito intercambio por tu libro "{titulo_libro}".'
        elif intercambio.estado == Intercambio.Estado.ACEPTADO:
            mensaje = f'Tienes un intercambio aceptado para "{titulo_libro}".'
        elif intercambio.estado == Intercambio.Estado.RECHAZADO:
            mensaje = f'La solicitud por "{titulo_libro}" fue rechazada.'
        else:
            mensaje = f'El intercambio por "{titulo_libro}" fue completado.'

        resultado.append({
            'id': intercambio.id,
            'usuario': nombre_solicitante,
            'libro': titulo_libro,
            'estado': intercambio.estado,
            'mensaje': mensaje,
            'fecha': intercambio.fecha_solicitud.strftime('%Y-%m-%d %H:%M'),
            'esNueva': intercambio.estado == Intercambio.Estado.PENDIENTE,
            'puedeAceptar': intercambio.estado == Intercambio.Estado.PENDIENTE,
        })

    return JsonResponse(resultado, safe=False)


@require_http_methods(["GET"])
def api_inventario_solicitante_intercambio(request, intercambio_id):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    try:
        intercambio = Intercambio.objects.select_related('usuario_receptor', 'usuario_solicitante').get(
            id=intercambio_id,
            activo=True,
        )
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if intercambio.usuario_receptor_id != request.user.id:
        return JsonResponse({'message': 'No tienes permiso para ver este inventario.'}, status=403)

    libros = (
        Libro.objects.filter(
            usuario_propietario=intercambio.usuario_solicitante,
            activo=True,
        )
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )

    return JsonResponse([serialize_book(libro) for libro in libros], safe=False)


@require_http_methods(["POST"])
def api_aceptar_intercambio(request, intercambio_id):
    # El receptor acepta la solicitud, elige libro de cambio y se genera PIN.
    if not request.user.is_authenticated:
        return _unauthorized_response()

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    try:
        intercambio = Intercambio.objects.select_related(
            'usuario_receptor',
            'usuario_solicitante',
            'libro_solicitado',
        ).get(id=intercambio_id, activo=True)
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if intercambio.usuario_receptor_id != request.user.id:
        return JsonResponse({'message': 'No tienes permiso para aceptar este intercambio.'}, status=403)

    if intercambio.estado != Intercambio.Estado.PENDIENTE:
        return JsonResponse({'message': 'Este intercambio ya no esta pendiente.'}, status=400)

    libro_cambio_id = data.get('libroCambioId')
    if not libro_cambio_id:
        return JsonResponse({'message': 'Debes seleccionar un libro del solicitante.'}, status=400)

    try:
        libro_cambio = Libro.objects.get(
            id=libro_cambio_id,
            usuario_propietario=intercambio.usuario_solicitante,
            activo=True,
        )
    except Libro.DoesNotExist:
        return JsonResponse({'message': 'El libro seleccionado no pertenece al solicitante.'}, status=400)

    intercambio.libro_cambio = libro_cambio
    intercambio.estado = Intercambio.Estado.ACEPTADO
    intercambio.fecha_confirmacion = timezone.now()
    # PIN de 6 digitos para confirmar presencialmente el intercambio.
    intercambio.pin_validacion = f'{random.randint(0, 999999):06d}'
    intercambio.save(update_fields=['libro_cambio', 'estado', 'fecha_confirmacion', 'pin_validacion'])

    solicitante = intercambio.usuario_solicitante
    receptor = intercambio.usuario_receptor
    telefono_solicitante = str(solicitante.telefono) if solicitante and solicitante.telefono else ''
    nombre_receptor = str(receptor) if receptor else 'el propietario'
    titulo_solicitado = intercambio.libro_solicitado.titulo if intercambio.libro_solicitado else 'tu libro'
    mensaje_whatsapp = (
        f'Hola {str(solicitante) if solicitante else ""}, '
        f'{nombre_receptor} acepto tu solicitud de intercambio por "{titulo_solicitado}". '
        f'El libro seleccionado para el intercambio es "{libro_cambio.titulo}". '
        f'Tu PIN de validacion es {intercambio.pin_validacion}. Ponganse de acuerdo para continuar.'
    )

    return JsonResponse({
        'message': 'Intercambio aceptado correctamente.',
        'idIntercambio': intercambio.id,
        'libroCambio': libro_cambio.titulo,
        'telefonoWhatsapp': telefono_solicitante,
        'mensajeWhatsapp': mensaje_whatsapp,
        'pinValidacion': intercambio.pin_validacion,
    })


@require_http_methods(["POST"])
def api_confirmar_intercambio_pin(request, intercambio_id):
    # Confirmacion final: valida PIN y realiza intercambio de propietarios en transaccion.
    if not request.user.is_authenticated:
        return _unauthorized_response()

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    try:
        intercambio = Intercambio.objects.select_related(
            'usuario_solicitante',
            'usuario_receptor',
            'libro_solicitado',
            'libro_cambio',
        ).get(id=intercambio_id, activo=True)
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if request.user.id not in {intercambio.usuario_solicitante_id, intercambio.usuario_receptor_id}:
        return JsonResponse({'message': 'No tienes permiso para confirmar este intercambio.'}, status=403)

    if intercambio.estado != Intercambio.Estado.ACEPTADO:
        return JsonResponse({'message': 'Este intercambio no esta listo para confirmacion.'}, status=400)

    pin = str(data.get('pin') or '').strip()
    if not pin:
        return JsonResponse({'message': 'Debes ingresar el PIN de validacion.'}, status=400)

    if pin != (intercambio.pin_validacion or ''):
        return JsonResponse({'message': 'El PIN ingresado no es valido.'}, status=400)

    if not intercambio.libro_solicitado or not intercambio.libro_cambio:
        return JsonResponse({'message': 'El intercambio no tiene ambos libros asignados.'}, status=400)

    if not intercambio.usuario_solicitante or not intercambio.usuario_receptor:
        return JsonResponse({'message': 'El intercambio no tiene usuarios validos para completar.'}, status=400)

    # Atomicidad: o se actualiza todo (libros + intercambio) o no se actualiza nada.
    with transaction.atomic():
        libro_solicitado = intercambio.libro_solicitado
        libro_cambio = intercambio.libro_cambio
        usuario_solicitante = intercambio.usuario_solicitante
        usuario_receptor = intercambio.usuario_receptor

        libro_solicitado.usuario_propietario = usuario_solicitante
        libro_cambio.usuario_propietario = usuario_receptor
        libro_solicitado.save(update_fields=['usuario_propietario'])
        libro_cambio.save(update_fields=['usuario_propietario'])

        intercambio.estado = Intercambio.Estado.COMPLETADO
        intercambio.fecha_completado = timezone.now()
        intercambio.save(update_fields=['estado', 'fecha_completado'])

    return JsonResponse({
        'message': 'Intercambio confirmado correctamente.',
        'idIntercambio': intercambio.id,
    })


@require_http_methods(["POST"])
def api_solicitar_intercambio(request):
    # Crea una solicitud de intercambio delegando reglas de negocio al servicio.
    if not request.user.is_authenticated:
        return _unauthorized_response()

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    try:
        intercambio = request_exchange(request.user, data)
    except ControlledError as error:
        return _service_error_response(error)

    return JsonResponse(intercambio, status=201)
