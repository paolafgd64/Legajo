"""
Modulo de autenticacion: registro, login, logout, recuperacion de contraseña.
Endpoints:
- POST /api/usuarios (registro)
- POST /api/login
- GET/PUT /api/me (perfil del usuario)
- GET/POST /forgot_password
- GET/POST /reset_password
"""
import json
from json import JSONDecodeError

from django.contrib.auth import authenticate, get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from ..validators import ControlledError
from .helpers import (
    _read_json_body,
    _unauthorized_response,
    _normalize_validation_messages,
    _build_password_reset_link,
    _get_password_reset_user,
)


User = get_user_model()


# ============================================================================
# VISTAS HTML (PAGES)
# ============================================================================

@ensure_csrf_cookie
def crear_cuenta(request):
    """Solo renderiza la pagina de registro. La creacion real ocurre en api_usuarios."""
    return render(request, 'web/crear_cuenta.html')


@ensure_csrf_cookie
def login(request):
    """Renderiza pagina de login."""
    return render(request, 'web/login.html')


@login_required(login_url='login')
@never_cache
@require_http_methods(["POST"])
def logout_view(request):
    """Cierra sesion del usuario autenticado."""
    auth_logout(request)
    response = redirect('index')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def forgot_password(request):
    """Solicita enlace de recuperacion de contraseña por correo."""
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
        if user:
            from django.conf import settings
            if settings.DEBUG:
                context['reset_link'] = _build_password_reset_link(request, user)

    return render(request, 'web/forgot-password.html', context)


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def reset_password(request):
    """Valida token y permite restableter contrasena."""
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
        return redirect(f"{request.build_absolute_uri('/login/')}?reset=success")

    return render(request, 'web/reset_password.html', context)


# ============================================================================
# API ENDPOINTS (JSON)
# ============================================================================

@require_http_methods(["POST"])
def api_usuarios(request):
    """
    Endpoint de registro: valida payload, crea usuario y guarda hash de contrasena.
    
    POST /api/usuarios
    Body:
        {
            "correo": "email@example.com",
            "primerNombre": "Juan",
            "primerApellido": "Perez",
            "clave": "contraseña123456",
            "ciudad": "Bogota",
            "telefono": "3015874123"
        }
    """
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
    """
    Login por correo+contrasena usando el backend de autenticacion de Django.
    
    POST /api/login
    Body:
        {
            "correo": "email@example.com",
            "clave": "contraseña123456"
        }
    """
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
    """
    Perfil del usuario logueado: GET consulta, PUT actualiza datos.
    
    GET /api/me/ (requiere autenticacion)
    
    PUT /api/me/
    Body:
        {
            "correo": "newemail@example.com",
            "primerNombre": "Nuevo",
            "ciudad": "Medellin"
        }
    """
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
