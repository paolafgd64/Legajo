import json

from django.contrib.auth import get_user_model
from django.test import TestCase


class AuthApiTests(TestCase):
    def test_registro_crea_usuario_en_base_de_datos(self):
        payload = {
            'primerNombre': 'Ana',
            'segundoNombre': 'Maria',
            'primerApellido': 'Lopez',
            'segundoApellido': 'Gomez',
            'correo': 'ana@example.com',
            'direccion': 'Calle 123',
            'ciudad': 'Bogota',
            'telefono': '3001234567',
            'clave': 'Segura123!@#',
        }

        response = self.client.post(
            '/api/usuarios',
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(get_user_model().objects.filter(email='ana@example.com').exists())

    def test_login_autentica_y_retorna_redireccion(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            email='admin@example.com',
            password='Segura123!@#',
            nombre1='Admin',
            apellido1='Principal',
            direccion='Calle 1',
            ciudad='Bogota',
            telefono=3001234567,
            rol=user_model.Rol.ADMIN,
        )

        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'correo': 'admin@example.com',
                'clave': 'Segura123!@#',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['redirect_url'], '/dashboard_admin/')
