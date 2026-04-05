from django.contrib.auth import get_user_model
from django.db import transaction

from ..validators import ValidationServiceError


User = get_user_model()


def _normalize_user_payload(item, indice):
    if not isinstance(item, dict):
        raise ValidationServiceError(f'El usuario en la posicion {indice} no es un objeto JSON valido.')

    email = str(item.get('email') or item.get('correo') or '').strip().lower()
    nombre1 = str(item.get('nombre1') or item.get('primerNombre') or '').strip()
    apellido1 = str(item.get('apellido1') or item.get('primerApellido') or '').strip()
    direccion = str(item.get('direccion') or '').strip()
    ciudad = str(item.get('ciudad') or '').strip()
    telefono = str(item.get('telefono') or '').strip()
    password = str(item.get('password') or item.get('clave') or '').strip()

    if not email:
        raise ValidationServiceError(f'El usuario en la posicion {indice} no tiene correo.')
    if not nombre1:
        raise ValidationServiceError(f'El usuario {email} no tiene primer nombre.')
    if not apellido1:
        raise ValidationServiceError(f'El usuario {email} no tiene primer apellido.')
    if not direccion:
        raise ValidationServiceError(f'El usuario {email} no tiene direccion.')
    if not ciudad:
        raise ValidationServiceError(f'El usuario {email} no tiene ciudad.')
    if not telefono.isdigit():
        raise ValidationServiceError(f'El telefono del usuario {email} debe contener solo numeros.')
    if not password:
        raise ValidationServiceError(f'El usuario {email} no tiene contrasena.')

    rol = str(item.get('rol') or User.Rol.USUARIO).strip().lower()
    if rol not in {User.Rol.ADMIN, User.Rol.USUARIO}:
        raise ValidationServiceError(f'El rol del usuario {email} no es valido.')

    return {
        'email': email,
        'password': password,
        'nombre1': nombre1,
        'nombre2': str(item.get('nombre2') or item.get('segundoNombre') or '').strip() or None,
        'apellido1': apellido1,
        'apellido2': str(item.get('apellido2') or item.get('segundoApellido') or '').strip() or None,
        'direccion': direccion,
        'ciudad': ciudad,
        'telefono': int(telefono),
        'rol': rol,
        'activo': bool(item.get('activo', True)),
        'is_active': bool(item.get('is_active', True)),
    }


def import_users_from_payload(payload, actualizar=False):
    if not isinstance(payload, list):
        raise ValidationServiceError('El archivo JSON debe contener una lista de usuarios.')

    creados = 0
    actualizados = 0
    omitidos = 0

    with transaction.atomic():
        for indice, item in enumerate(payload, start=1):
            usuario_data = _normalize_user_payload(item, indice)
            email = usuario_data.pop('email')
            password = usuario_data.pop('password')

            existente = User.objects.filter(email=email).first()
            if existente:
                if not actualizar:
                    omitidos += 1
                    continue

                for field, value in usuario_data.items():
                    setattr(existente, field, value)
                existente.set_password(password)
                existente.save()
                actualizados += 1
                continue

            User.objects.create_user(
                email=email,
                password=password,
                **usuario_data,
            )
            creados += 1

    return {
        'creados': creados,
        'actualizados': actualizados,
        'omitidos': omitidos,
    }
