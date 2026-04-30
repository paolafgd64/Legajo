"""Vistas del modulo de usuarios.

Aqui viven:
- autenticacion y recuperacion de contrasena
- perfil del usuario autenticado
- dashboard y vistas HTML del usuario final
- reportes que un usuario envia a administracion
"""

from django.contrib.auth import authenticate, get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from ..administracion.models import ReporteUsuario
from ..gestion_libros.models import Libro
from ..services import list_recommended_books
from ..views.helpers import (
    _build_account_activation_link,
    _build_password_reset_link,
    _get_password_reset_user,
    _normalize_validation_messages,
    _read_json_body,
    _send_account_activation_email,
    _send_password_reset_email,
    _unauthorized_response,
)


User = get_user_model()


def index(request):
    return render(request, 'usuarios/index.html')


@ensure_csrf_cookie
def crear_cuenta(request):
    return render(request, 'usuarios/crear_cuenta.html')


@ensure_csrf_cookie
def login(request):
    return render(request, 'usuarios/login.html')


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
@require_http_methods(["GET", "POST"])
def forgot_password(request):
    context = {}

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        context['submitted_email'] = email

        if not email:
            context['error_message'] = 'Debes ingresar un correo electronico.'
            return render(request, 'usuarios/forgot-password.html', context, status=400)

        try:
            user = User.objects.get(email=email, activo=True, is_active=True)
        except User.DoesNotExist:
            user = None

        context['success_message'] = 'Si el correo existe en Legajo, ya generamos un enlace para restablecer la contrasena.'
        if user:
            try:
                _send_password_reset_email(request, user)
            except Exception:
                if settings.DEBUG:
                    context['reset_link'] = _build_password_reset_link(request, user)
                    context['error_message'] = 'No se pudo enviar el correo en este entorno. Usa temporalmente el enlace generado abajo.'
                else:
                    context['error_message'] = 'No fue posible enviar el correo en este momento. Intenta de nuevo.'
                    return render(request, 'usuarios/forgot-password.html', context, status=500)

    return render(request, 'usuarios/forgot-password.html', context)


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def reset_password(request):
    uid = (request.GET.get('uid') or request.POST.get('uid') or '').strip()
    token = (request.GET.get('token') or request.POST.get('token') or '').strip()
    user = _get_password_reset_user(uid) if uid else None

    from django.contrib.auth.tokens import default_token_generator
    token_is_valid = bool(user and token and default_token_generator.check_token(user, token))

    context = {
        'uid': uid,
        'token': token,
        'token_is_valid': token_is_valid,
    }

    if request.method == 'POST':
        if not token_is_valid:
            context['error_message'] = 'El enlace de recuperacion no es valido o ya vencio.'
            return render(request, 'usuarios/reset_password.html', context, status=400)

        password = request.POST.get('password') or ''
        confirm_password = request.POST.get('confirmPassword') or ''

        if not password or not confirm_password:
            context['error_message'] = 'Debes completar ambos campos de contrasena.'
            return render(request, 'usuarios/reset_password.html', context, status=400)

        if password != confirm_password:
            context['error_message'] = 'Las contrasenas no coinciden.'
            return render(request, 'usuarios/reset_password.html', context, status=400)

        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            context['error_message'] = _normalize_validation_messages(exc.messages)
            return render(request, 'usuarios/reset_password.html', context, status=400)

        user.set_password(password)
        user.save(update_fields=['password'])
        return redirect('/login/?reset=success')

    return render(request, 'usuarios/reset_password.html', context)


@require_http_methods(["GET"])
def activate_account(request, uidb64, token):
    user = None
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id, activo=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])
        return redirect('/login/?activated=success')

    return redirect('/login/?activated=invalid')


@login_required(login_url='login')
@never_cache
def chats(request):
    return render(request, 'usuarios/chats.html')


@login_required(login_url='login')
@never_cache
def dashboard_usuario(request):
    # El dashboard reutiliza el serializer de libros para que la UI consuma
    # el mismo formato que los endpoints JSON.
    libros_serializados = list_recommended_books(request.user)
    return render(
        request,
        'usuarios/dashboard_usuario.html',
        {
            'libros_recomendados': libros_serializados[:8],
            'libros_generos': [],
            'total_libros_sistema': Libro.objects.filter(activo=True).count(),
            'total_libros_ajenos': len(libros_serializados),
        },
    )


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
def notificaciones(request):
    return render(request, 'intercambios/notificaciones.html')


