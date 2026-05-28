import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from web.models import Libro


class AuthIntegrationTests(TestCase):
    def test_login_de_usuario_activo_por_api(self):
        get_user_model().objects.create_user(
            email='usuario.activo@example.com',
            password='Segura123!@#',
            nombre1='Usuario',
            apellido1='Activo',
            direccion='Calle 10',
            ciudad='Bogota',
            telefono=3001234567,
        )

        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'correo': 'usuario.activo@example.com',
                'clave': 'Segura123!@#',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['redirect_url'], '/dashboard_usuario/')


class BookInventoryIntegrationTests(TestCase):
    def test_crear_libros_y_listar_stock_agrupado_por_api(self):
        usuario = get_user_model().objects.create_user(
            email='inventario.integracion@example.com',
            password='Segura123!@#',
            nombre1='Usuario',
            apellido1='Inventario',
            direccion='Calle 11',
            ciudad='Bogota',
            telefono=3002222222,
        )
        self.client.force_login(usuario)

        creacion = self.client.post(
            '/api/libros',
            data={
                'titulo': 'Rayuela',
                'autor': 'Julio Cortazar',
                'genero': 'Ficcion',
                'sinopsis': 'Novela experimental.',
                'estado': Libro.Estado.PUBLICADO,
                'cantidadLibros': '2',
            },
        )
        listado = self.client.get('/api/libros')

        self.assertEqual(creacion.status_code, 201)
        self.assertEqual(listado.status_code, 200)
        self.assertEqual(listado.json()[0]['stock'], 2)
