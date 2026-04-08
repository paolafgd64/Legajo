from .errors import ValidationServiceError


# Exige libroId y lo transforma a entero para que el service trabaje con tipos consistentes.
def validate_exchange_payload(data):
    libro_id = data.get('libroId')
    if libro_id in (None, ''):
        raise ValidationServiceError('Debes indicar el libro solicitado.')

    try:
        libro_id = int(libro_id)
    except (TypeError, ValueError) as exc:
        raise ValidationServiceError('El identificador del libro no es valido.') from exc

    return {'libro_id': libro_id}
