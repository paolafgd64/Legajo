"""
Modulo de intercambios: solicitudes, aceptacion, confirmacion con PIN.
Endpoints:
- GET /api/intercambios (lista de intercambios del usuario)
- GET /api/notificaciones (intercambios pendientes)
- GET /api/inventario_solicitante_intercambio/<id> (libros para seleccionar)
- POST /api/aceptar_intercambio/<id> (receptor acepta y selecciona libro)
- POST /api/confirmar_intercambio_pin/<id> (confirma con PIN)
- POST /api/solicitar_intercambio (crea solicitud)
"""
import random

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..models import Intercambio, Libro
from ..services import request_exchange, serialize_book
from ..validators import ControlledError
from .helpers import (
    _read_json_body,
    _unauthorized_response,
    _service_error_response,
)


User = get_user_model()


# ============================================================================
# API ENDPOINTS (JSON)
# ============================================================================

@require_http_methods(["GET"])
def api_intercambios(request):
    """
    Lista intercambios donde participa el usuario (como solicitante o receptor).
    GET /api/intercambios/
    """
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
        # Traduce modelo a JSON de lectura simple para la UI.
        es_solicitante = intercambio.usuario_solicitante_id == request.user.id
        contraparte = intercambio.usuario_receptor if es_solicitante else intercambio.usuario_solicitante
        nombre_contraparte = str(contraparte) if contraparte else 'Usuario desconocido'
        libro_solicitado = intercambio.libro_solicitado.titulo if intercambio.libro_solicitado else 'Libro no disponible'
        libro_cambio = intercambio.libro_cambio.titulo if intercambio.libro_cambio else 'Sin seleccionar'

        if intercambio.estado == Intercambio.Estado.PENDIENTE:
            descripcion = f'Pendiente por "{libro_solicitado}".'
        elif intercambio.estado == Intercambio.Estado.ACEPTADO:
            descripcion = f'Aceptado: "{libro_solicitado}" por "{libro_cambio}".'
        elif intercambio.estado == Intercambio.Estado.COMPLETADO:
            descripcion = f'Completado: "{libro_solicitado}" por "{libro_cambio}".'
        else:
            descripcion = f'Estado: {intercambio.estado}.'

        resultado.append({
            'id': intercambio.id,
            'usuario': nombre_contraparte,
            'rolUsuario': 'Solicitante' if es_solicitante else 'Propietario',
            'estado': intercambio.estado,
            'descripcion': descripcion,
            'fecha': intercambio.fecha_solicitud.strftime('%Y-%m-%d %H:%M'),
            'libroSolicitado': libro_solicitado,
            'libroCambio': libro_cambio,
            'pinRequerido': intercambio.estado == Intercambio.Estado.ACEPTADO,
            'yaCompletado': intercambio.estado == Intercambio.Estado.COMPLETADO,
        })

    return JsonResponse(resultado, safe=False)


@require_http_methods(["GET"])
def api_notificaciones(request):
    """
    Notificaciones: intercambios pendientes dirigidos al usuario actual.
    GET /api/notificaciones/
    """
    if not request.user.is_authenticated:
        return _unauthorized_response()

    notificaciones = (
        Intercambio.objects.filter(
            usuario_receptor=request.user,
            activo=True,
        )
        .select_related('usuario_solicitante', 'libro_solicitado')
        .order_by('-fecha_solicitud')
    )

    resultado = []
    for intercambio in notificaciones:
        solicitante = intercambio.usuario_solicitante
        libro = intercambio.libro_solicitado
        nombre_solicitante = str(solicitante) if solicitante else 'Usuario desconocido'
        titulo_libro = libro.titulo if libro else 'Libro sin titulo'

        if intercambio.estado == Intercambio.Estado.PENDIENTE:
            mensaje = f'{nombre_solicitante} solicito intercambio por tu libro "{titulo_libro}".'
        elif intercambio.estado == Intercambio.Estado.ACEPTADO:
            mensaje = f'Tienes un intercambio aceptado para "{titulo_libro}".'
        elif intercambio.estado == Intercambio.Estado.RECHAZADO:
            mensaje = f'La solicitud por "{titulo_libro}" fue rechazada.'
        else:
            mensaje = f'El intercambio por "{titulo_libro}" fue completado.'

        resultado.append({
            'id': intercambio.id,
            'usuario': nombre_solicitante,
            'libro': titulo_libro,
            'estado': intercambio.estado,
            'mensaje': mensaje,
            'fecha': intercambio.fecha_solicitud.strftime('%Y-%m-%d %H:%M'),
            'esNueva': intercambio.estado == Intercambio.Estado.PENDIENTE,
            'puedeAceptar': intercambio.estado == Intercambio.Estado.PENDIENTE,
        })

    return JsonResponse(resultado, safe=False)


@require_http_methods(["GET"])
def api_inventario_solicitante_intercambio(request, intercambio_id):
    """
    Lista libros del solicitante para que el receptor pueda elegir cual cambiar.
    GET /api/inventario_solicitante_intercambio/<id>/
    """
    if not request.user.is_authenticated:
        return _unauthorized_response()

    try:
        intercambio = Intercambio.objects.select_related('usuario_receptor', 'usuario_solicitante').get(
            id=intercambio_id,
            activo=True,
        )
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if intercambio.usuario_receptor_id != request.user.id:
        return JsonResponse({'message': 'No tienes permiso para ver este inventario.'}, status=403)

    libros = (
        Libro.objects.filter(
            usuario_propietario=intercambio.usuario_solicitante,
            activo=True,
        )
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )

    return JsonResponse([serialize_book(libro) for libro in libros], safe=False)


