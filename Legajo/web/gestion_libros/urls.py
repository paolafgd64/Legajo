from django.urls import path

from . import views


urlpatterns = [
    path('registrar_libro/', views.registrar_libro, name='registrar_libro'),
    path('registrar_libro/<int:libro_id>/', views.registrar_libro, name='editar_libro'),
    path('reporte_libros/', views.reporte_libros, name='reporte_libros'),
    path('libros/reporte/pdf', views.reporte_libros_pdf, name='reporte_libros_pdf'),
    path('api/libros', views.api_libros, name='api_libros'),
    path('api/libros/recomendados', views.api_libros_recomendados, name='api_libros_recomendados'),
    path('api/libros/<int:libro_id>', views.api_libro_detalle, name='api_libro_detalle'),
    path('api/libros/<int:libro_id>/', views.api_libro_detalle, name='api_libro_detalle_slash'),
]

