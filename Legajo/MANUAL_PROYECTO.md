# Manual Del Proyecto Legajo

## 1. Idea general

Legajo es una aplicacion Django organizada por dominios funcionales.  
La app principal sigue llamandose `web`, pero por dentro ya no esta pensada
como un bloque unico.

Cada modulo tiene sus propios archivos:

- `models.py`: define datos y relaciones de base de datos.
- `views.py`: recibe requests HTTP y devuelve HTML o JSON.
- `urls.py`: conecta rutas con las views del modulo.
- `templates/<modulo>/`: contiene las plantillas HTML de ese dominio.
- `static/<modulo>/`: contiene JS, CSS e imagenes de ese dominio.

## 2. Mapa rapido de carpetas

### `web/usuarios`

Responsable de:

- login
- logout
- registro
- recuperacion de contrasena
- perfil del usuario
- dashboard del usuario
- reportes que un usuario crea sobre otro usuario

Archivos clave:

- `web/usuarios/models.py`
- `web/usuarios/views.py`
- `web/usuarios/urls.py`
- `web/usuarios/templates/usuarios/`
- `web/usuarios/static/usuarios/`

### `web/administracion`

Responsable de:

- dashboard del administrador
- carga masiva de usuarios
- consulta de usuarios
- revision de reportes
- notificaciones administrativas

Archivos clave:

- `web/administracion/models.py`
- `web/administracion/views.py`
- `web/administracion/urls.py`
- `web/administracion/helpers.py`
- `web/administracion/templates/administracion/`
- `web/administracion/static/administracion/`

### `web/intercambios`

Responsable de:

- solicitar intercambio
- aceptar intercambio
- listar intercambios
- confirmar intercambio por ambas partes
- notificaciones relacionadas con intercambios

Archivos clave:

- `web/intercambios/models.py`
- `web/intercambios/views.py`
- `web/intercambios/urls.py`
- `web/intercambios/templates/intercambios/`
- `web/intercambios/static/intercambios/`

### `web/gestion_libros`

Responsable de:

- CRUD de libros
- inventario
- recomendaciones
- carga masiva de libros
- reporte PDF de libros

Archivos clave:

- `web/gestion_libros/models.py`
- `web/gestion_libros/views.py`
- `web/gestion_libros/urls.py`
- `web/gestion_libros/templates/gestion_libros/`
- `web/gestion_libros/static/gestion_libros/`

### `web/services`

Aqui va la logica de negocio reusable.  
Regla practica:

- si una funcion solo responde HTTP, va en `views.py`
- si una funcion valida, consulta o guarda datos con reglas de negocio, va en `services`

Archivos clave:

- `web/services/books.py`
- `web/services/users.py`
- `web/services/exchanges.py`
- `web/services/serialization.py`
- `web/services/cloudinary.py`

### `web/validators`

Aqui viven las validaciones reutilizables y errores controlados.

Archivos clave:

- `web/validators/books.py`
- `web/validators/exchanges.py`
- `web/validators/passwords.py`
- `web/validators/errors.py`

### `web/views/helpers.py`

Aunque el proyecto ya esta modularizado, este archivo sigue siendo util como
bolsa de helpers compartidos:

- leer JSON del request
- respuestas comunes de error
- construccion de PDF
- utilidades de recuperacion de contrasena

Si en el futuro quieres limpiar aun mas, este archivo puede dividirse en:

- `web/common/http.py`
- `web/common/pdf.py`
- `web/common/auth.py`

## 3. Como descubre Django los templates y estaticos

Como los modulos estan anidados dentro de `web/`, Django no los encuentra solo
con `APP_DIRS`.

Por eso se registraron manualmente en:

- `Legajo/settings.py` dentro de `TEMPLATES[0]['DIRS']`
- `Legajo/settings.py` dentro de `STATICFILES_DIRS`

Si en el futuro creas un modulo nuevo con frontend, recuerda agregar:

1. su carpeta `templates/<modulo>/`
2. su carpeta `static/<modulo>/`
3. sus rutas en `settings.py`

## 4. Flujo recomendado para entender el proyecto

Si quieres seguir una funcionalidad:

1. Busca la ruta en `urls.py`.
2. Abre la `view` asociada.
3. Mira si esa `view` llama un servicio en `web/services`.
4. Si el servicio guarda o consulta datos, revisa el `model` correspondiente.

Ejemplo:

1. Ruta de crear libro: `web/gestion_libros/urls.py`
2. View: `registrar_libro` o `api_libros` en `web/gestion_libros/views.py`
3. Servicio: `create_book` en `web/services/books.py`
4. Modelo: `Libro` en `web/gestion_libros/models.py`

## 5. Que archivo tocar segun el cambio

Si quieres cambiar el formulario o endpoint de login:

- `web/usuarios/views.py`

Si quieres cambiar reglas de importacion masiva de usuarios:

- `web/services/users.py`

Si quieres cambiar el flujo del intercambio:

- `web/intercambios/views.py`
- `web/services/exchanges.py`

Si quieres cambiar reglas del libro:

- `web/gestion_libros/views.py`
- `web/services/books.py`
- `web/validators/books.py`

Si quieres cambiar estadisticas del admin:

- `web/administracion/views.py`
- `web/administracion/helpers.py`

## 6. Por que se conserva `web/models.py`

Ese archivo ya no contiene la implementacion real.

Se conserva porque:

- `AUTH_USER_MODEL` sigue apuntando a `web.Usuario`
- algunos imports antiguos pueden seguir haciendo `from web.models import ...`

En otras palabras:

- la logica real vive en los modulos
- `web/models.py` solo reexporta

## 7. Convenciones para seguir manteniendo orden

- No meter logica nueva en `Legajo/urls.py`; usa `web/urls.py` y luego el `urls.py` del modulo correcto.
- No meter reglas de negocio pesadas en las views; llévalas a `web/services`.
- No mezclar modelos de libros en usuarios ni modelos de usuarios en libros.
- Si aparece una nueva funcionalidad grande, crear un nuevo modulo en `web/`.
- Si un helper empieza a crecer demasiado, moverlo a una carpeta `common` o `shared`.
- Si agregas un HTML nuevo, guardalo dentro de `templates/<modulo>/` y renderizalo con una ruta como `usuarios/login.html` o `gestion_libros/inventario.html`.
- Si agregas un asset nuevo, guardalo dentro de `static/<modulo>/` y cargalo con `{% static 'modulo/archivo.ext' %}`.

## 8. Estado actual de la limpieza

Ya se eliminaron:

- `web/views_old.py`
- varios archivos puente antiguos que solo duplicaban imports

La estructura activa que debes usar de ahora en adelante es la modular.
