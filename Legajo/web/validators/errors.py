class ControlledError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationServiceError(ControlledError):
    status_code = 400


class PermissionDeniedServiceError(ControlledError):
    status_code = 403


class NotFoundServiceError(ControlledError):
    status_code = 404


class DatabaseServiceError(ControlledError):
    status_code = 500

    def __init__(self, message='Ocurrio un error al procesar la solicitud.'):
        super().__init__(message, status_code=self.status_code)
