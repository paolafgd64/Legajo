import hashlib
import json
import mimetypes
import time
import uuid
from urllib import error, request

from django.conf import settings

from ..validators import ExternalServiceError


def is_cloudinary_configured():
    config = getattr(settings, 'LEGAJO_CLOUDINARY', {})
    return all(
        config.get(key)
        for key in ('cloud_name', 'api_key', 'api_secret')
    )


def upload_image_to_cloudinary(uploaded_file):
    config = getattr(settings, 'LEGAJO_CLOUDINARY', {})
    cloud_name = config.get('cloud_name')
    api_key = config.get('api_key')
    api_secret = config.get('api_secret')
    folder = config.get('folder', 'legajo/libros')

    if not all([cloud_name, api_key, api_secret]):
        raise ExternalServiceError('Cloudinary no esta configurado en el entorno actual.')

    timestamp = str(int(time.time()))
    signature_payload = f'folder={folder}&timestamp={timestamp}{api_secret}'
    signature = hashlib.sha1(signature_payload.encode('utf-8')).hexdigest()

    content_type = uploaded_file.content_type or mimetypes.guess_type(uploaded_file.name)[0] or 'application/octet-stream'
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    boundary = f'----LegajoBoundary{uuid.uuid4().hex}'
    body = bytearray()

    def add_field(name, value):
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode('utf-8'))
        body.extend(str(value).encode('utf-8'))
        body.extend(b'\r\n')

    add_field('api_key', api_key)
    add_field('timestamp', timestamp)
    add_field('signature', signature)
    add_field('folder', folder)

    body.extend(f'--{boundary}\r\n'.encode('utf-8'))
    body.extend(
        (
            f'Content-Disposition: form-data; name="file"; filename="{uploaded_file.name}"\r\n'
            f'Content-Type: {content_type}\r\n\r\n'
        ).encode('utf-8')
    )
    body.extend(file_bytes)
    body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))

    upload_request = request.Request(
        url=f'https://api.cloudinary.com/v1_1/{cloud_name}/image/upload',
        data=bytes(body),
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        method='POST',
    )

    try:
        with request.urlopen(upload_request, timeout=30) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except error.HTTPError as exc:
        details = exc.read().decode('utf-8', errors='ignore')
        raise ExternalServiceError(
            f'Cloudinary rechazo la carga de la imagen. {details or "Verifica las credenciales y el archivo."}'
        ) from exc
    except error.URLError as exc:
        raise ExternalServiceError(
            'No se pudo conectar con Cloudinary. Revisa tu conexion a internet e intentalo de nuevo.'
        ) from exc

    secure_url = (payload.get('secure_url') or '').strip()
    if not secure_url:
        raise ExternalServiceError('Cloudinary no devolvio una URL valida para la imagen.')

    return secure_url
