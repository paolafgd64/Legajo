"""Vistas del modulo de gestion de libros."""

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.http.multipartparser import MultiPartParser, MultiPartParserError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from ..administracion.models import NotificacionUsuario
from ..services import (
    create_book_copies,
    get_book_detail,
    list_books,
    list_recommended_books,
    serialize_book,
    soft_delete_book,
    update_book,
)
from ..validators import ControlledError
from ..views.helpers import (
    _build_pdf_response,
    _forbidden_response,
    _read_json_body,
    _service_error_response,
    _unauthorized_response,
)
from .models import CalificacionLibro, Libro


User = get_user_model()


def _read_update_payload(request):
    content_type = request.content_type or ''
    if content_type.startswith('multipart/form-data'):
        try:
            parser = MultiPartParser(request.META, request, request.upload_handlers, request.encoding)
            data, files = parser.parse()
            return data, files
        except MultiPartParserError:
            return None, None

    data = _read_json_body(request)
    if data is None:
        return None, None
    return data, None


def _count_matching_active_book_copies(libro):
    author_ids = set(libro.autores.values_list('id', flat=True))
    genre_ids = set(libro.generos.values_list('id', flat=True))
    candidates = (
        Libro.objects.filter(
            activo=True,
            titulo=libro.titulo,
            sinopsis=libro.sinopsis,
            estado=libro.estado,
            url_imagen=libro.url_imagen,
            usuario_propietario=libro.usuario_propietario,
        )
        .prefetch_related('autores', 'generos')
    )

    return sum(
        1
        for candidate in candidates
        if set(candidate.autores.values_list('id', flat=True)) == author_ids
        and set(candidate.generos.values_list('id', flat=True)) == genre_ids
    )


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
def registrar_libro(request, libro_id=None):
    if request.user.rol == User.Rol.ADMIN:
        return redirect('dashboard_admin')

    source = (request.GET.get('source') or request.POST.get('source') or '').strip().lower()
    context = {
        'source': source,
        'back_url_name': 'inventario',
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
            'stock': _count_matching_active_book_copies(libro),
        }

    return render(request, 'gestion_libros/registrar_libro.html', context)


@ensure_csrf_cookie
@login_required(login_url='login')
@never_cache
@require_http_methods(["GET"])
def reporte_libros(request):
    if request.user.rol != User.Rol.ADMIN:
        return redirect('dashboard_usuario') if request.user.is_authenticated else redirect('login')

    context = {
        'admin_name': request.user.nombre1 or 'Administrador',
        'url_portada_predeterminada': '/static/gestion_libros/imgs/libropredeterminado1.png',
    }
    return render(request, 'gestion_libros/reporte_libros.html', context)


def _admin_books_report_queryset():
    return (
        Libro.objects.all()
        .select_related('usuario_propietario')
        .prefetch_related('autores', 'generos')
        .annotate(
            promedio_calificacion=Avg('calificacionlibro__calificacion', filter=Q(calificacionlibro__activo=True), distinct=True),
            total_calificaciones=Count('calificacionlibro', filter=Q(calificacionlibro__activo=True), distinct=True),
        )
    )