@require_http_methods(["POST"])
def api_aceptar_intercambio(request, intercambio_id):
    """
    El receptor acepta la solicitud, elige libro de cambio y se genera PIN.
    POST /api/aceptar_intercambio/<id>/
    Body:
        {
            "libroCambioId": 42
        }
    
    Respuesta incluye PIN y mensaje WhatsApp para contatoar al solicitante.
    """
    if not request.user.is_authenticated:
        return _unauthorized_response()

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    try:
        intercambio = Intercambio.objects.select_related(
            'usuario_receptor',
            'usuario_solicitante',
            'libro_solicitado',
        ).get(id=intercambio_id, activo=True)
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if intercambio.usuario_receptor_id != request.user.id:
        return JsonResponse({'message': 'No tienes permiso para aceptar este intercambio.'}, status=403)

    if intercambio.estado != Intercambio.Estado.PENDIENTE:
        return JsonResponse({'message': 'Este intercambio ya no esta pendiente.'}, status=400)

    libro_cambio_id = data.get('libroCambioId')
    if not libro_cambio_id:
        return JsonResponse({'message': 'Debes seleccionar un libro del solicitante.'}, status=400)

    try:
        libro_cambio = Libro.objects.get(
            id=libro_cambio_id,
            usuario_propietario=intercambio.usuario_solicitante,
            activo=True,
        )
    except Libro.DoesNotExist:
        return JsonResponse({'message': 'El libro seleccionado no pertenece al solicitante.'}, status=400)

    intercambio.libro_cambio = libro_cambio
    intercambio.estado = Intercambio.Estado.ACEPTADO
    intercambio.fecha_confirmacion = timezone.now()
    # PIN de 6 digitos para confirmar presencialmente el intercambio.
    intercambio.pin_validacion = f'{random.randint(0, 999999):06d}'
    intercambio.save(update_fields=['libro_cambio', 'estado', 'fecha_confirmacion', 'pin_validacion'])

    solicitante = intercambio.usuario_solicitante
    receptor = intercambio.usuario_receptor
    telefono_solicitante = str(solicitante.telefono) if solicitante and solicitante.telefono else ''
    nombre_receptor = str(receptor) if receptor else 'el propietario'
    titulo_solicitado = intercambio.libro_solicitado.titulo if intercambio.libro_solicitado else 'tu libro'
    mensaje_whatsapp = (
        f'Hola {str(solicitante) if solicitante else ""}, '
        f'{nombre_receptor} acepto tu solicitud de intercambio por "{titulo_solicitado}". '
        f'El libro seleccionado para el intercambio es "{libro_cambio.titulo}". '
        f'Tu PIN de validacion es {intercambio.pin_validacion}. Ponganse de acuerdo para continuar.'
    )

    return JsonResponse({
        'message': 'Intercambio aceptado correctamente.',
        'idIntercambio': intercambio.id,
        'libroCambio': libro_cambio.titulo,
        'telefonoWhatsapp': telefono_solicitante,
        'mensajeWhatsapp': mensaje_whatsapp,
        'pinValidacion': intercambio.pin_validacion,
    })


@require_http_methods(["POST"])
def api_confirmar_intercambio_pin(request, intercambio_id):
    """
    Confirmacion final: valida PIN y realiza intercambio de propietarios en transaccion atomica.
    POST /api/confirmar_intercambio_pin/<id>/
    Body:
        {
            "pin": "123456"
        }
    """
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

    pin = str(data.get('pin') or '').strip()
    if not pin:
        return JsonResponse({'message': 'Debes ingresar el PIN de validacion.'}, status=400)

    if pin != (intercambio.pin_validacion or ''):
        return JsonResponse({'message': 'El PIN ingresado no es valido.'}, status=400)

    if not intercambio.libro_solicitado or not intercambio.libro_cambio:
        return JsonResponse({'message': 'El intercambio no tiene ambos libros asignados.'}, status=400)

    if not intercambio.usuario_solicitante or not intercambio.usuario_receptor:
        return JsonResponse({'message': 'El intercambio no tiene usuarios validos para completar.'}, status=400)

    # Atomicidad: o se actualiza todo (libros + intercambio) o no se actualiza nada.
    with transaction.atomic():
        libro_solicitado = intercambio.libro_solicitado
        libro_cambio = intercambio.libro_cambio
        usuario_solicitante = intercambio.usuario_solicitante
        usuario_receptor = intercambio.usuario_receptor

        libro_solicitado.usuario_propietario = usuario_solicitante
        libro_cambio.usuario_propietario = usuario_receptor
        libro_solicitado.save(update_fields=['usuario_propietario'])
        libro_cambio.save(update_fields=['usuario_propietario'])

        intercambio.estado = Intercambio.Estado.COMPLETADO
        intercambio.fecha_completado = timezone.now()
        intercambio.save(update_fields=['estado', 'fecha_completado'])

    return JsonResponse({
        'message': 'Intercambio confirmado correctamente.',
        'idIntercambio': intercambio.id,
    })


@require_http_methods(["POST"])
def api_solicitar_intercambio(request):
    """
    Crea una solicitud de intercambio delegando reglas de negocio al servicio.
    POST /api/solicitar_intercambio/
    Body:
        {
            "libroSolicitadoId": 42,
            "usuarioReceptorId": 10
        }
    """
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
