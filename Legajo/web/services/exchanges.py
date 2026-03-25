from django.db import DatabaseError

from ..models import Intercambio, Libro
from ..validators import DatabaseServiceError, NotFoundServiceError, ValidationServiceError, validate_exchange_payload


def request_exchange(user, data):
    payload = validate_exchange_payload(data)

    try:
        libro = Libro.objects.select_related('usuario_propietario').get(id=payload['libro_id'], activo=True)
    except Libro.DoesNotExist as exc:
        raise NotFoundServiceError('El libro solicitado no existe.') from exc
    except DatabaseError as exc:
        raise DatabaseServiceError() from exc

    if libro.usuario_propietario_id == user.id:
        raise ValidationServiceError('No puedes solicitar intercambio por tu propio libro.')

    try:
        existente = Intercambio.objects.filter(
            usuario_solicitante=user,
            libro_solicitado=libro,
            estado=Intercambio.Estado.PENDIENTE,
            activo=True,
        ).exists()
        if existente:
            raise ValidationServiceError('Ya tienes una solicitud pendiente para este libro.')

        intercambio = Intercambio.objects.create(
            estado=Intercambio.Estado.PENDIENTE,
            usuario_solicitante=user,
            usuario_receptor=libro.usuario_propietario,
            libro_solicitado=libro,
            libro_cambio=None,
        )
    except DatabaseError as exc:
        raise DatabaseServiceError() from exc

    return {
        'message': 'Solicitud de intercambio enviada correctamente.',
        'idIntercambio': intercambio.id,
    }
