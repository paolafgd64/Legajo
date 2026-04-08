"""
Modulo de dashboard y vistas UI: paginas que solo renderizan templates.
Views:
- GET /index (homepage)
- GET /chats (chat del usuario)
- GET /dashboard_usuario (dashboard usuario regular)
- GET /notificaciones (campana de notificaciones)
- GET /novedades_usuarios (novedades)
- GET /perfil (perfil del usuario)
- GET /inventario (inventario del usuario)
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from ..models import Libro, ReporteUsuario
from ..services import serialize_book
from .helpers import _admin_required_response, _read_json_body, _unauthorized_response


User = get_user_model()


# ============================================================================
# VISTAS HTML (PAGES) - Solo renderizado, sin logica de negocio
# ============================================================================

def index(request):
    """Homepage publica."""
    return render(request, 'web/index.html')


@login_required(login_url='login')
@never_cache
def chats(request):
    """Pagina de chats del usuario (requiere autenticacion)."""
    return render(request, 'web/chats.html')


@login_required(login_url='login')
@never_cache
def dashboard_usuario(request):
    """
    Dashboard del usuario regular: muestra libros recomendados.
    GET /dashboard_usuario/
    """
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
@login_required(login_url='login')
@never_cache
def notificaciones(request):
    """Pagina de notificaciones del usuario."""
    return render(request, 'web/notificaciones.html')


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
def novedades_usuarios(request):
    """Vista administrativa para gestionar reportes de usuarios."""
    admin_error = _admin_required_response(request)
    if admin_error:
        return redirect('dashboard_usuario')
    return render(request, 'web/novedades_usuarios.html', {
        'admin_name': request.user.nombre1 or 'Administrador',
    })


@login_required(login_url='login')
@never_cache
def perfil(request):
    """Perfil del usuario regular."""
    user = request.user
    return render(request, 'web/perfil.html', {
        'perfil_usuario': user,
        'nombre_completo': ' '.join(filter(None, [user.nombre1, user.nombre2, user.apellido1, user.apellido2])),
    })


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
def inventario(request):
    """Inventario de libros del usuario."""
    return render(request, 'web/inventario.html')


@login_required(login_url='login')
@require_http_methods(["GET", "POST"])
def api_user_reports(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    if request.method == 'GET':
        reportes = (
            ReporteUsuario.objects.filter(usuario_reportante=request.user, activo=True)
            .select_related('usuario_reportado')
            .order_by('-fecha_reporte')
        )
        return JsonResponse([
            {
                'id': reporte.id,
                'motivo': reporte.motivo,
                'descripcion': reporte.descripcion,
                'estado': reporte.estado,
                'usuarioReportado': str(reporte.usuario_reportado) if reporte.usuario_reportado else 'Usuario desconocido',
                'fechaReporte': reporte.fecha_reporte.strftime('%Y-%m-%d %H:%M') if reporte.fecha_reporte else '',
            }
            for reporte in reportes
        ], safe=False)

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    usuario_reportado_id = data.get('usuarioReportadoId')
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

    reporte_existente = ReporteUsuario.objects.filter(
        activo=True,
        usuario_reportante=request.user,
        usuario_reportado=usuario_reportado,
        motivo__iexact=motivo,
        estado=ReporteUsuario.Estado.PENDIENTE,
    ).exists()
    if reporte_existente:
        return JsonResponse({'message': 'Ya tienes un reporte pendiente para este usuario con ese motivo.'}, status=400)

    reporte = ReporteUsuario.objects.create(
        motivo=motivo,
        descripcion=descripcion,
        estado=ReporteUsuario.Estado.PENDIENTE,
        usuario_reportante=request.user,
        usuario_reportado=usuario_reportado,
    )

    return JsonResponse({
        'message': 'Reporte enviado correctamente. El equipo administrador lo revisara.',
        'reporteId': reporte.id,
        'estado': reporte.estado,
    }, status=201)
