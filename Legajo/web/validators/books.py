from ..models import Libro
from .errors import ValidationServiceError


# Limpieza basica para evitar None y espacios sobrantes en validaciones.
def _clean_text(value):
    if value is None:
        return ''
    return str(value).strip()


# Verifica campos obligatorios genericos para no repetir validacion en cada endpoint.
def validate_required_fields(data, required_fields):
    for field, message in required_fields.items():
        if _clean_text(data.get(field)) == '':
            raise ValidationServiceError(message)


# Valida y normaliza payload de libros antes de llegar a la capa de persistencia.
def validate_book_payload(data, require_all=True):
    required_fields = {
        'titulo': 'El titulo es obligatorio.',
        'autor': 'El autor es obligatorio.',
        'genero': 'El genero es obligatorio.',
    }
    if require_all:
        validate_required_fields(data, required_fields)

    titulo = _clean_text(data.get('titulo'))
    autor = _clean_text(data.get('autor'))
    genero = _clean_text(data.get('genero'))
    sinopsis = _clean_text(data.get('sinopsis'))
    estado = _clean_text(data.get('estado')) or Libro.Estado.PUBLICADO
    url_imagen = _clean_text(data.get('urlImagen') or data.get('url_imagen'))

    if titulo == '' and 'titulo' in data:
        raise ValidationServiceError('El titulo es obligatorio.')
    if autor == '' and 'autor' in data:
        raise ValidationServiceError('El autor es obligatorio.')
    if genero == '' and 'genero' in data:
        raise ValidationServiceError('El genero es obligatorio.')

    if estado not in Libro.Estado.values:
        raise ValidationServiceError('El estado del libro no es valido.')

    if len(titulo) > 100:
        raise ValidationServiceError('El titulo no puede superar los 100 caracteres.')
    if len(genero) > 45:
        raise ValidationServiceError('El genero no puede superar los 45 caracteres.')
    if len(url_imagen) > 255:
        raise ValidationServiceError('La URL de la imagen no puede superar los 255 caracteres.')

    return {
        'titulo': titulo,
        'autor': autor,
        'sinopsis': sinopsis,
        'genero': genero,
        'estado': estado,
        'url_imagen': url_imagen,
    }