def _filter_books_report_queryset(libros, request):
    titulo = (request.GET.get('titulo') or '').strip()
    autor = (request.GET.get('autor') or '').strip()
    usuario = (request.GET.get('usuario') or '').strip()
    genero = (request.GET.get('genero') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    if titulo:
        libros = libros.filter(titulo__icontains=titulo)
    if autor:
        libros = libros.filter(
            Q(autores__nombre1__icontains=autor) |
            Q(autores__nombre2__icontains=autor) |
            Q(autores__apellido1__icontains=autor) |
            Q(autores__apellido2__icontains=autor) |
            Q(autores__apodo__icontains=autor)
        )
    if usuario:
        libros = libros.filter(
            Q(usuario_propietario__nombre1__icontains=usuario) |
            Q(usuario_propietario__nombre2__icontains=usuario) |
            Q(usuario_propietario__apellido1__icontains=usuario) |
            Q(usuario_propietario__apellido2__icontains=usuario) |
            Q(usuario_propietario__email__icontains=usuario)
        )
    if genero:
        libros = libros.filter(generos__nombre__icontains=genero)
    if estado:
        libros = libros.filter(estado__iexact=estado)

    return libros.distinct()


@login_required(login_url='login')
@require_http_methods(["GET"])
def api_admin_libros_reporte(request):
    if request.user.rol != User.Rol.ADMIN:
        return _forbidden_response()

    libros = _filter_books_report_queryset(_admin_books_report_queryset(), request).order_by('-id')
    return JsonResponse([serialize_book(libro) for libro in libros], safe=False)


@login_required(login_url='login')
@require_http_methods(["PATCH"])
def api_admin_actualizar_estado_libro(request, libro_id):
    if request.user.rol != User.Rol.ADMIN:
        return _forbidden_response()

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    activo = data.get('activo')
    if not isinstance(activo, bool):
        return JsonResponse({'message': 'El estado enviado no es valido.'}, status=400)

    try:
        libro = Libro.objects.select_related('usuario_propietario').prefetch_related('autores', 'generos').get(id=libro_id)
    except Libro.DoesNotExist:
        return JsonResponse({'message': 'Libro no encontrado.'}, status=404)

    motivo = str(data.get('motivo') or '').strip()
    if not activo and len(motivo) < 10:
        return JsonResponse({'message': 'Debes escribir un motivo de al menos 10 caracteres.'}, status=400)

    libro.activo = activo
    libro.save(update_fields=['activo', 'fecha_actualizacion'])

    propietario = libro.usuario_propietario
    if propietario:
        if activo:
            mensaje = f'Tu libro "{libro.titulo}" fue activado nuevamente por el equipo administrador.'
        else:
            mensaje = f'Tu libro "{libro.titulo}" fue desactivado por el equipo administrador. Motivo: {motivo}'
        NotificacionUsuario.objects.create(usuario=propietario, mensaje=mensaje)

    return JsonResponse({
        'message': 'Libro activado correctamente.' if activo else 'Libro desactivado correctamente.',
        'libro': serialize_book(libro),
    })


@require_http_methods(["GET", "POST"])
def api_libros(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    if request.method == 'GET':
        try:
            libros = list_books(request.user, request.GET)
        except ControlledError as error:
            return _service_error_response(error)
        return JsonResponse(libros, safe=False)

    if request.user.rol == User.Rol.ADMIN:
        return _forbidden_response('Los administradores no pueden registrar libros para intercambio.')

    try:
        # La creacion valida y persiste relaciones en la capa de servicios.
        libro = create_book_copies(request.user, request.POST, image_file=request.FILES.get('imagen'))
    except ControlledError as error:
        return _service_error_response(error)

    return JsonResponse(libro, status=201, safe=False)


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
    if not request.user.is_authenticated:
        return _unauthorized_response()

    if request.method == 'GET':
        try:
            libro = get_book_detail(request.user, libro_id)
        except ControlledError as error:
            return _service_error_response(error)
        return JsonResponse(libro)

    if request.method == 'PUT':
        if request.user.rol == User.Rol.ADMIN:
            return _forbidden_response('Los administradores no pueden editar libros de intercambio.')

        data, files = _read_update_payload(request)
        if data is None:
            return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

        try:
            libro = update_book(request.user, libro_id, data, image_file=files.get('imagen') if files else None)
        except ControlledError as error:
            return _service_error_response(error)
        return JsonResponse(libro)

    if request.user.rol == User.Rol.ADMIN:
        return _forbidden_response('Los administradores no pueden eliminar libros de intercambio.')

    try:
        soft_delete_book(request.user, libro_id)
    except ControlledError as error:
        return _service_error_response(error)
    return JsonResponse({'message': 'Libro eliminado correctamente.'})


@login_required(login_url='login')
@require_http_methods(["GET"])
def reporte_libros_pdf(request):
    if request.user.rol != User.Rol.ADMIN:
        return _forbidden_response()

    libros = (
        Libro.objects.all()
        .select_related('usuario_propietario')
        .prefetch_related('autores', 'generos')
        .annotate(
            promedio_calificacion=Avg('calificacionlibro__calificacion', filter=Q(calificacionlibro__activo=True), distinct=True),
            total_calificaciones=Count('calificacionlibro', filter=Q(calificacionlibro__activo=True), distinct=True),
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
    total_usuarios = libros.exclude(usuario_propietario_id__isnull=True).values('usuario_propietario_id').distinct().count()
    total_generos = libros.exclude(generos__id__isnull=True).values('generos__id').distinct().count()

    calificaciones = CalificacionLibro.objects.filter(activo=True, libro__in=libros)
    resumen_calificaciones = calificaciones.aggregate(promedio=Avg('calificacion'), total=Count('id'))
    consulta_estados = list(libros.values('estado').annotate(total=Count('id')).order_by('-total', 'estado'))
    consulta_generos = list(
        libros.exclude(generos__nombre__isnull=True).values('generos__nombre').annotate(total=Count('id')).order_by('-total', 'generos__nombre')[:5]
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
    distribucion_calificaciones = list(calificaciones.values('calificacion').annotate(total=Count('id')).order_by('-calificacion'))

    genero_dominante = consulta_generos[0] if consulta_generos else None
    estado_dominante = consulta_estados[0] if consulta_estados else None
    usuario_mayor_inventario = consulta_usuarios[0] if consulta_usuarios else None
    promedio_calificacion = resumen_calificaciones['promedio'] or 0

    hallazgos = [f"Se analizaron {total_libros} libros publicados por {total_usuarios} usuarios activos bajo los filtros configurados."]
    if genero_dominante:
        hallazgos.append(f"El genero con mayor presencia es {genero_dominante['generos__nombre']} con {genero_dominante['total']} registros.")
    if estado_dominante:
        hallazgos.append(
            f"El estado predominante es {estado_dominante['estado']} con {estado_dominante['total']} libros, lo que ayuda a identificar disponibilidad real del inventario."
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
        hallazgos.append(f"El usuario con mayor inventario en la consulta es {nombre_usuario} con {usuario_mayor_inventario['total']} libros.")
    if resumen_calificaciones['total']:
        hallazgos.append(
            f"La calificacion promedio de los libros filtrados es {promedio_calificacion:.1f}/5 basada en {resumen_calificaciones['total']} resenas activas."
        )
    else:
        hallazgos.append(
            'No hay resenas activas en el subconjunto filtrado, por lo que conviene incentivar calificaciones para fortalecer el analisis de satisfaccion.'
        )

    report_context = {
        'filters_lines': [f'{clave}: {valor}' for clave, valor in filtros.items()],
        'summary_cards': [
            {'label': 'Libros filtrados', 'value': str(total_libros)},
            {'label': 'Usuarios involucrados', 'value': str(total_usuarios)},
            {'label': 'Generos presentes', 'value': str(total_generos)},
            {'label': 'Promedio calificacion', 'value': f'{promedio_calificacion:.1f}/5' if resumen_calificaciones['total'] else 'Sin datos'},
        ],
        'stat_sections': [
            {'title': 'Consulta estadistica por estado', 'headers': ['Estado', 'Total'], 'rows': [[item['estado'], item['total']] for item in consulta_estados]},
            {'title': 'Consulta estadistica por genero', 'headers': ['Genero', 'Total'], 'rows': [[item['generos__nombre'], item['total']] for item in consulta_generos]},
            {
                'title': 'Consulta estadistica por usuario',
                'headers': ['Usuario', 'Total libros'],
                'rows': [[
                    ' '.join(filter(None, [item['usuario_propietario__nombre1'], item['usuario_propietario__nombre2'], item['usuario_propietario__apellido1'], item['usuario_propietario__apellido2']])).strip() or item['usuario_propietario__email'],
                    item['total'],
                ] for item in consulta_usuarios],
            },
            {'title': 'Consulta estadistica de calificaciones', 'headers': ['Estrellas', 'Total resenas'], 'rows': [[f"{item['calificacion']}/5", item['total']] for item in distribucion_calificaciones]},
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
            'Activo' if serialized['activo'] else 'Desactivado',
            f"{serialized['calificacion']:.1f}/5" if serialized['totalCalificaciones'] else 'Sin resenas',
        ])

    return _build_pdf_response(
        'Reporte analitico de libros registrados',
        rows,
        'reporte_libros.pdf',
        report_context=report_context,
        columns=[('Usuario', 92), ('Titulo', 120), ('Autor', 92), ('Genero', 70), ('Estado', 54), ('Activo', 48), ('Calif.', 48)],
    )
