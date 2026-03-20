from django.shortcuts import render
from django.http import JsonResponse

# Create your views here.
def index(request):
    return render(request, 'web/index.html')

def chats(request):
    return render(request, 'web/chats.html')

def crear_cuenta(request):
    return render(request, 'web/crear_cuenta.html')

def dashboard_admin(request):
    return render(request, 'web/dashboard_admin.html')

def dashboard_usuario(request):
    return render(request, 'web/dashboard_usuario.html')

def forgot_password(request):
    return render(request, 'web/forgot_password.html')

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

def api_usuarios(request):
    if request.method == 'POST':
        return JsonResponse({'mensaje': 'Usuario registrado correctamente'})

