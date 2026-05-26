"""Router principal de la app `web`.

Cada include delega a un modulo funcional distinto para evitar volver a un
`urls.py` monolitico.
"""

from django.http import HttpResponse
from django.urls import include, path
from .views import ping


urlpatterns = [
    path('', include('web.usuarios.urls')),
    path('', include('web.administracion.urls')),
    path('', include('web.gestion_libros.urls')),
    path('', include('web.intercambios.urls')),
    path("ping/", ping, name="ping"),
]
