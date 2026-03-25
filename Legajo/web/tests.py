import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from .models import Autor, Intercambio, Libro, ReporteUsuario
from .views import _get_admin_dashboard_context


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

        self.assertEqual(response.status_code, 302)
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

    def test_actualiza_libro_exitosamente(self):
        self.client.force_login(self.user)
        libro = Libro.objects.create(
            titulo='Libro original',
            sinopsis='Version inicial',
            estado='Publicado',
            url_imagen='/static/web/imgs/libro_de_la_selva.jpg',
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

    def test_actualizacion_invalida_retorna_error_controlado(self):
        self.client.force_login(self.user)
        libro = Libro.objects.create(
            titulo='Libro original',
            sinopsis='Version inicial',
            estado='Publicado',
            url_imagen='/static/web/imgs/libro_de_la_selva.jpg',
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
            url_imagen='/static/web/imgs/libro_de_la_selva.jpg',
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
        ReporteUsuario.objects.create(
            motivo='Spam',
            descripcion='Descripcion',
            estado=ReporteUsuario.Estado.PENDIENTE,
            usuario_reportante=self.reportante,
            usuario_reportado=self.reportado,
        )

        context = _get_admin_dashboard_context()

        self.assertEqual(context['admin_stats']['usuarios_total'], self.user_model.objects.filter(activo=True).count())
        self.assertEqual(context['admin_stats']['reportes_total'], ReporteUsuario.objects.filter(activo=True).count())

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

    def test_dashboard_admin_completed_exchanges_endpoint_devuelve_datos_reales(self):
        libro = Libro.objects.create(
            titulo='Libro intercambio',
            sinopsis='Disponible',
            estado='Publicado',
            url_imagen='/static/web/imgs/libro_de_la_selva.jpg',
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
