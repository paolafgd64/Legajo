import json

from django.contrib.auth import authenticate, get_user_model, login as auth_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
<<<<<<< HEAD
import json
from django.http import JsonResponse
import json
from django.http import JsonResponse
from django.http import JsonResponse








=======
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
>>>>>>> 00e45309638ed4bf1e4ae15a6b5121f5aa5736dd

# Create your views here.
User = get_user_model()


def index(request):
    return render(request, 'web/index.html')

def api_usuarios(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        print(data)  # 👈 para ver en consola

        return JsonResponse({
            'mensaje': 'Usuario registrado correctamente'
        })

def chats(request):
    return render(request, 'web/chats.html')

def crear_cuenta(request):
    return render(request, 'web/crear_cuenta.html')

def dashboard_admin(request):
    return render(request, 'web/dashboard_admin.html')

def dashboard_usuario(request):
    return render(request, 'web/dashboard_usuario.html')

def forgot_password(request):
    return render(request, 'web/forgot-password.html')

def inventario_admi(request):
    return render(request, 'web/inventario_admi.html')

def inventario(request):
    return render(request, 'web/inventario.html')

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

def registrar_libro(request):
    return render(request, 'web/registrar_libro.html')

def reporte_libros(request):
    return render(request, 'web/reporte_libros.html')

def reset_password(request):
    return render(request, 'web/reset_password.html')

<<<<<<< HEAD
def api_usuarios(request):
    if request.method == 'POST':
        return JsonResponse({'mensaje': 'Usuario registrado correctamente'})
    
def api_login(request):
    if request.method == 'POST':
        data = json.loads(request.body)
=======
def _read_json_body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


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
    })
>>>>>>> 00e45309638ed4bf1e4ae15a6b5121f5aa5736dd

        correo = data.get('correo')
        clave = data.get('clave')

        # 🔥 LOGIN SIMULADO (luego lo hacemos real)
        if correo == 'admin@gmail.com' and clave == '123':
            return JsonResponse({
                'mensaje': 'Login exitoso',
                'token': 'fake-jwt-token',
                'role': 'admin'
            })

        elif correo == 'user@gmail.com' and clave == '123':
            return JsonResponse({
                'mensaje': 'Login exitoso',
                'token': 'fake-jwt-token',
                'role': 'usuario'
            })

        else:
            return JsonResponse({
                'error': 'Credenciales inválidas'
            }, status=400)

def api_me(request):
    # Simulación por ahora
    return JsonResponse({
        'primerNombre': 'David',
        'rol': 'admin'
    })
