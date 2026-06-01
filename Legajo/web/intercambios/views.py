"""Vistas del modulo de intercambios.

Manejan el ciclo completo del intercambio:
- solicitud
- aceptacion
- consulta de notificaciones
- confirmacion final por ambas partes
"""

from django.http import JsonResponse
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..administracion.models import NotificacionUsuario, ReporteUsuario
from ..gestion_libros.models import Libro
from ..services import request_exchange, serialize_book
from ..validators import ControlledError
from ..views.helpers import (
    _read_json_body,
    _service_error_response,
    _unauthorized_response,
)
from .models import Intercambio


@require_http_methods(["GET"])
def api_intercambios(request):
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
        es_solicitante = intercambio.usuario_solicitante_id == request.user.id
        contraparte = intercambio.usuario_receptor if es_solicitante else intercambio.usuario_solicitante
        nombre_contraparte = str(contraparte) if contraparte else 'Usuario desconocido'
        libro_solicitado = intercambio.libro_solicitado.titulo if intercambio.libro_solicitado else 'Libro no disponible'
        libro_cambio = intercambio.libro_cambio.titulo if intercambio.libro_cambio else 'Sin seleccionar'

        if intercambio.estado == Intercambio.Estado.PENDIENTE:
            descripcion = f'Pendiente por "{libro_solicitado}".'
        elif intercambio.estado == Intercambio.Estado.ACEPTADO:
            total_confirmaciones = (
                (1 if intercambio.confirmacion_solicitante else 0) +
                (1 if intercambio.confirmacion_receptor else 0)
            )
            descripcion = (
                f'Aceptado: "{libro_solicitado}" por "{libro_cambio}". '
                f'Confirmaciones registradas: {total_confirmaciones}/2.'
            )
        elif intercambio.estado == Intercambio.Estado.COMPLETADO:
            descripcion = f'Completado: "{libro_solicitado}" por "{libro_cambio}".'
        elif intercambio.estado == Intercambio.Estado.RECHAZADO:
            descripcion = f'Rechazado: la solicitud por "{libro_solicitado}" no fue aceptada.'
        elif intercambio.estado == Intercambio.Estado.CANCELADO:
            descripcion = f'Cancelado: se cancelo la solicitud por "{libro_solicitado}".'
        else:
            descripcion = f'Estado: {intercambio.estado}.'

        confirmo_actual = intercambio.confirmacion_solicitante if es_solicitante else intercambio.confirmacion_receptor
        confirmo_contraparte = intercambio.confirmacion_receptor if es_solicitante else intercambio.confirmacion_solicitante

        resultado.append({
            'id': intercambio.id,
            'usuario': nombre_contraparte,
            'rolUsuario': 'Solicitante' if es_solicitante else 'Propietario',
            'estado': intercambio.estado,
            'descripcion': descripcion,
            'fecha': intercambio.fecha_solicitud.strftime('%Y-%m-%d %H:%M'),
            'libroSolicitado': libro_solicitado,
            'libroCambio': libro_cambio,
            'requiereConfirmacionDoble': intercambio.estado == Intercambio.Estado.ACEPTADO,
            'yaCompletado': intercambio.estado == Intercambio.Estado.COMPLETADO,
            'puedeCancelar': es_solicitante and intercambio.estado == Intercambio.Estado.PENDIENTE,
            'confirmoActual': confirmo_actual,
            'confirmoContraparte': confirmo_contraparte,
        })

    return JsonResponse(resultado, safe=False)


