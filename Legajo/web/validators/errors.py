# Base de errores controlados para traducir fallos de negocio a respuestas HTTP coherentes.
class ControlledError(Exception):
    # Error padre: cualquier fallo esperado del negocio sale de aqui.
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationServiceError(ControlledError):
    # Se usa cuando los datos vienen mal formados, faltan campos o no cumplen reglas.
    status_code = 400


class PermissionDeniedServiceError(ControlledError):
    # Se usa cuando el usuario esta autenticado pero no tiene permiso para la accion.
    status_code = 403


class NotFoundServiceError(ControlledError):
    # Se usa cuando el recurso pedido no existe o ya no esta disponible.
    status_code = 404


class DatabaseServiceError(ControlledError):
    # Se usa cuando falla la base de datos o una operacion interna de persistencia.
    status_code = 500

    def __init__(self, message='Ocurrio un error al procesar la solicitud.'):
        super().__init__(message, status_code=self.status_code)


class ExternalServiceError(ControlledError):
    # Se usa cuando falla un servicio externo, por ejemplo Cloudinary.
    status_code = 502

    def __init__(self, message='No se pudo completar la conexion con el servicio externo.'):
        super().__init__(message, status_code=self.status_code)