@login_required(login_url='login')
@never_cache
def perfil(request):
    user = request.user
    return render(request, 'usuarios/perfil.html', {
        'perfil_usuario': user,
        'nombre_completo': ' '.join(filter(None, [user.nombre1, user.nombre2, user.apellido1, user.apellido2])),
    })


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
def inventario(request):
    return render(request, 'gestion_libros/inventario.html')


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

    existing_user = User.objects.filter(email=email).first()
    if existing_user and existing_user.is_active and existing_user.activo:
        return JsonResponse({'message': 'Ya existe un usuario registrado con ese correo.'}, status=400)

    telefono = str(data.get('telefono')).strip()
    if not telefono.isdigit():
        return JsonResponse({'message': 'El telefono debe contener solo numeros.'}, status=400)

    user = existing_user or User(email=email)
    user.nombre1 = data.get('primerNombre', '').strip()
    user.nombre2 = (data.get('segundoNombre') or '').strip() or None
    user.apellido1 = data.get('primerApellido', '').strip()
    user.apellido2 = (data.get('segundoApellido') or '').strip() or None
    user.direccion = data.get('direccion', '').strip()
    user.ciudad = data.get('ciudad', '').strip()
    user.telefono = int(telefono)
    user.rol = User.Rol.USUARIO
    user.is_active = False
    user.activo = True

    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return JsonResponse({'message': _normalize_validation_messages(exc.messages)}, status=400)

    user.set_password(password)
    user.save()

    try:
        _send_account_activation_email(request, user)
    except Exception:
        if settings.DEBUG:
            return JsonResponse(
                {
                    'mensaje': 'Usuario registrado. No se pudo enviar correo en este entorno; usa el enlace de activacion temporal.',
                    'activation_link': _build_account_activation_link(request, user),
                },
                status=201,
            )
        return JsonResponse(
            {'message': 'No fue posible enviar el correo de activacion. Intenta registrarte de nuevo.'},
            status=500,
        )

    return JsonResponse({'mensaje': 'Usuario registrado. Revisa tu correo para activar la cuenta.'}, status=201)


@require_http_methods(["POST"])
def api_login(request):
    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    email = (data.get('correo') or '').strip().lower()
    password = data.get('clave') or ''

    if not email or not password:
        return JsonResponse({'message': 'Correo y contrasena son obligatorios.'}, status=400)

    usuario_encontrado = User.objects.filter(email=email).first()
    if usuario_encontrado and usuario_encontrado.check_password(password):
        motivo_desactivacion = (usuario_encontrado.motivo_desactivacion or '').strip()
        if not usuario_encontrado.is_active or not getattr(usuario_encontrado, 'activo', True):
            if motivo_desactivacion:
                return JsonResponse({
                    'message': 'Tu cuenta fue desactivada por administracion.',
                    'reason': motivo_desactivacion,
                    'code': 'account_disabled',
                    'landingUrl': '/',
                }, status=403)
            return JsonResponse({'message': 'Tu cuenta esta inactiva. Revisa tu correo y activa tu cuenta.'}, status=403)

    user = authenticate(request, email=email, password=password)
    if user is None:
        return JsonResponse({'message': 'Credenciales invalidas.'}, status=401)

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


@login_required(login_url='login')
@require_http_methods(["GET", "POST"])
def api_user_reports(request):
    if request.method == 'GET':
        reportes = (
            ReporteUsuario.objects.filter(usuario_reportante=request.user, activo=True)
            .select_related('usuario_reportado', 'libro_reportado')
            .order_by('-fecha_reporte')
        )
        return JsonResponse([
            {
                'id': reporte.id,
                'motivo': reporte.motivo,
                'descripcion': reporte.descripcion,
                'estado': reporte.estado,
                'usuarioReportado': str(reporte.usuario_reportado) if reporte.usuario_reportado else 'Usuario desconocido',
                'libroReportado': reporte.libro_reportado.titulo if reporte.libro_reportado else '',
                'libroReportadoId': reporte.libro_reportado_id,
                'fechaReporte': reporte.fecha_reporte.strftime('%Y-%m-%d %H:%M') if reporte.fecha_reporte else '',
            }
            for reporte in reportes
        ], safe=False)

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    usuario_reportado_id = data.get('usuarioReportadoId')
    libro_reportado_id = data.get('libroReportadoId')
    motivo = str(data.get('motivo') or '').strip()
    descripcion = str(data.get('descripcion') or '').strip()

    if not usuario_reportado_id:
        return JsonResponse({'message': 'Debes indicar a que usuario deseas reportar.'}, status=400)
    if not motivo:
        return JsonResponse({'message': 'Debes seleccionar o escribir el motivo del reporte.'}, status=400)
    if len(descripcion) < 10:
        return JsonResponse({'message': 'Describe mejor lo ocurrido. Minimo 10 caracteres.'}, status=400)

    try:
        usuario_reportado = User.objects.get(id=usuario_reportado_id, activo=True, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'message': 'El usuario reportado no existe o ya no esta disponible.'}, status=404)

    if usuario_reportado.id == request.user.id:
        return JsonResponse({'message': 'No puedes reportarte a ti mismo.'}, status=400)

    libro_reportado = None
    if libro_reportado_id:
        try:
            libro_reportado = Libro.objects.get(
                id=libro_reportado_id,
                usuario_propietario=usuario_reportado,
            )
        except Libro.DoesNotExist:
            return JsonResponse({'message': 'El libro reportado no pertenece al usuario indicado.'}, status=400)

    reporte_existente = ReporteUsuario.objects.filter(
        activo=True,
        usuario_reportante=request.user,
        usuario_reportado=usuario_reportado,
        libro_reportado=libro_reportado,
        motivo__iexact=motivo,
        estado=ReporteUsuario.Estado.PENDIENTE,
    ).exists()
    if reporte_existente:
        return JsonResponse({'message': 'Ya tienes un reporte pendiente para este usuario con ese motivo.'}, status=400)

    reporte = ReporteUsuario.objects.create(
        # El reporte queda pendiente hasta revision administrativa.
        motivo=motivo,
        descripcion=descripcion,
        estado=ReporteUsuario.Estado.PENDIENTE,
        usuario_reportante=request.user,
        usuario_reportado=usuario_reportado,
        libro_reportado=libro_reportado,
    )

    return JsonResponse({
        'message': 'Reporte enviado correctamente. El equipo administrador lo revisara.',
        'reporteId': reporte.id,
        'estado': reporte.estado,
    }, status=201)
