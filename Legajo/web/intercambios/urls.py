from django.urls import path

from . import views


urlpatterns = [
    path('intercambios/', views.intercambios, name='intercambios'),
    path('api/notificaciones', views.api_notificaciones, name='api_notificaciones'),
    path('api/notificaciones/marcar-leidas', views.api_marcar_notificaciones_leidas, name='api_marcar_notificaciones_leidas'),
    path('api/intercambios', views.api_intercambios, name='api_intercambios'),
    path('api/intercambios/request', views.api_solicitar_intercambio, name='api_solicitar_intercambio'),
    path('api/intercambios/<int:intercambio_id>/inventario', views.api_inventario_solicitante_intercambio, name='api_inventario_solicitante_intercambio'),
    path('api/intercambios/<int:intercambio_id>/accept', views.api_aceptar_intercambio, name='api_aceptar_intercambio'),
    path('api/intercambios/<int:intercambio_id>/reject', views.api_rechazar_intercambio, name='api_rechazar_intercambio'),
    path('api/intercambios/<int:intercambio_id>/cancel', views.api_cancelar_intercambio, name='api_cancelar_intercambio'),
    path('api/intercambios/<int:intercambio_id>/confirm', views.api_confirmar_intercambio_pin, name='api_confirmar_intercambio_pin'),
]
