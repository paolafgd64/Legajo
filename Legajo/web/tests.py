import json
import os
from importlib import import_module, reload
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone

from .models import Autor, Genero, Intercambio, Libro, NotificacionUsuario, ReporteUsuario
from .views.helpers import _build_password_reset_link, _get_admin_dashboard_context, _get_password_reset_user


class CloudinarySettingsTests(TestCase):
    def setUp(self):
        self.settings_module = import_module('Legajo.settings')
        self.env_path = Path(self.settings_module.BASE_DIR) / '.env'
        self.original_env = {
            key: os.environ.get(key)
            for key in (
                'CLOUDINARY_URL',
                'LEGAJO_CLOUDINARY_CLOUD_NAME',
                'LEGAJO_CLOUDINARY_API_KEY',
                'LEGAJO_CLOUDINARY_API_SECRET',
                'LEGAJO_CLOUDINARY_FOLDER',
            )
        }
        self.original_env_file = self.env_path.read_text(encoding='utf-8') if self.env_path.exists() else None

    def tearDown(self):
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        if self.original_env_file is None:
            if self.env_path.exists():
                self.env_path.unlink()
        else:
            self.env_path.write_text(self.original_env_file, encoding='utf-8')

        reload(self.settings_module)

    def test_cloudinary_settings_accept_cloudinary_url(self):
        os.environ.pop('LEGAJO_CLOUDINARY_CLOUD_NAME', None)
        os.environ.pop('LEGAJO_CLOUDINARY_API_KEY', None)
        os.environ.pop('LEGAJO_CLOUDINARY_API_SECRET', None)
        os.environ['CLOUDINARY_URL'] = 'cloudinary://mi_api_key:mi_api_secret@mi_cloud_name'
        os.environ['LEGAJO_CLOUDINARY_FOLDER'] = 'legajo/pruebas'

        config = self.settings_module._get_cloudinary_settings()

        self.assertEqual(config['cloud_name'], 'mi_cloud_name')
        self.assertEqual(config['api_key'], 'mi_api_key')
        self.assertEqual(config['api_secret'], 'mi_api_secret')
        self.assertEqual(config['folder'], 'legajo/pruebas')

    def test_local_env_file_loads_cloudinary_variables(self):
        for key in self.original_env:
            os.environ.pop(key, None)

        self.env_path.write_text(
            '\n'.join([
                'LEGAJO_CLOUDINARY_CLOUD_NAME=demo-cloud',
                'LEGAJO_CLOUDINARY_API_KEY=demo-key',
                'LEGAJO_CLOUDINARY_API_SECRET=demo-secret',
                'LEGAJO_CLOUDINARY_FOLDER=legajo/env-file',
            ]),
            encoding='utf-8',
        )

        reloaded_settings = reload(self.settings_module)

        self.assertEqual(reloaded_settings.LEGAJO_CLOUDINARY['cloud_name'], 'demo-cloud')
        self.assertEqual(reloaded_settings.LEGAJO_CLOUDINARY['api_key'], 'demo-key')
        self.assertEqual(reloaded_settings.LEGAJO_CLOUDINARY['api_secret'], 'demo-secret')
        self.assertEqual(reloaded_settings.LEGAJO_CLOUDINARY['folder'], 'legajo/env-file')


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

    def test_login_usuario_desactivado_devuelve_motivo(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email='desactivado@example.com',
            password='Segura123!@#',
            nombre1='Cuenta',
            apellido1='Desactivada',
            direccion='Calle 2',
            ciudad='Bogota',
            telefono=3001234568,
        )
        user.activo = False
        user.is_active = False
        user.motivo_desactivacion = 'Incumplimiento de normas de la comunidad.'
        user.save(update_fields=['activo', 'is_active', 'motivo_desactivacion'])

        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'correo': 'desactivado@example.com',
                'clave': 'Segura123!@#',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['code'], 'account_disabled')
        self.assertEqual(data['reason'], 'Incumplimiento de normas de la comunidad.')
        self.assertEqual(data['landingUrl'], '/')

    def test_forgot_password_generates_reset_link_in_debug(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email='recovery@example.com',
            password='Segura123!@#',
            nombre1='Recuperar',
            apellido1='Cuenta',
            direccion='Calle 8',
            ciudad='Bogota',
            telefono=3001230000,
        )

        class DummyRequest:
            def build_absolute_uri(self, path):
                return f'http://testserver{path}'

        reset_link = _build_password_reset_link(DummyRequest(), user)

        self.assertIn('/reset_password/?uid=', reset_link)
        self.assertIn('token=', reset_link)
        self.assertEqual(_get_password_reset_user(urlsafe_base64_encode(force_bytes(user.pk))), user)

    def test_reset_password_updates_user_password(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email='reset@example.com',
            password='Anterior123!@#',
            nombre1='Reset',
            apellido1='Usuario',
            direccion='Calle 9',
            ciudad='Bogota',
            telefono=3001230001,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.post(
            '/reset_password/',
            data={
                'uid': uid,
                'token': token,
                'password': 'NuevaSegura123!@#',
                'confirmPassword': 'NuevaSegura123!@#',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/login/?reset=success')
        user.refresh_from_db()
        self.assertTrue(user.check_password('NuevaSegura123!@#'))


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

        response = self.client.post(
            '/api/libros',
            data={
                'titulo': 'Cien anos de soledad',
                'autor': 'Gabriel Garcia Marquez',
                'sinopsis': 'Una novela clasica.',
                'genero': 'Realismo magico',
                'estado': 'Publicado',
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Libro.objects.filter(titulo='Cien anos de soledad').exists())
        self.assertEqual(Libro.objects.get(titulo='Cien anos de soledad').usuario_propietario, self.user)

    def test_crea_varias_copias_y_lista_stock_agrupado(self):
        self.client.force_login(self.user)

        response = self.client.post(
            '/api/libros',
            data={
                'titulo': 'Rayuela',
                'autor': 'Julio Cortazar',
                'sinopsis': 'Novela experimental.',
                'genero': 'Ficcion',
                'estado': 'Publicado',
                'cantidadLibros': '3',
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Libro.objects.filter(titulo='Rayuela', usuario_propietario=self.user).count(), 3)

        inventario = self.client.get('/api/libros')
        self.assertEqual(inventario.status_code, 200)
        data = inventario.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['titulo'], 'Rayuela')
        self.assertEqual(data[0]['stock'], 3)
        self.assertEqual(len(data[0]['idsLibros']), 3)

    def test_no_permite_mas_de_diez_copias(self):
        self.client.force_login(self.user)

        response = self.client.post(
            '/api/libros',
            data={
                'titulo': 'Libro repetido',
                'autor': 'Autor Prueba',
                'sinopsis': 'Demasiadas copias.',
                'genero': 'Ficcion',
                'estado': 'Publicado',
                'cantidadLibros': '11',
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'La cantidad de libros debe estar entre 1 y 10.')
        self.assertFalse(Libro.objects.filter(titulo='Libro repetido').exists())

    def test_autor_de_un_solo_nombre_no_duplica_apellido(self):
        self.client.force_login(self.user)

        response = self.client.post(
            '/api/libros',
            data={
                'titulo': 'Libro de Cher',
                'autor': 'Cher',
                'sinopsis': 'Biografia',
                'genero': 'Biografia',
                'estado': 'Publicado',
            },
        )

        self.assertEqual(response.status_code, 201)
        autor = Autor.objects.get(nombre1='Cher')
        self.assertEqual(autor.apellido1, '')

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
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )
        Libro.objects.create(
            titulo='Libro ajeno',
            sinopsis='Ajeno',
            estado='Publicado',
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
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
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )

        response = self.client.delete(f'/api/libros/{libro.id}')

        self.assertEqual(response.status_code, 200)
        libro.refresh_from_db()
        self.assertFalse(libro.activo)

    def test_actualiza_libro_exitosamente(self):
        self.client.force_login(self.user)
        libro = Libro.objects.create(
            titulo='Libro original',
            sinopsis='Version inicial',
            estado='Publicado',
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )

        response = self.client.put(
            f'/api/libros/{libro.id}',
            data=json.dumps({
                'titulo': 'Libro actualizado',
                'autor': 'Isabel Allende',
                'sinopsis': 'Version actualizada',
                'genero': 'Novela',
                'estado': 'Leyendo',
                'urlImagen': '/media/libros/actualizado.jpg',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        libro.refresh_from_db()
        self.assertEqual(libro.titulo, 'Libro actualizado')
        self.assertEqual(libro.sinopsis, 'Version actualizada')
        self.assertEqual(libro.estado, 'Leyendo')
        self.assertEqual(libro.url_imagen, '/media/libros/actualizado.jpg')
        self.assertEqual(str(libro.autores.first()), 'Isabel Allende')
        self.assertEqual(libro.generos.first().nombre, 'Novela')

    def test_actualiza_stock_al_editar_libro(self):
        self.client.force_login(self.user)
        libro = Libro.objects.create(
            titulo='Libro original',
            sinopsis='Version inicial',
            estado='Publicado',
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )

        response = self.client.put(
            f'/api/libros/{libro.id}',
            data=json.dumps({
                'titulo': 'Libro con stock',
                'autor': 'Isabel Allende',
                'sinopsis': 'Version con varias copias',
                'genero': 'Novela',
                'estado': 'Publicado',
                'urlImagen': libro.url_imagen,
                'cantidadLibros': '3',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Libro.objects.filter(titulo='Libro con stock', usuario_propietario=self.user, activo=True).count(), 3)

        inventario = self.client.get('/api/libros')
        data = inventario.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['stock'], 3)

    def test_reduce_stock_al_editar_desactiva_copias_sobrantes(self):
        self.client.force_login(self.user)
        autor = Autor.objects.create(nombre1='Julio', apellido1='Cortazar')
        genero = Genero.objects.create(nombre='Ficcion')
        libros = []
        for _ in range(3):
            libro = Libro.objects.create(
                titulo='Rayuela',
                sinopsis='Novela experimental.',
                estado='Publicado',
                url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
                usuario_propietario=self.user,
            )
            libro.autores.add(autor)
            libro.generos.add(genero)
            libros.append(libro)

        response = self.client.put(
            f'/api/libros/{libros[-1].id}',
            data=json.dumps({
                'titulo': 'Rayuela editada',
                'autor': 'Julio Cortazar',
                'sinopsis': 'Novela experimental editada.',
                'genero': 'Ficcion',
                'estado': 'Publicado',
                'urlImagen': libros[-1].url_imagen,
                'cantidadLibros': '1',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        libros[-1].refresh_from_db()
        self.assertTrue(libros[-1].activo)
        self.assertEqual(libros[-1].titulo, 'Rayuela editada')
        self.assertEqual(Libro.objects.filter(titulo='Rayuela editada', usuario_propietario=self.user, activo=True).count(), 1)
        self.assertEqual(Libro.objects.filter(titulo='Rayuela', usuario_propietario=self.user, activo=False).count(), 2)

    def test_formulario_edicion_muestra_stock_actual(self):
        self.client.force_login(self.user)
        autor = Autor.objects.create(nombre1='Julio', apellido1='Cortazar')
        genero = Genero.objects.create(nombre='Ficcion')
        libros = []
        for _ in range(3):
            libro = Libro.objects.create(
                titulo='Rayuela',
                sinopsis='Novela experimental.',
                estado='Publicado',
                url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
                usuario_propietario=self.user,
            )
            libro.autores.add(autor)
            libro.generos.add(genero)
            libros.append(libro)

        response = self.client.get(f'/registrar_libro/{libros[0].id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<option value="3" selected>3</option>', html=True)
        self.assertContains(response, 'registrarLibro.js?v=20260505a')

    def test_actualiza_libro_con_nueva_imagen(self):
        self.client.force_login(self.user)
        libro = Libro.objects.create(
            titulo='Libro original',
            sinopsis='Version inicial',
            estado='Publicado',
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )

        portada = SimpleUploadedFile('nueva-portada.jpg', b'fake-image-content', content_type='image/jpeg')
        payload = encode_multipart(
            BOUNDARY,
            {
                'titulo': 'Libro con portada nueva',
                'autor': 'Laura Restrepo',
                'sinopsis': 'Version actualizada con imagen',
                'genero': 'Novela',
                'estado': 'Publicado',
                'url_imagen': libro.url_imagen,
                'imagen': portada,
            },
        )

        response = self.client.generic(
            'PUT',
            f'/api/libros/{libro.id}',
            data=payload,
            content_type=MULTIPART_CONTENT,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['message'],
            'Cloudinary no esta configurado. Agrega tus credenciales en el archivo .env para subir imagenes.',
        )
        libro.refresh_from_db()
        self.assertEqual(libro.titulo, 'Libro original')
        self.assertEqual(libro.url_imagen, '/static/gestion_libros/imgs/libropredeterminado1.png')

    @patch('web.services.books.upload_image_to_cloudinary')
    @patch('web.services.books.is_cloudinary_configured', return_value=True)
    def test_actualiza_libro_con_nueva_imagen_en_cloudinary(self, _, mocked_upload):
        self.client.force_login(self.user)
        libro = Libro.objects.create(
            titulo='Libro original',
            sinopsis='Version inicial',
            estado='Publicado',
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )

        mocked_upload.return_value = 'https://res.cloudinary.com/demo/image/upload/v1/legajo/libros/nueva-portada.jpg'

        portada = SimpleUploadedFile('nueva-portada.jpg', b'fake-image-content', content_type='image/jpeg')
        payload = encode_multipart(
            BOUNDARY,
            {
                'titulo': 'Libro con portada nueva',
                'autor': 'Laura Restrepo',
                'sinopsis': 'Version actualizada con imagen',
                'genero': 'Novela',
                'estado': 'Publicado',
                'url_imagen': libro.url_imagen,
                'imagen': portada,
            },
        )

        response = self.client.generic(
            'PUT',
            f'/api/libros/{libro.id}',
            data=payload,
            content_type=MULTIPART_CONTENT,
        )

        self.assertEqual(response.status_code, 200)
        libro.refresh_from_db()
        self.assertEqual(libro.titulo, 'Libro con portada nueva')
        self.assertEqual(str(libro.autores.first()), 'Laura Restrepo')
        self.assertTrue(libro.url_imagen.startswith('https://res.cloudinary.com/'))
        self.assertNotEqual(libro.url_imagen, '/static/gestion_libros/imgs/libropredeterminado1.png')

    def test_actualizacion_invalida_retorna_error_controlado(self):
        self.client.force_login(self.user)
        libro = Libro.objects.create(
            titulo='Libro original',
            sinopsis='Version inicial',
            estado='Publicado',
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )

        response = self.client.put(
            f'/api/libros/{libro.id}',
            data=json.dumps({
                'titulo': '',
                'autor': 'Autor valido',
                'sinopsis': 'Sinopsis',
                'genero': 'Novela',
                'estado': 'Publicado',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'El titulo es obligatorio.')

    def test_usuario_no_dueno_no_puede_actualizar_ni_eliminar(self):
        other_user = get_user_model().objects.create_user(
            email='propietario@example.com',
            password='Segura123!@#',
            nombre1='Propietario',
            apellido1='Libro',
            direccion='Calle 12',
            ciudad='Bogota',
            telefono=3000000009,
        )
        libro = Libro.objects.create(
            titulo='Libro protegido',
            sinopsis='Privado',
            estado='Publicado',
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=other_user,
        )

        self.client.force_login(self.user)
        update_response = self.client.put(
            f'/api/libros/{libro.id}',
            data=json.dumps({
                'titulo': 'Intento de cambio',
                'autor': 'Autor ajeno',
                'sinopsis': 'Intento',
                'genero': 'Drama',
                'estado': 'Publicado',
            }),
            content_type='application/json',
        )
        delete_response = self.client.delete(f'/api/libros/{libro.id}')

        self.assertEqual(update_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        libro.refresh_from_db()
        self.assertTrue(libro.activo)
        self.assertEqual(libro.titulo, 'Libro protegido')

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
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )
        Libro.objects.create(
            titulo='Libro recomendado',
            sinopsis='De otro usuario',
            estado='Publicado',
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=other_user,
        )

        self.client.force_login(self.user)
        response = self.client.get('/api/libros/recomendados')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['titulo'], 'Libro recomendado')

    def test_recomendados_agrupa_copias_y_devuelve_stock(self):
        other_user = get_user_model().objects.create_user(
            email='stock-recomendado@example.com',
            password='Segura123!@#',
            nombre1='Stock',
            apellido1='Recomendado',
            direccion='Calle 90',
            ciudad='Bogota',
            telefono=3000000012,
        )
        for _ in range(4):
            Libro.objects.create(
                titulo='Libro con stock',
                sinopsis='Varias copias de otro usuario',
                estado='Publicado',
                url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
                usuario_propietario=other_user,
            )

        self.client.force_login(self.user)
        response = self.client.get('/api/libros/recomendados')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['titulo'], 'Libro con stock')
        self.assertEqual(data[0]['stock'], 4)
        self.assertEqual(len(data[0]['idsLibros']), 4)

    def test_recomendados_no_devuelve_libros_en_leyendo(self):
        other_user = get_user_model().objects.create_user(
            email='leyendo-recomendado@example.com',
            password='Segura123!@#',
            nombre1='Lector',
            apellido1='Ocupado',
            direccion='Calle 91',
            ciudad='Bogota',
            telefono=3000000013,
        )
        Libro.objects.create(
            titulo='Libro no disponible',
            sinopsis='Esta en lectura',
            estado=Libro.Estado.LEYENDO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=other_user,
        )
        Libro.objects.create(
            titulo='Libro disponible',
            sinopsis='Se puede intercambiar',
            estado=Libro.Estado.PUBLICADO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=other_user,
        )

        self.client.force_login(self.user)
        response = self.client.get('/api/libros/recomendados')

        self.assertEqual(response.status_code, 200)
        titulos = [libro['titulo'] for libro in response.json()]
        self.assertIn('Libro disponible', titulos)
        self.assertNotIn('Libro no disponible', titulos)

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
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
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

    def test_solicitar_intercambio_rechaza_libro_en_leyendo(self):
        other_user = get_user_model().objects.create_user(
            email='dueno-leyendo@example.com',
            password='Segura123!@#',
            nombre1='Dueno',
            apellido1='Leyendo',
            direccion='Calle 78',
            ciudad='Barranquilla',
            telefono=3000000004,
        )
        libro = Libro.objects.create(
            titulo='Libro ocupado',
            sinopsis='No disponible para intercambio',
            estado=Libro.Estado.LEYENDO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=other_user,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            '/api/intercambios/request',
            data=json.dumps({'libroId': libro.id}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'Este libro no esta disponible para intercambio.')
        self.assertFalse(Intercambio.objects.filter(libro_solicitado=libro).exists())

    def test_completar_intercambio_pone_libros_en_leyendo(self):
        other_user = get_user_model().objects.create_user(
            email='dueno-completa@example.com',
            password='Segura123!@#',
            nombre1='Dueno',
            apellido1='Completa',
            direccion='Calle 79',
            ciudad='Bogota',
            telefono=3000000005,
        )
        libro_solicitado = Libro.objects.create(
            titulo='Libro solicitado final',
            sinopsis='Disponible para intercambio',
            estado=Libro.Estado.PUBLICADO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=other_user,
        )
        libro_cambio = Libro.objects.create(
            titulo='Libro cambio final',
            sinopsis='Disponible para entregar',
            estado=Libro.Estado.PUBLICADO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )
        intercambio = Intercambio.objects.create(
            estado=Intercambio.Estado.ACEPTADO,
            usuario_solicitante=self.user,
            usuario_receptor=other_user,
            libro_solicitado=libro_solicitado,
            libro_cambio=libro_cambio,
        )

        self.client.force_login(self.user)
        primera_confirmacion = self.client.post(
            f'/api/intercambios/{intercambio.id}/confirm',
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(primera_confirmacion.status_code, 200)

        self.client.force_login(other_user)
        segunda_confirmacion = self.client.post(
            f'/api/intercambios/{intercambio.id}/confirm',
            data=json.dumps({}),
            content_type='application/json',
        )

        self.assertEqual(segunda_confirmacion.status_code, 200)
        self.assertTrue(segunda_confirmacion.json()['completado'])
        libro_solicitado.refresh_from_db()
        libro_cambio.refresh_from_db()
        self.assertEqual(libro_solicitado.usuario_propietario, self.user)
        self.assertEqual(libro_cambio.usuario_propietario, other_user)
        self.assertEqual(libro_solicitado.estado, Libro.Estado.LEYENDO)
        self.assertEqual(libro_cambio.estado, Libro.Estado.LEYENDO)


class ImportacionMasivaLibrosTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_user(
            email='admin-libros@example.com',
            password='Segura123!@#',
            nombre1='Admin',
            apellido1='Libros',
            direccion='Calle 1',
            ciudad='Bogota',
            telefono=3001112233,
            rol=self.user_model.Rol.ADMIN,
        )
        self.owner = self.user_model.objects.create_user(
            email='dueno-libro@example.com',
            password='Segura123!@#',
            nombre1='Dueno',
            apellido1='Libro',
            direccion='Calle 2',
            ciudad='Bogota',
            telefono=3001112244,
        )

    def test_reporte_libros_no_acepta_importacion_masiva(self):
        self.client.force_login(self.admin)
        archivo = SimpleUploadedFile(
            'libros.json',
            json.dumps({
                'libros': [
                    {
                        'nombre': 'Pedro Paramo',
                        'author': 'Juan Rulfo',
                        'descripcion': 'Novela latinoamericana.',
                        'categoria': 'Ficcion',
                        'correo': 'dueno-libro@example.com',
                        'portada': 'https://res.cloudinary.com/demo/image/upload/v1/pedro-paramo.jpg',
                    }
                ]
            }).encode('utf-8'),
            content_type='application/json',
        )

        response = self.client.post('/reporte_libros/', data={'archivo_libros': archivo}, follow=True)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(Libro.objects.filter(titulo='Pedro Paramo').exists())

    def test_admin_no_puede_crear_libros_desde_api(self):
        Libro.objects.create(
            titulo='El Aleph',
            sinopsis='Ya existe',
            estado='Publicado',
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.owner,
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            '/api/libros',
            data={
                'titulo': 'El Aleph nuevo',
                'autor': 'Jorge Luis Borges',
                'sinopsis': 'Intento admin',
                'genero': 'Ficcion',
                'estado': 'Publicado',
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['message'], 'Los administradores no pueden registrar libros para intercambio.')
        self.assertEqual(Libro.objects.filter(titulo='El Aleph', usuario_propietario=self.owner).count(), 1)
        self.assertFalse(Libro.objects.filter(titulo='El Aleph nuevo').exists())

    def test_admin_inactiva_libro_y_notifica_propietario(self):
        libro = Libro.objects.create(
            titulo='Libro con reporte admin',
            sinopsis='Contenido a revisar',
            estado=Libro.Estado.PUBLICADO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.owner,
        )
        self.client.force_login(self.admin)

        response = self.client.patch(
            f'/api/admin/libros/{libro.id}/estado',
            data=json.dumps({
                'activo': False,
                'motivo': 'La publicacion incumple las normas de la comunidad.',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        libro.refresh_from_db()
        self.assertFalse(libro.activo)
        self.assertTrue(
            NotificacionUsuario.objects.filter(
                usuario=self.owner,
                mensaje__icontains='La publicacion incumple las normas de la comunidad.',
            ).exists()
        )

    def test_reporte_admin_libros_incluye_inactivos(self):
        Libro.objects.create(
            titulo='Libro inactivo visible',
            sinopsis='Debe aparecer en reporte',
            estado=Libro.Estado.PUBLICADO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.owner,
            activo=False,
        )
        self.client.force_login(self.admin)

        response = self.client.get('/api/admin/libros/reporte')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['titulo'], 'Libro inactivo visible')
        self.assertFalse(data[0]['activo'])


class ImportacionMasivaUsuariosAjaxTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_user(
            email='admin-ajax@example.com',
            password='Segura123!@#',
            nombre1='Admin',
            apellido1='Ajax',
            direccion='Calle 10',
            ciudad='Bogota',
            telefono=3009991111,
            rol=self.user_model.Rol.ADMIN,
        )

    def test_importacion_usuarios_ajax_retorna_json_de_exito(self):
        self.client.force_login(self.admin)
        archivo = SimpleUploadedFile(
            'usuarios.json',
            json.dumps([
                {
                    'correo': 'nuevo-ajax@example.com',
                    'primerNombre': 'Nuevo',
                    'primerApellido': 'Ajax',
                    'direccion': 'Calle 11',
                    'ciudad': 'Bogota',
                    'telefono': '3005554444',
                    'clave': 'Segura123!@#',
                }
            ]).encode('utf-8'),
            content_type='application/json',
        )

        response = self.client.post(
            '/usuarios_admin/',
            data={'archivo_usuarios': archivo},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('Importacion completada.', data['message'])
        self.assertEqual(data['resultado']['creados'], 1)
        self.assertTrue(self.user_model.objects.filter(email='nuevo-ajax@example.com').exists())

    def test_admin_desactiva_usuario_con_motivo(self):
        usuario = self.user_model.objects.create_user(
            email='usuario-desactivar@example.com',
            password='Segura123!@#',
            nombre1='Usuario',
            apellido1='Desactivar',
            direccion='Calle 12',
            ciudad='Bogota',
            telefono=3005554445,
        )
        self.client.force_login(self.admin)

        response = self.client.patch(
            f'/api/admin/usuarios/{usuario.id}/estado',
            data=json.dumps({
                'activo': False,
                'motivo': 'Incumplimiento de normas de intercambio.',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        usuario.refresh_from_db()
        self.assertFalse(usuario.activo)
        self.assertFalse(usuario.is_active)
        self.assertEqual(usuario.motivo_desactivacion, 'Incumplimiento de normas de intercambio.')
        self.assertEqual(response.json()['usuario']['motivoDesactivacion'], 'Incumplimiento de normas de intercambio.')

    def test_admin_no_desactiva_usuario_sin_motivo(self):
        usuario = self.user_model.objects.create_user(
            email='usuario-sin-motivo@example.com',
            password='Segura123!@#',
            nombre1='Usuario',
            apellido1='Sinmotivo',
            direccion='Calle 13',
            ciudad='Bogota',
            telefono=3005554446,
        )
        self.client.force_login(self.admin)

        response = self.client.patch(
            f'/api/admin/usuarios/{usuario.id}/estado',
            data=json.dumps({
                'activo': False,
                'motivo': 'Corto',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        usuario.refresh_from_db()
        self.assertTrue(usuario.activo)
        self.assertTrue(usuario.is_active)

    def test_admin_consulta_inventario_de_usuario(self):
        usuario = self.user_model.objects.create_user(
            email='usuario-inventario-admin@example.com',
            password='Segura123!@#',
            nombre1='Usuario',
            apellido1='Inventario',
            direccion='Calle 14',
            ciudad='Bogota',
            telefono=3005554447,
        )
        Libro.objects.create(
            titulo='Libro visible para admin',
            sinopsis='Inventario consultable',
            estado=Libro.Estado.PUBLICADO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=usuario,
        )
        self.client.force_login(self.admin)

        response = self.client.get(f'/api/admin/usuarios/{usuario.id}/inventario')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['usuario']['correo'], 'usuario-inventario-admin@example.com')
        self.assertEqual(len(data['libros']), 1)
        self.assertEqual(data['libros'][0]['titulo'], 'Libro visible para admin')


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_user(
            email='admin-dashboard@example.com',
            password='Segura123!@#',
            nombre1='Admin',
            apellido1='Dashboard',
            direccion='Calle 1',
            ciudad='Bogota',
            telefono=3001111111,
            rol=self.user_model.Rol.ADMIN,
        )
        self.reportante = self.user_model.objects.create_user(
            email='reportante@example.com',
            password='Segura123!@#',
            nombre1='Reporte',
            apellido1='Uno',
            direccion='Calle 2',
            ciudad='Bogota',
            telefono=3002222222,
        )
        self.reportado = self.user_model.objects.create_user(
            email='reportado@example.com',
            password='Segura123!@#',
            nombre1='Reportado',
            apellido1='Dos',
            direccion='Calle 3',
            ciudad='Bogota',
            telefono=3003333333,
        )

    def test_dashboard_admin_contexto_calcula_metricas_reales(self):
        libro = Libro.objects.create(
            titulo='Libro admin',
            sinopsis='Disponible',
            estado=Libro.Estado.LEYENDO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.reportado,
        )
        ReporteUsuario.objects.create(
            motivo='Spam',
            descripcion='Descripcion',
            estado=ReporteUsuario.Estado.PENDIENTE,
            usuario_reportante=self.reportante,
            usuario_reportado=self.reportado,
        )
        Intercambio.objects.create(
            estado=Intercambio.Estado.PENDIENTE,
            usuario_solicitante=self.reportante,
            usuario_receptor=self.reportado,
            libro_solicitado=libro,
            libro_cambio=None,
        )

        context = _get_admin_dashboard_context()

        self.assertEqual(context['admin_stats']['usuarios_total'], self.user_model.objects.filter(activo=True).count())
        self.assertEqual(context['admin_stats']['libros_total'], Libro.objects.filter(activo=True).count())
        self.assertEqual(context['admin_stats']['libros_leyendo'], Libro.objects.filter(activo=True, estado=Libro.Estado.LEYENDO).count())
        self.assertEqual(context['admin_stats']['reportes_total'], ReporteUsuario.objects.filter(activo=True).count())
        self.assertEqual(
            context['admin_stats']['reportes_pendientes'],
            ReporteUsuario.objects.filter(activo=True, estado=ReporteUsuario.Estado.PENDIENTE).count(),
        )
        self.assertEqual(
            context['admin_stats']['intercambios_pendientes'],
            Intercambio.objects.filter(activo=True, estado=Intercambio.Estado.PENDIENTE).count(),
        )
        self.assertIn('usuarios_por_mes', context['admin_charts'])
        self.assertIn('reportes_por_mes', context['admin_charts'])
        self.assertIn('intercambios_por_estado', context['admin_charts'])
        self.assertIn('usuarios_por_ciudad', context['admin_charts'])
        self.assertTrue(len(context['admin_charts']['usuarios_por_mes']['labels']) >= 6)

    def test_dashboard_admin_reported_users_endpoint_devuelve_datos_reales(self):
        reporte = ReporteUsuario.objects.create(
            motivo='Incumplimiento',
            descripcion='Descripcion',
            estado=ReporteUsuario.Estado.PENDIENTE,
            usuario_reportante=self.reportante,
            usuario_reportado=self.reportado,
        )
        hoy = timezone.localtime().replace(day=3, hour=10, minute=0, second=0, microsecond=0)
        ReporteUsuario.objects.filter(id=reporte.id).update(fecha_reporte=hoy)

        self.client.force_login(self.admin)
        response = self.client.get('/api/admin/dashboard/reported-users')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['labels']), len(data['data']))
        self.assertEqual(data['data'][2], 1)
        self.assertGreaterEqual(data['data'][-1], 1)


class UserReportsTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_user(
            email='admin-reportes@example.com',
            password='Segura123!@#',
            nombre1='Admin',
            apellido1='Moderacion',
            direccion='Calle 10',
            ciudad='Bogota',
            telefono=3004444444,
            rol=self.user_model.Rol.ADMIN,
        )
        self.reportante = self.user_model.objects.create_user(
            email='lector-reporta@example.com',
            password='Segura123!@#',
            nombre1='Lector',
            apellido1='Reporta',
            direccion='Calle 11',
            ciudad='Bogota',
            telefono=3005555555,
        )
        self.reportado = self.user_model.objects.create_user(
            email='usuario-reportado@example.com',
            password='Segura123!@#',
            nombre1='Usuario',
            apellido1='Conflictivo',
            direccion='Calle 12',
            ciudad='Medellin',
            telefono=3006666666,
        )

    def test_usuario_puede_reportar_a_otro_usuario(self):
        libro = Libro.objects.create(
            titulo='Libro reportado por usuario',
            sinopsis='Disponible',
            estado=Libro.Estado.PUBLICADO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.reportado,
        )
        self.client.force_login(self.reportante)

        response = self.client.post(
            '/api/reportes-usuarios',
            data=json.dumps({
                'usuarioReportadoId': self.reportado.id,
                'libroReportadoId': libro.id,
                'motivo': 'Incumplimiento de intercambio',
                'descripcion': 'No entrego el libro acordado despues de aceptar el intercambio.',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            ReporteUsuario.objects.filter(
                usuario_reportante=self.reportante,
                usuario_reportado=self.reportado,
                libro_reportado=libro,
                estado=ReporteUsuario.Estado.PENDIENTE,
            ).exists()
        )

    def test_admin_ve_libro_reportado_en_novedades(self):
        libro = Libro.objects.create(
            titulo='Libro visible en novedades',
            sinopsis='Reporte con libro',
            estado=Libro.Estado.PUBLICADO,
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.reportado,
        )
        ReporteUsuario.objects.create(
            motivo='Spam o contenido ofensivo',
            descripcion='El reporte incluye libro.',
            estado=ReporteUsuario.Estado.PENDIENTE,
            usuario_reportante=self.reportante,
            usuario_reportado=self.reportado,
            libro_reportado=libro,
        )
        self.client.force_login(self.admin)

        response = self.client.get('/api/admin/reportes-usuarios')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0]['libroReportado'], 'Libro visible en novedades')
        self.assertEqual(data[0]['libroReportadoId'], libro.id)

    def test_usuario_no_puede_reportarse_a_si_mismo(self):
        self.client.force_login(self.reportante)

        response = self.client.post(
            '/api/reportes-usuarios',
            data=json.dumps({
                'usuarioReportadoId': self.reportante.id,
                'motivo': 'Mal comportamiento',
                'descripcion': 'Intento invalidar el sistema de reportes.',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'No puedes reportarte a ti mismo.')

    def test_admin_puede_listar_y_actualizar_reportes(self):
        reporte = ReporteUsuario.objects.create(
            motivo='Spam o contenido ofensivo',
            descripcion='Envio mensajes ofensivos repetidos en el chat.',
            estado=ReporteUsuario.Estado.PENDIENTE,
            usuario_reportante=self.reportante,
            usuario_reportado=self.reportado,
        )

        self.client.force_login(self.admin)

        list_response = self.client.get('/api/admin/reportes-usuarios')
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        patch_response = self.client.patch(
            f'/api/admin/reportes-usuarios/{reporte.id}',
            data=json.dumps({'estado': 'revisado'}),
            content_type='application/json',
        )
        self.assertEqual(patch_response.status_code, 200)

        reporte.refresh_from_db()
        self.assertEqual(reporte.estado, ReporteUsuario.Estado.REVISADO)
        self.assertTrue(
            NotificacionUsuario.objects.filter(
                usuario=self.reportante,
                reporte_relacionado=reporte,
            ).exists()
        )

    def test_usuario_ve_notificacion_cuando_su_reporte_es_revisado(self):
        reporte = ReporteUsuario.objects.create(
            motivo='Incumplimiento de intercambio',
            descripcion='No entrego el libro y dejo de responder.',
            estado=ReporteUsuario.Estado.PENDIENTE,
            usuario_reportante=self.reportante,
            usuario_reportado=self.reportado,
        )

        self.client.force_login(self.admin)
        self.client.patch(
            f'/api/admin/reportes-usuarios/{reporte.id}',
            data=json.dumps({'estado': 'revisado'}),
            content_type='application/json',
        )

        self.client.force_login(self.reportante)
        response = self.client.get('/api/notificaciones')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(
            item['tipo'] == 'sistema' and 'se tomaron las medidas correspondientes' in item['mensaje']
            for item in data
        ))

    def test_admin_envia_respuesta_personalizada_al_resolver_reporte(self):
        reporte = ReporteUsuario.objects.create(
            motivo='Spam o contenido ofensivo',
            descripcion='Envio mensajes ofensivos repetidos en el chat.',
            estado=ReporteUsuario.Estado.PENDIENTE,
            usuario_reportante=self.reportante,
            usuario_reportado=self.reportado,
        )
        mensaje = 'Revisamos tu reporte y aplicamos las medidas correspondientes.'

        self.client.force_login(self.admin)
        response = self.client.patch(
            f'/api/admin/reportes-usuarios/{reporte.id}',
            data=json.dumps({
                'estado': 'revisado',
                'mensaje': mensaje,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        notificacion = NotificacionUsuario.objects.get(
            usuario=self.reportante,
            reporte_relacionado=reporte,
        )
        self.assertIn('Tu reporte fue revisado y confirmado', notificacion.mensaje)
        self.assertIn(mensaje, notificacion.mensaje)

    def test_admin_envia_respuesta_personalizada_al_descartar_reporte(self):
        reporte = ReporteUsuario.objects.create(
            motivo='Mal comportamiento',
            descripcion='La situacion no tenia evidencia suficiente.',
            estado=ReporteUsuario.Estado.PENDIENTE,
            usuario_reportante=self.reportante,
            usuario_reportado=self.reportado,
        )
        mensaje = 'No encontramos evidencia suficiente para tomar medidas.'

        self.client.force_login(self.admin)
        response = self.client.patch(
            f'/api/admin/reportes-usuarios/{reporte.id}',
            data=json.dumps({
                'estado': 'descartado',
                'mensaje': mensaje,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        notificacion = NotificacionUsuario.objects.get(
            usuario=self.reportante,
            reporte_relacionado=reporte,
        )
        self.assertIn('Tu reporte fue descartado', notificacion.mensaje)
        self.assertIn(mensaje, notificacion.mensaje)

    def test_usuario_ve_notificacion_cuando_su_reporte_es_descartado(self):
        reporte = ReporteUsuario.objects.create(
            motivo='Mal comportamiento',
            descripcion='La situacion no tenia evidencia suficiente.',
            estado=ReporteUsuario.Estado.PENDIENTE,
            usuario_reportante=self.reportante,
            usuario_reportado=self.reportado,
        )

        self.client.force_login(self.admin)
        self.client.patch(
            f'/api/admin/reportes-usuarios/{reporte.id}',
            data=json.dumps({'estado': 'descartado'}),
            content_type='application/json',
        )

        self.client.force_login(self.reportante)
        response = self.client.get('/api/notificaciones')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(
            item['tipo'] == 'sistema' and 'no se encontraron motivos justificables' in item['mensaje']
            for item in data
        ))

    def test_usuario_ve_notificacion_sintetica_si_no_existe_registro_persistente(self):
        ReporteUsuario.objects.create(
            motivo='Mal comportamiento',
            descripcion='Se reviso el caso aunque no exista notificacion persistente.',
            estado=ReporteUsuario.Estado.REVISADO,
            usuario_reportante=self.reportante,
            usuario_reportado=self.reportado,
        )

        self.client.force_login(self.reportante)
        response = self.client.get('/api/notificaciones')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(
            item['tipo'] == 'sistema' and 'se tomaron las medidas correspondientes' in item['mensaje']
            for item in data
        ))

    def test_dashboard_admin_completed_exchanges_endpoint_devuelve_datos_reales(self):
        libro = Libro.objects.create(
            titulo='Libro intercambio',
            sinopsis='Disponible',
            estado='Publicado',
            url_imagen='/static/gestion_libros/imgs/libropredeterminado1.png',
            usuario_propietario=self.reportado,
        )
        intercambio = Intercambio.objects.create(
            estado=Intercambio.Estado.COMPLETADO,
            usuario_solicitante=self.reportante,
            usuario_receptor=self.reportado,
            libro_solicitado=libro,
            libro_cambio=None,
        )
        completado = timezone.localtime().replace(day=5, hour=12, minute=0, second=0, microsecond=0)
        Intercambio.objects.filter(id=intercambio.id).update(fecha_completado=completado)

        self.client.force_login(self.admin)
        response = self.client.get('/api/admin/dashboard/completed-exchanges')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['labels']), len(data['data']))
        self.assertEqual(data['data'][4], 1)
        self.assertGreaterEqual(data['data'][-1], 1)


