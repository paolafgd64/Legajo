import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import Intercambio, Libro


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


class InventarioApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='lector@example.com',
            password='Segura123!@#',
            nombre1='Lector',
            apellido1='Demo',
            direccion='Calle 45',
            ciudad='Bogota',
            telefono=3004567890,
        )

    def test_crea_libro_en_base_de_datos(self):
        self.client.force_login(self.user)
        portada = SimpleUploadedFile('portada.jpg', b'fake-image-content', content_type='image/jpeg')

        response = self.client.post(
            '/api/libros',
            data={
                'titulo': 'Cien anos de soledad',
                'autor': 'Gabriel Garcia Marquez',
                'sinopsis': 'Una novela clasica.',
                'genero': 'Realismo magico',
                'estado': 'Publicado',
                'imagen': portada,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Libro.objects.filter(titulo='Cien anos de soledad').exists())
        self.assertEqual(Libro.objects.get(titulo='Cien anos de soledad').usuario_propietario, self.user)

    def test_lista_solo_libros_del_usuario_autenticado(self):
        other_user = get_user_model().objects.create_user(
            email='otro@example.com',
            password='Segura123!@#',
            nombre1='Otro',
            apellido1='Usuario',
            direccion='Calle 9',
            ciudad='Cali',
            telefono=3000000001,
        )
        Libro.objects.create(
            titulo='Libro mio',
            sinopsis='Propio',
            estado='Publicado',
            url_imagen='/static/web/imgs/libro_de_la_selva.jpg',
            usuario_propietario=self.user,
        )
        Libro.objects.create(
            titulo='Libro ajeno',
            sinopsis='Ajeno',
            estado='Publicado',
            url_imagen='/static/web/imgs/libro_de_la_selva.jpg',
            usuario_propietario=other_user,
        )

        self.client.force_login(self.user)
        response = self.client.get('/api/libros')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['titulo'], 'Libro mio')

    def test_elimina_libro_del_inventario(self):
        self.client.force_login(self.user)
        libro = Libro.objects.create(
            titulo='Libro temporal',
            sinopsis='Temporal',
            estado='Publicado',
            url_imagen='/static/web/imgs/libro_de_la_selva.jpg',
            usuario_propietario=self.user,
        )

        response = self.client.delete(f'/api/libros/{libro.id}')

        self.assertEqual(response.status_code, 200)
        libro.refresh_from_db()
        self.assertFalse(libro.activo)

    def test_recomendados_devuelve_libros_de_otros_usuarios(self):
        other_user = get_user_model().objects.create_user(
            email='recomienda@example.com',
            password='Segura123!@#',
            nombre1='Otra',
            apellido1='Persona',
            direccion='Calle 88',
            ciudad='Medellin',
            telefono=3000000002,
        )
        Libro.objects.create(
            titulo='Libro propio',
            sinopsis='Propio',
            estado='Publicado',
            url_imagen='/static/web/imgs/libro_de_la_selva.jpg',
            usuario_propietario=self.user,
        )
        Libro.objects.create(
            titulo='Libro recomendado',
            sinopsis='De otro usuario',
            estado='Publicado',
            url_imagen='/static/web/imgs/libro_de_la_selva.jpg',
            usuario_propietario=other_user,
        )

        self.client.force_login(self.user)
        response = self.client.get('/api/libros/recomendados')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['titulo'], 'Libro recomendado')

    def test_solicitar_intercambio_crea_registro_pendiente(self):
        other_user = get_user_model().objects.create_user(
            email='dueno@example.com',
            password='Segura123!@#',
            nombre1='Dueno',
            apellido1='Libro',
            direccion='Calle 77',
            ciudad='Barranquilla',
            telefono=3000000003,
        )
        libro = Libro.objects.create(
            titulo='Libro solicitado',
            sinopsis='Disponible para intercambio',
            estado='Publicado',
            url_imagen='/static/web/imgs/libro_de_la_selva.jpg',
            usuario_propietario=other_user,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            '/api/intercambios/request',
            data=json.dumps({'libroId': libro.id}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Intercambio.objects.filter(
                usuario_solicitante=self.user,
                usuario_receptor=other_user,
                libro_solicitado=libro,
                estado=Intercambio.Estado.PENDIENTE,
            ).exists()
        )
