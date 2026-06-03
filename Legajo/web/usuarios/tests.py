from django.test import TestCase
from django.urls import reverse


class UsuariosViewsSmokeTests(TestCase):
    def test_login_page_responde_ok(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)

    def test_crear_cuenta_page_responde_ok(self):
        response = self.client.get(reverse('crear_cuenta'))

        self.assertEqual(response.status_code, 200)