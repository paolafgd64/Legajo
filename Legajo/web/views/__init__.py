# VIEWS ORGANIZADAS POR CAPACIDAD (Programacion Orientada a Objetos)
# Importa todas las views para compatibilidad con urls.py

# Auth Views (Autenticación, Registro, Contraseña)
from .auth import (
    crear_cuenta,
    login,
    logout_view,
    api_usuarios,
    api_login,
    api_me,
    forgot_password,
    reset_password,
)

# Books Views (Gestión de Libros)
from .books import (
    api_libros,
    api_libros_recomendados,
    api_libro_detalle,
    registrar_libro,
    reporte_libros,
    reporte_libros_pdf,
)

# Exchanges Views (Intercambios de Libros)
from .exchanges import (
    api_intercambios,
    api_solicitar_intercambio,
    api_aceptar_intercambio,
    api_confirmar_intercambio_pin,
    api_notificaciones,
    api_inventario_solicitante_intercambio,
)

# Admin Views (Panel Administrativo)
from .admin import (
    dashboard_admin,
    usuarios_admin,
    carga_masiva_usuarios,
    api_admin_users,
    api_admin_reported_users,
    api_admin_completed_exchanges,
    api_admin_user_reports,
    api_admin_update_user_report,
    inventario_admi,
    perfil_admin,
)

# Dashboard Views (UI: Dashboard, Perfil, etc)
from .dashboard import (
    index,
    dashboard_usuario,
    chats,
    perfil,
    notificaciones,
    novedades_usuarios,
    inventario,
    api_user_reports,
)

__all__ = [
    # Auth
    'crear_cuenta', 'login', 'logout_view', 'api_usuarios', 'api_login', 'api_me',
    'forgot_password', 'reset_password',
    # Books
    'api_libros', 'api_libros_recomendados', 'api_libro_detalle', 'registrar_libro',
    'reporte_libros', 'reporte_libros_pdf',
    # Exchanges
    'api_intercambios', 'api_solicitar_intercambio', 'api_aceptar_intercambio',
    'api_confirmar_intercambio_pin', 'api_notificaciones',
    'api_inventario_solicitante_intercambio',
    # Admin
    'dashboard_admin', 'usuarios_admin', 'carga_masiva_usuarios', 'api_admin_users',
    'api_admin_reported_users', 'api_admin_completed_exchanges', 'api_admin_user_reports',
    'api_admin_update_user_report', 'inventario_admi',
    'perfil_admin',
    # Dashboard
    'index', 'dashboard_usuario', 'chats', 'perfil', 'notificaciones',
    'novedades_usuarios', 'inventario', 'api_user_reports',
]