@require_http_methods(["GET"])
def api_notificaciones(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    notificaciones_intercambio = (
        Intercambio.objects.filter(
            usuario_receptor=request.user,
            activo=True,
        )
        .select_related('usuario_solicitante', 'libro_solicitado')
        .order_by('-fecha_solicitud')
    )

    resultado = []
    for intercambio in notificaciones_intercambio:
        solicitante = intercambio.usuario_solicitante
        libro = intercambio.libro_solicitado
        nombre_solicitante = str(solicitante) if solicitante else 'Usuario desconocido'
        titulo_libro = libro.titulo if libro else 'Libro sin titulo'

        if intercambio.estado == Intercambio.Estado.PENDIENTE:
            mensaje = f'{nombre_solicitante} solicito intercambio por tu libro "{titulo_libro}".'
        elif intercambio.estado == Intercambio.Estado.ACEPTADO:
            mensaje = f'Tienes un intercambio aceptado para "{titulo_libro}".'
        elif intercambio.estado == Intercambio.Estado.RECHAZADO:
            mensaje = f'Rechazaste la solicitud por "{titulo_libro}".'
        elif intercambio.estado == Intercambio.Estado.CANCELADO and intercambio.cancelado_por_id == intercambio.usuario_solicitante_id:
            mensaje = f'{nombre_solicitante} cancelo el intercambio por tu libro "{titulo_libro}".'
        elif intercambio.estado == Intercambio.Estado.CANCELADO:
            continue
        else:
            mensaje = f'El intercambio por "{titulo_libro}" fue completado.'

        fecha_notificacion = intercambio.fecha_confirmacion if intercambio.estado == Intercambio.Estado.CANCELADO and intercambio.fecha_confirmacion else intercambio.fecha_solicitud

        resultado.append({
            'id': intercambio.id,
            'tipo': 'intercambio',
            'usuario': nombre_solicitante,
            'libro': titulo_libro,
            'estado': intercambio.estado,
            'mensaje': mensaje,
            'fecha': fecha_notificacion.strftime('%Y-%m-%d %H:%M'),
            'timestamp': fecha_notificacion.isoformat(),
            'esNueva': intercambio.estado in {Intercambio.Estado.PENDIENTE, Intercambio.Estado.CANCELADO} and not intercambio.notificacion_leida,
            'puedeAceptar': intercambio.estado == Intercambio.Estado.PENDIENTE,
        })

    try:
        notificaciones_sistema = NotificacionUsuario.objects.filter(usuario=request.user, activo=True).order_by('-fecha_creacion')
        for notificacion in notificaciones_sistema:
            resultado.append({
                'id': notificacion.id,
                'tipo': 'sistema',
                'usuario': 'Equipo Legajo',
                'libro': '',
                'reporteId': notificacion.reporte_relacionado_id,
                'estado': 'informativo',
                'mensaje': notificacion.mensaje,
                'fecha': notificacion.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
                'timestamp': notificacion.fecha_creacion.isoformat(),
                'esNueva': not notificacion.leida,
                'puedeAceptar': False,
            })
    except DatabaseError:
        pass

    reportes_resueltos = (
        ReporteUsuario.objects.filter(
            usuario_reportante=request.user,
            activo=True,
            estado__in=[ReporteUsuario.Estado.REVISADO, ReporteUsuario.Estado.DESCARTADO],
        )
        .select_related('usuario_reportado')
        .order_by('-fecha_reporte')
    )

    reportes_notificados = {
        item.get('reporteId')
        for item in resultado
        if item.get('tipo') == 'sistema' and item.get('reporteId')
    }

    for reporte in reportes_resueltos:
        if reporte.id in reportes_notificados:
            continue

        nombre_reportado = str(reporte.usuario_reportado) if reporte.usuario_reportado else 'el usuario reportado'
        if reporte.estado == ReporteUsuario.Estado.REVISADO:
            mensaje = (
                f'Tu reporte sobre {nombre_reportado} ya fue revisado por el equipo administrador '
                'y se tomaron las medidas correspondientes.'
            )
        else:
            mensaje = (
                f'Tu reporte sobre {nombre_reportado} fue descartado porque no se encontraron '
                'motivos justificables para tomar medidas.'
            )

        resultado.append({
            'id': f'reporte-{reporte.id}',
            'tipo': 'sistema',
            'usuario': 'Equipo Legajo',
            'libro': '',
            'reporteId': reporte.id,
            'estado': 'informativo',
            'mensaje': mensaje,
            'fecha': reporte.fecha_reporte.strftime('%Y-%m-%d %H:%M'),
            'timestamp': reporte.fecha_reporte.isoformat(),
            'esNueva': str(reporte.id) not in request.session.get('reportes_notificados_leidos', []),
            'puedeAceptar': False,
        })

    resultado.sort(key=lambda item: item['timestamp'], reverse=True)
    for item in resultado:
        item.pop('timestamp', None)
        item.pop('reporteId', None)

    return JsonResponse(resultado, safe=False)


@require_http_methods(["POST"])
def api_marcar_notificaciones_leidas(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    intercambios_actualizados = Intercambio.objects.filter(
        usuario_receptor=request.user,
        activo=True,
        estado__in=[Intercambio.Estado.PENDIENTE, Intercambio.Estado.CANCELADO],
        notificacion_leida=False,
    ).update(notificacion_leida=True)

    notificaciones_actualizadas = 0
    try:
        notificaciones_actualizadas = NotificacionUsuario.objects.filter(
            usuario=request.user,
            activo=True,
            leida=False,
        ).update(leida=True)
    except DatabaseError:
        pass

    reportes_resueltos = ReporteUsuario.objects.filter(
        usuario_reportante=request.user,
        activo=True,
        estado__in=[ReporteUsuario.Estado.REVISADO, ReporteUsuario.Estado.DESCARTADO],
    ).values_list('id', flat=True)
    request.session['reportes_notificados_leidos'] = [str(reporte_id) for reporte_id in reportes_resueltos]
    request.session.modified = True

    return JsonResponse({
        'ok': True,
        'intercambiosMarcados': intercambios_actualizados,
        'notificacionesMarcadas': notificaciones_actualizadas,
    })


@require_http_methods(["GET"])
def api_inventario_solicitante_intercambio(request, intercambio_id):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    try:
        intercambio = Intercambio.objects.select_related('usuario_receptor', 'usuario_solicitante').get(id=intercambio_id, activo=True)
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if intercambio.usuario_receptor_id != request.user.id:
        return JsonResponse({'message': 'No tienes permiso para ver este inventario.'}, status=403)

    libros = (
        Libro.objects.filter(
            usuario_propietario=intercambio.usuario_solicitante,
            estado=Libro.Estado.PUBLICADO,
            activo=True,
        )
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )
    return JsonResponse([serialize_book(libro) for libro in libros], safe=False)


@require_http_methods(["POST"])
def api_aceptar_intercambio(request, intercambio_id):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    try:
        intercambio = Intercambio.objects.select_related('usuario_receptor', 'usuario_solicitante', 'libro_solicitado').get(
            id=intercambio_id,
            activo=True,
        )
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if intercambio.usuario_receptor_id != request.user.id:
        return JsonResponse({'message': 'No tienes permiso para aceptar este intercambio.'}, status=403)
    if intercambio.estado != Intercambio.Estado.PENDIENTE:
        return JsonResponse({'message': 'Este intercambio ya no esta pendiente.'}, status=400)
    if not intercambio.libro_solicitado or intercambio.libro_solicitado.estado != Libro.Estado.PUBLICADO:
        return JsonResponse({'message': 'El libro solicitado ya no esta disponible para intercambio.'}, status=400)

    libro_cambio_id = data.get('libroCambioId')
    if not libro_cambio_id:
        return JsonResponse({'message': 'Debes seleccionar un libro del solicitante.'}, status=400)

    try:
        libro_cambio = Libro.objects.get(
            id=libro_cambio_id,
            usuario_propietario=intercambio.usuario_solicitante,
            estado=Libro.Estado.PUBLICADO,
            activo=True,
        )
    except Libro.DoesNotExist:
        return JsonResponse({'message': 'El libro seleccionado no pertenece al solicitante o no esta disponible.'}, status=400)

    intercambio.libro_cambio = libro_cambio
    intercambio.estado = Intercambio.Estado.ACEPTADO
    intercambio.fecha_confirmacion = timezone.now()
    intercambio.confirmacion_solicitante = False
    intercambio.confirmacion_receptor = False
    intercambio.pin_validacion = None
    intercambio.save(update_fields=['libro_cambio', 'estado', 'fecha_confirmacion', 'confirmacion_solicitante', 'confirmacion_receptor', 'pin_validacion'])

    solicitante = intercambio.usuario_solicitante
    receptor = intercambio.usuario_receptor
    telefono_solicitante = str(solicitante.telefono) if solicitante and solicitante.telefono else ''
    nombre_receptor = str(receptor) if receptor else 'el propietario'
    titulo_solicitado = intercambio.libro_solicitado.titulo if intercambio.libro_solicitado else 'tu libro'
    mensaje_whatsapp = (
        f'Hola {str(solicitante) if solicitante else ""}, '
        f'{nombre_receptor} acepto tu solicitud de intercambio por "{titulo_solicitado}". '
        f'El libro seleccionado para el intercambio es "{libro_cambio.titulo}". '
        'Ya pueden coordinar la entrega y luego ambos deben marcar el intercambio como completado dentro de la app.'
    )

    return JsonResponse({
        'message': 'Intercambio aceptado correctamente.',
        'idIntercambio': intercambio.id,
        'libroCambio': libro_cambio.titulo,
        'telefonoWhatsapp': telefono_solicitante,
        'mensajeWhatsapp': mensaje_whatsapp,
    })


@require_http_methods(["POST"])
def api_rechazar_intercambio(request, intercambio_id):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    try:
        intercambio = Intercambio.objects.select_related('usuario_receptor', 'usuario_solicitante', 'libro_solicitado').get(
            id=intercambio_id,
            activo=True,
        )
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if intercambio.usuario_receptor_id != request.user.id:
        return JsonResponse({'message': 'No tienes permiso para rechazar este intercambio.'}, status=403)
    if intercambio.estado != Intercambio.Estado.PENDIENTE:
        return JsonResponse({'message': 'Este intercambio ya no esta pendiente.'}, status=400)

    intercambio.estado = Intercambio.Estado.RECHAZADO
    intercambio.libro_cambio = None
    intercambio.fecha_confirmacion = timezone.now()
    intercambio.confirmacion_solicitante = False
    intercambio.confirmacion_receptor = False
    intercambio.pin_validacion = None
    intercambio.save(update_fields=[
        'estado',
        'libro_cambio',
        'fecha_confirmacion',
        'confirmacion_solicitante',
        'confirmacion_receptor',
        'pin_validacion',
    ])

    titulo_solicitado = intercambio.libro_solicitado.titulo if intercambio.libro_solicitado else 'el libro solicitado'
    return JsonResponse({
        'message': f'Rechazaste la solicitud de intercambio por "{titulo_solicitado}".',
        'idIntercambio': intercambio.id,
    })


@require_http_methods(["POST"])
def api_cancelar_intercambio(request, intercambio_id):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    try:
        intercambio = Intercambio.objects.select_related('usuario_receptor', 'usuario_solicitante', 'libro_solicitado').get(
            id=intercambio_id,
            activo=True,
        )
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if intercambio.usuario_solicitante_id != request.user.id:
        return JsonResponse({'message': 'Solo quien envio la solicitud puede cancelar este intercambio.'}, status=403)
    if intercambio.estado != Intercambio.Estado.PENDIENTE:
        return JsonResponse({'message': 'Solo puedes cancelar solicitudes pendientes.'}, status=400)

    intercambio.estado = Intercambio.Estado.CANCELADO
    intercambio.libro_cambio = None
    intercambio.fecha_confirmacion = timezone.now()
    intercambio.confirmacion_solicitante = False
    intercambio.confirmacion_receptor = False
    intercambio.pin_validacion = None
    intercambio.notificacion_leida = False
    intercambio.cancelado_por = request.user
    intercambio.save(update_fields=[
        'estado',
        'libro_cambio',
        'fecha_confirmacion',
        'confirmacion_solicitante',
        'confirmacion_receptor',
        'pin_validacion',
        'notificacion_leida',
        'cancelado_por',
    ])

    titulo_solicitado = intercambio.libro_solicitado.titulo if intercambio.libro_solicitado else 'el libro solicitado'
    return JsonResponse({
        'message': f'Cancelaste la solicitud de intercambio por "{titulo_solicitado}".',
        'idIntercambio': intercambio.id,
    })


@require_http_methods(["POST"])
def api_confirmar_intercambio_pin(request, intercambio_id):
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
    if not intercambio.libro_solicitado or not intercambio.libro_cambio:
        return JsonResponse({'message': 'El intercambio no tiene ambos libros asignados.'}, status=400)
    if not intercambio.usuario_solicitante or not intercambio.usuario_receptor:
        return JsonResponse({'message': 'El intercambio no tiene usuarios validos para completar.'}, status=400)

    with transaction.atomic():
        # El intercambio solo se completa cuando ambos participantes confirman
        # desde su propia sesion. Asi evitamos cierres accidentales por terceros.
        if request.user.id == intercambio.usuario_solicitante_id:
            if intercambio.confirmacion_solicitante:
                return JsonResponse({'message': 'Ya marcaste este intercambio como completado.'}, status=400)
            intercambio.confirmacion_solicitante = True
        else:
            if intercambio.confirmacion_receptor:
                return JsonResponse({'message': 'Ya marcaste este intercambio como completado.'}, status=400)
            intercambio.confirmacion_receptor = True

        ambos_confirmaron = intercambio.confirmacion_solicitante and intercambio.confirmacion_receptor
        update_fields = ['confirmacion_solicitante', 'confirmacion_receptor']

        if ambos_confirmaron:
            libro_solicitado = intercambio.libro_solicitado
            libro_cambio = intercambio.libro_cambio
            usuario_solicitante = intercambio.usuario_solicitante
            usuario_receptor = intercambio.usuario_receptor

            libro_solicitado.usuario_propietario = usuario_solicitante
            libro_cambio.usuario_propietario = usuario_receptor
            libro_solicitado.estado = Libro.Estado.LEYENDO
            libro_cambio.estado = Libro.Estado.LEYENDO
            libro_solicitado.save(update_fields=['usuario_propietario', 'estado', 'fecha_actualizacion'])
            libro_cambio.save(update_fields=['usuario_propietario', 'estado', 'fecha_actualizacion'])

            intercambio.estado = Intercambio.Estado.COMPLETADO
            intercambio.fecha_completado = timezone.now()
            update_fields.extend(['estado', 'fecha_completado'])

        intercambio.save(update_fields=update_fields)

    if ambos_confirmaron:
        return JsonResponse({
            'message': 'Ambos usuarios confirmaron. El intercambio se completo correctamente.',
            'idIntercambio': intercambio.id,
            'completado': True,
        })

    return JsonResponse({
        'message': 'Tu confirmacion fue registrada. Falta la confirmacion de la otra persona para completar el intercambio.',
        'idIntercambio': intercambio.id,
        'completado': False,
    })


@require_http_methods(["POST"])
def api_solicitar_intercambio(request):
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

