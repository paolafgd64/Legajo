import json

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone

from .models import Autor, Intercambio, Libro, NotificacionUsuario, ReporteUsuario
from .views.helpers import _build_password_reset_link, _get_admin_dashboard_context, _get_password_reset_user


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
            url_imagen='/static/web/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )
        Libro.objects.create(
            titulo='Libro ajeno',
            sinopsis='Ajeno',
            estado='Publicado',
            url_imagen='/static/web/imgs/libropredeterminado1.png',
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
            url_imagen='/static/web/imgs/libropredeterminado1.png',
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
            url_imagen='/static/web/imgs/libropredeterminado1.png',
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

    def test_actualiza_libro_con_nueva_imagen(self):
        self.client.force_login(self.user)
        libro = Libro.objects.create(
            titulo='Libro original',
            sinopsis='Version inicial',
            estado='Publicado',
            url_imagen='/static/web/imgs/libropredeterminado1.png',
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

        self.assertEqual(response.status_code, 200)
        libro.refresh_from_db()
        self.assertEqual(libro.titulo, 'Libro con portada nueva')
        self.assertEqual(str(libro.autores.first()), 'Laura Restrepo')
        self.assertTrue(libro.url_imagen.startswith('/media/libros/'))
        self.assertNotEqual(libro.url_imagen, '/static/web/imgs/libropredeterminado1.png')

    def test_actualizacion_invalida_retorna_error_controlado(self):
        self.client.force_login(self.user)
        libro = Libro.objects.create(
            titulo='Libro original',
            sinopsis='Version inicial',
            estado='Publicado',
            url_imagen='/static/web/imgs/libropredeterminado1.png',
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
            url_imagen='/static/web/imgs/libropredeterminado1.png',
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
            url_imagen='/static/web/imgs/libropredeterminado1.png',
            usuario_propietario=self.user,
        )
        Libro.objects.create(
            titulo='Libro recomendado',
            sinopsis='De otro usuario',
            estado='Publicado',
            url_imagen='/static/web/imgs/libropredeterminado1.png',
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
            url_imagen='/static/web/imgs/libropredeterminado1.png',
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
        libro = Libro.objects.create(
            titulo='Libro admin',
            sinopsis='Disponible',
            estado=Libro.Estado.LEYENDO,
            url_imagen='/static/web/imgs/libropredeterminado1.png',
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
        self.client.force_login(self.reportante)

        response = self.client.post(
            '/api/reportes-usuarios',
            data=json.dumps({
                'usuarioReportadoId': self.reportado.id,
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
                estado=ReporteUsuario.Estado.PENDIENTE,
            ).exists()
        )

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
            url_imagen='/static/web/imgs/libropredeterminado1.png',
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
