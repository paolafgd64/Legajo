from django.contrib.auth import get_user_model
from django.test import TestCase

from web.models import Intercambio, Libro
from web.services.exchanges import request_exchange
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


class ExchangeServiceUnitTests(TestCase):
    def test_request_exchange_crea_solicitud_pendiente(self):
        user_model = get_user_model()
        propietario = user_model.objects.create_user(
            email='propietario.unitario@example.com',
            password='Segura123!@#',
            nombre1='Propietario',
            apellido1='Unitario',
            direccion='Calle 2',
            ciudad='Bogota',
            telefono=3002222222,
        )
        solicitante = user_model.objects.create_user(
            email='solicitante.unitario@example.com',
            password='Segura123!@#',
            nombre1='Solicitante',
            apellido1='Unitario',
            direccion='Calle 3',
            ciudad='Bogota',
            telefono=3003333333,
        )
        libro = Libro.objects.create(
            titulo='Libro intercambiable',
            sinopsis='Disponible para intercambio.',
            estado=Libro.Estado.PUBLICADO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=propietario,
        )

        resultado = request_exchange(solicitante, {'libroId': libro.id})

        intercambio = Intercambio.objects.get(id=resultado['idIntercambio'])
        self.assertEqual(intercambio.estado, Intercambio.Estado.PENDIENTE)
        self.assertEqual(intercambio.usuario_solicitante, solicitante)
        self.assertEqual(intercambio.usuario_receptor, propietario)
