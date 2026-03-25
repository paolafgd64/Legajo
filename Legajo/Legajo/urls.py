"""
URL configuration for Legajo project.
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from web import views


urlpatterns = [
    path('', views.index, name='index'),
    path('admin/', admin.site.urls),
    path('chats/', views.chats, name='chats'),
    path('crear_cuenta/', views.crear_cuenta, name='crear_cuenta'),
    path('dashboard_admin/', views.dashboard_admin, name='dashboard_admin'),
    path('api/admin/dashboard/reported-users', views.api_admin_reported_users, name='api_admin_reported_users'),
    path('api/admin/dashboard/completed-exchanges', views.api_admin_completed_exchanges, name='api_admin_completed_exchanges'),
    path('dashboard_usuario/', views.dashboard_usuario, name='dashboard_usuario'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('inventario_admi/', views.inventario_admi, name='inventario_admi'),
    path('inventario/', views.inventario, name='inventario'),
    path('login/', views.login, name='login'),
    path('notificaciones/', views.notificaciones, name='notificaciones'),
    path('novedades_usuarios/', views.novedades_usuarios, name='novedades_usuarios'),
    path('perfil_admin/', views.perfil_admin, name='perfil_admin'),
    path('perfil/', views.perfil, name='perfil'),
    path('registrar_libro/', views.registrar_libro, name='registrar_libro'),
    path('registrar_libro/<int:libro_id>/', views.registrar_libro, name='editar_libro'),
    path('reporte_libros/', views.reporte_libros, name='reporte_libros'),
    path('libros/reporte/pdf', views.reporte_libros_pdf, name='reporte_libros_pdf'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('api/usuarios', views.api_usuarios, name='api_usuarios'),
    path('api/usuarios/', views.api_usuarios, name='api_usuarios_slash'),
    path('api/login/', views.api_login, name='api_login_legacy'),
    path('api/auth/login', views.api_login, name='api_login'),
    path('api/me/', views.api_me, name='api_me'),
    path('api/auth/me', views.api_me, name='api_auth_me'),
    path('api/libros', views.api_libros, name='api_libros'),
    path('api/libros/recomendados', views.api_libros_recomendados, name='api_libros_recomendados'),
    path('api/libros/<int:libro_id>', views.api_libro_detalle, name='api_libro_detalle'),
    path('api/libros/<int:libro_id>/', views.api_libro_detalle, name='api_libro_detalle_slash'),
    path('api/notificaciones', views.api_notificaciones, name='api_notificaciones'),
    path('api/intercambios', views.api_intercambios, name='api_intercambios'),
    path('api/intercambios/<int:intercambio_id>/inventario', views.api_inventario_solicitante_intercambio, name='api_inventario_solicitante_intercambio'),
    path('api/intercambios/<int:intercambio_id>/accept', views.api_aceptar_intercambio, name='api_aceptar_intercambio'),
    path('api/intercambios/<int:intercambio_id>/confirm', views.api_confirmar_intercambio_pin, name='api_confirmar_intercambio_pin'),
    path('api/intercambios/request', views.api_solicitar_intercambio, name='api_solicitar_intercambio'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
