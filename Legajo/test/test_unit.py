from django.contrib.auth import get_user_model
from django.test import TestCase

from web.models import Libro
from web.services.users import import_users_from_payload
from web.validators.books import validate_book_payload


class BookValidatorUnitTests(TestCase):
    def test_validate_book_payload_normaliza_campos_y_estado_por_defecto(self):
        payload = validate_book_payload({
            'titulo': '  El principito  ',
            'autor': '  Antoine de Saint-Exupery  ',
            'genero': ' fantasia ',
            'sinopsis': '  Un viaje por planetas. ',
        })

        self.assertEqual(payload['titulo'], 'El principito')
        self.assertEqual(payload['autor'], 'Antoine de Saint-Exupery')
        self.assertEqual(payload['genero'], 'fantasia')
        self.assertEqual(payload['estado'], Libro.Estado.PUBLICADO)


class UserImportServiceUnitTests(TestCase):
    def test_import_users_from_payload_crea_usuario(self):
        resultado = import_users_from_payload([{
            'correo': 'lectora@example.com',
            'clave': 'Segura123!@#',
            'primerNombre': 'Lectora',
            'primerApellido': 'Prueba',
            'direccion': 'Calle 1',
            'ciudad': 'Bogota',
            'telefono': '3001234567',
        }])

        self.assertEqual(resultado['creados'], 1)
        self.assertTrue(get_user_model().objects.filter(email='lectora@example.com').exists())
