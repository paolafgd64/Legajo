"""Punto de agregacion de modelos del app `web`.

Se conserva para que Django siga resolviendo `AUTH_USER_MODEL = "web.Usuario"`
y para que imports antiguos como `from web.models import Libro` sigan funcionando.
La implementacion real vive dentro de los modulos de dominio.
"""

from .administracion.models import NotificacionUsuario, ReporteUsuario
from .gestion_libros.models import Autor, CalificacionLibro, Genero, Libro
from .intercambios.models import Intercambio
from .usuarios.models import Usuario, UsuarioManager


__all__ = [
    'Autor',
    'CalificacionLibro',
    'Genero',
    'Intercambio',
    'Libro',
    'NotificacionUsuario',
    'ReporteUsuario',
    'Usuario',
    'UsuarioManager',
]
