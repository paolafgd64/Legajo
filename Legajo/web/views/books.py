"""
Modulo de libros: CRUD, listado, recomendaciones, reportes PDF.
Endpoints:
- GET/POST /api/libros (lista y crea libros del usuario)
- GET /api/libros_recomendados
- GET/PUT/DELETE /api/libro_detalle/<id>
- GET/POST /reporte_libros (carga masiva)
- GET /reporte_libros_pdf (reporte en PDF)
- GET/POST /registrar_libro (formulario para crear/editar)
"""
import json
from json import JSONDecodeError

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from ..models import CalificacionLibro, Libro
from ..services import (
    create_book,
    get_book_detail,
    import_books_from_payload,
    list_books,
    list_recommended_books,
    serialize_book,
    soft_delete_book,
    update_book,
)
from ..validators import ControlledError
from .helpers import (
    _read_json_body,
    _unauthorized_response,
    _service_error_response,
    _forbidden_response,
    _build_pdf_response,
)


User = get_user_model()


# ============================================================================
# VISTAS HTML (PAGES)
# ============================================================================

@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
def registrar_libro(request, libro_id=None):
    """Formulario para registrar o editar un libro del usuario logueado."""
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


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
@require_http_methods(["GET", "POST"])
def reporte_libros(request):
    """
    Panel de administrador: vista de carga misma de libros (JSON).
    GET: Renderiza el formulario.
    POST: Procesa archivo JSON y lo importa.
    """
    if request.user.rol != User.Rol.ADMIN:
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


# ============================================================================
# API ENDPOINTS (JSON)
# ============================================================================

@require_http_methods(["GET", "POST"])
def api_libros(request):
    """
    Libros del usuario: GET lista con filtros; POST registra un libro nuevo.
    
    GET /api/libros/?titulo=xxx&estado=yyy
    
    POST /api/libros/ (multipart/form-data)
    Campos: titulo, autor, genero, sinopsis, estado, imagen (file)
    """
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
    """
    Lista de libros recomendados (libros de otros usuarios).
    GET /api/libros_recomendados/
    """
    if not request.user.is_authenticated:
        return _unauthorized_response()

    try:
        libros = list_recommended_books(request.user)
    except ControlledError as error:
        return _service_error_response(error)
    return JsonResponse(libros, safe=False)


@require_http_methods(["GET", "PUT", "DELETE"])
def api_libro_detalle(request, libro_id):
    """
    CRUD por id: GET detalle, PUT edicion, DELETE borrado logico.
    
    GET /api/libro_detalle/<id>/
    PUT /api/libro_detalle/<id>/
    DELETE /api/libro_detalle/<id>/
    """
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


