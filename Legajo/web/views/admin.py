"""
Modulo administrativo: panel, vista de usuarios, carga masiva.

IMPORTANTE:
- Este archivo SI es de vistas de la app (rutas web/API que atienden requests).
- No confundir con web/admin.py, que es solo para el Django Admin nativo.

Endpoints:
- GET /dashboard_admin (panel admin)
- GET/POST /usuarios_admin (carga masiva de usuarios)
- GET/POST /carga_masiva_usuarios (alternativa para carga masiva)
- GET /inventario_admi (inventario admin)
- GET /perfil_admin (perfil del admin)
- GET /api/admin_reported_users (reporte de usuarios reportados)
- GET /api/admin_completed_exchanges (reporte de intercambios completados)
- GET /api/admin_users (lista filtrable de usuarios)
"""
import json
from json import JSONDecodeError

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from ..models import ReporteUsuario, Intercambio
from ..services import import_users_from_payload
from ..validators import ControlledError
from .helpers import (
    _admin_required_response,
    _get_admin_dashboard_context,
    _serialize_admin_user,
    _build_monthly_cumulative_series,
)


User = get_user_model()


# ============================================================================
# VISTAS HTML (PAGES)
# ============================================================================

@login_required(login_url='login')
@never_cache
def dashboard_admin(request):
    """Panel principal del administrador con estadisticas."""
    if request.user.rol != User.Rol.ADMIN:
        return redirect('dashboard_usuario')

    context = _get_admin_dashboard_context()
    context['admin_name'] = request.user.nombre1 or 'Administrador'
    return render(request, 'web/dashboard_admin.html', context)


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
@require_http_methods(["GET", "POST"])
def usuarios_admin(request):
    """
    Vista para carga masiva de usuarios (JSON).
    GET: Renderiza el formulario.
    POST: Procesa archivo JSON y lo importa.
    """
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


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
@require_http_methods(["GET", "POST"])
def carga_masiva_usuarios(request):
    """
    Alternativa para carga masiva de usuarios (con opcion de actualizar existentes).
    GET: Renderiza el formulario.
    POST: Procesa archivo JSON y lo importa.
    """
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


@login_required(login_url='login')
@never_cache
def inventario_admi(request):
    """Inventario de libros desde vista admin."""
    if request.user.rol != User.Rol.ADMIN:
        return redirect('dashboard_usuario')
    return render(request, 'web/inventario_admi.html')


@login_required(login_url='login')
@never_cache
def perfil_admin(request):
    """Perfil del usuario administrador."""
    user = request.user
    return render(request, 'web/perfil_admin.html', {
        'perfil_usuario': user,
        'nombre_completo': ' '.join(filter(None, [user.nombre1, user.nombre2, user.apellido1, user.apellido2])),
    })


# ============================================================================
# API ENDPOINTS (JSON)
# ============================================================================

@login_required(login_url='login')
@require_http_methods(["GET"])
def api_admin_reported_users(request):
    """
    Reporte de usuarios reportados (grafico de linea acumulado mensual).
    GET /api/admin_reported_users/
    """
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
    """
    Reporte de intercambios completados (grafico de linea acumulado mensual).
    GET /api/admin_completed_exchanges/
    """
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
    """
    Lista filtrable de usuarios registrados en el sistema.
    GET /api/admin_users/?nombre=xxx&correo=yyy&ciudad=zzz&rol=ADMIN&estado=activo
    
    Filtros opcionales:
    - nombre
    - correo
    - ciudad
    - rol (ADMIN, USUARIO)
    - estado (activo, inactivo)
    """
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
