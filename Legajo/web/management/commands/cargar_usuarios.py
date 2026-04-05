import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ...services import import_users_from_payload
from ...validators import ValidationServiceError


class Command(BaseCommand):
    help = 'Carga usuarios desde un archivo JSON.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', type=str, help='Ruta del archivo JSON con los usuarios.')
        parser.add_argument(
            '--actualizar',
            action='store_true',
            help='Si el correo ya existe, actualiza el usuario en lugar de omitirlo.',
        )

    def handle(self, *args, **options):
        archivo = Path(options['archivo']).expanduser()
        actualizar = options['actualizar']

        if not archivo.exists():
            raise CommandError(f'No existe el archivo: {archivo}')

        try:
            payload = json.loads(archivo.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise CommandError(f'El archivo no contiene JSON valido: {exc}') from exc

        try:
            result = import_users_from_payload(payload, actualizar=actualizar)
        except ValidationServiceError as exc:
            raise CommandError(exc.message) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Carga completada. Creados: {result['creados']}, actualizados: {result['actualizados']}, omitidos: {result['omitidos']}."
        ))