@login_required(login_url='login')
@require_http_methods(["GET"])
def reporte_libros_pdf(request):
    """
    Genera un PDF con el reporte de libros registrados en el sistema.
    GET /reporte_libros_pdf/?titulo=xxx&autor=yyy&usuario=zzz
    
    Filtros opcionales:
    - titulo
    - autor
    - usuario
    - genero
    - estado
    - calificacion_min
    """
    if request.user.rol != User.Rol.ADMIN:
        return _forbidden_response()

    libros = (
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
        .order_by('-id')
    )

    titulo = (request.GET.get('titulo') or '').strip()
    autor = (request.GET.get('autor') or '').strip()
    usuario = (request.GET.get('usuario') or '').strip()
    genero = (request.GET.get('genero') or '').strip()
    estado = (request.GET.get('estado') or '').strip()
    calificacion_min = (request.GET.get('calificacion_min') or '').strip()

    if titulo:
        libros = libros.filter(titulo__icontains=titulo)
    if autor:
        libros = libros.filter(
            Q(autores__nombre1__icontains=autor) |
            Q(autores__nombre2__icontains=autor) |
            Q(autores__apellido1__icontains=autor) |
            Q(autores__apellido2__icontains=autor) |
            Q(autores__apodo__icontains=autor)
        ).distinct()
    if usuario:
        libros = libros.filter(
            Q(usuario_propietario__nombre1__icontains=usuario) |
            Q(usuario_propietario__nombre2__icontains=usuario) |
            Q(usuario_propietario__apellido1__icontains=usuario) |
            Q(usuario_propietario__apellido2__icontains=usuario) |
            Q(usuario_propietario__email__icontains=usuario)
        ).distinct()
    if genero:
        libros = libros.filter(generos__nombre__icontains=genero).distinct()
    if estado:
        libros = libros.filter(estado__iexact=estado)
    if calificacion_min:
        try:
            libros = libros.filter(promedio_calificacion__gte=float(calificacion_min))
        except ValueError:
            pass

    libros = libros.distinct()

    filtros = {
        'Titulo': titulo or 'Todos',
        'Autor': autor or 'Todos',
        'Usuario': usuario or 'Todos',
        'Genero': genero or 'Todos',
        'Estado': estado or 'Todos',
        'Calificacion minima': f'{calificacion_min}/5' if calificacion_min else 'Sin restriccion',
    }

    total_libros = libros.count()
    total_usuarios = (
        libros.exclude(usuario_propietario_id__isnull=True)
        .values('usuario_propietario_id')
        .distinct()
        .count()
    )
    total_generos = (
        libros.exclude(generos__id__isnull=True)
        .values('generos__id')
        .distinct()
        .count()
    )

    calificaciones = CalificacionLibro.objects.filter(activo=True, libro__in=libros)
    resumen_calificaciones = calificaciones.aggregate(
        promedio=Avg('calificacion'),
        total=Count('id'),
    )

    consulta_estados = list(
        libros.values('estado')
        .annotate(total=Count('id'))
        .order_by('-total', 'estado')
    )
    consulta_generos = list(
        libros.exclude(generos__nombre__isnull=True)
        .values('generos__nombre')
        .annotate(total=Count('id'))
        .order_by('-total', 'generos__nombre')[:5]
    )
    consulta_usuarios = list(
        libros.exclude(usuario_propietario_id__isnull=True)
        .values(
            'usuario_propietario__nombre1',
            'usuario_propietario__nombre2',
            'usuario_propietario__apellido1',
            'usuario_propietario__apellido2',
            'usuario_propietario__email',
        )
        .annotate(total=Count('id'))
        .order_by('-total', 'usuario_propietario__nombre1', 'usuario_propietario__apellido1')[:5]
    )
    distribucion_calificaciones = list(
        calificaciones.values('calificacion')
        .annotate(total=Count('id'))
        .order_by('-calificacion')
    )

    genero_dominante = consulta_generos[0] if consulta_generos else None
    estado_dominante = consulta_estados[0] if consulta_estados else None
    usuario_mayor_inventario = consulta_usuarios[0] if consulta_usuarios else None
    promedio_calificacion = resumen_calificaciones['promedio'] or 0

    hallazgos = [
        (
            f"Se analizaron {total_libros} libros publicados por {total_usuarios} usuarios activos "
            f"bajo los filtros configurados."
        )
    ]
    if genero_dominante:
        hallazgos.append(
            f"El genero con mayor presencia es {genero_dominante['generos__nombre']} "
            f"con {genero_dominante['total']} registros."
        )
    if estado_dominante:
        hallazgos.append(
            f"El estado predominante es {estado_dominante['estado']} con {estado_dominante['total']} libros, "
            "lo que ayuda a identificar disponibilidad real del inventario."
        )
    if usuario_mayor_inventario:
        nombre_usuario = ' '.join(
            filter(
                None,
                [
                    usuario_mayor_inventario['usuario_propietario__nombre1'],
                    usuario_mayor_inventario['usuario_propietario__nombre2'],
                    usuario_mayor_inventario['usuario_propietario__apellido1'],
                    usuario_mayor_inventario['usuario_propietario__apellido2'],
                ],
            )
        ).strip() or usuario_mayor_inventario['usuario_propietario__email']
        hallazgos.append(
            f"El usuario con mayor inventario en la consulta es {nombre_usuario} "
            f"con {usuario_mayor_inventario['total']} libros."
        )
    if resumen_calificaciones['total']:
        hallazgos.append(
            f"La calificacion promedio de los libros filtrados es {promedio_calificacion:.1f}/5 "
            f"basada en {resumen_calificaciones['total']} resenas activas."
        )
    else:
        hallazgos.append(
            "No hay resenas activas en el subconjunto filtrado, por lo que conviene incentivar calificaciones "
            "para fortalecer el analisis de satisfaccion."
        )

    report_context = {
        'filters_lines': [f'{clave}: {valor}' for clave, valor in filtros.items()],
        'summary_cards': [
            {'label': 'Libros filtrados', 'value': str(total_libros)},
            {'label': 'Usuarios involucrados', 'value': str(total_usuarios)},
            {'label': 'Generos presentes', 'value': str(total_generos)},
            {
                'label': 'Promedio calificacion',
                'value': f'{promedio_calificacion:.1f}/5' if resumen_calificaciones['total'] else 'Sin datos',
            },
        ],
        'stat_sections': [
            {
                'title': 'Consulta estadistica por estado',
                'headers': ['Estado', 'Total'],
                'rows': [[item['estado'], item['total']] for item in consulta_estados],
            },
            {
                'title': 'Consulta estadistica por genero',
                'headers': ['Genero', 'Total'],
                'rows': [[item['generos__nombre'], item['total']] for item in consulta_generos],
            },
            {
                'title': 'Consulta estadistica por usuario',
                'headers': ['Usuario', 'Total libros'],
                'rows': [[
                    ' '.join(
                        filter(
                            None,
                            [
                                item['usuario_propietario__nombre1'],
                                item['usuario_propietario__nombre2'],
                                item['usuario_propietario__apellido1'],
                                item['usuario_propietario__apellido2'],
                            ],
                        )
                    ).strip() or item['usuario_propietario__email'],
                    item['total'],
                ] for item in consulta_usuarios],
            },
            {
                'title': 'Consulta estadistica de calificaciones',
                'headers': ['Estrellas', 'Total resenas'],
                'rows': [[f"{item['calificacion']}/5", item['total']] for item in distribucion_calificaciones],
            },
        ],
        'insights': hallazgos,
    }

    rows = []
    for libro in libros:
        serialized = serialize_book(libro)
        rows.append([
            serialized['usuario'],
            serialized['titulo'],
            serialized['autor'],
            serialized['genero'],
            serialized['estado'],
            f"{serialized['calificacion']:.1f}/5" if serialized['totalCalificaciones'] else 'Sin resenas',
        ])

    return _build_pdf_response(
        'Reporte analitico de libros registrados',
        rows,
        'reporte_libros.pdf',
        report_context=report_context,
        columns=[
            ('Usuario', 102),
            ('Titulo', 140),
            ('Autor', 108),
            ('Genero', 82),
            ('Estado', 58),
            ('Calif.', 50),
        ],
    )
