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
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache

from ..models import Libro
from ..services import serialize_book


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


def novedades_usuarios(request):
    """Pagina publica de novedades."""
    return render(request, 'web/novedades_usuarios.html')


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
