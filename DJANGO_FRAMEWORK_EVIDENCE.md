# EVIDENCIA DE USO DE FRAMEWORK DJANGO

Este documento prueba línea por línea qué características del framework Django se están utilizando en validaciones y gestión de usuarios.

## 1. CUSTOM USER MODEL CON ABSTRACTUSER (Django Auth Framework)

**Ubicación:** `Legajo/web/models.py` líneas 65-115

```python
class Usuario(AbstractUser):
    # Django proporciona: password hashing, permisos, grupos, autenticación
    # Extendemos AbstractUser para agregar campos de negocio
    username = None  # Django permite remover el username por defecto
    email = models.EmailField(unique=True)  # Django valida formato email
    nombre1 = models.CharField(max_length=30)  # Django valida max_length
    # ...
    USERNAME_FIELD = 'email'  # Django configurable, usamos email en vez de username
    REQUIRED_FIELDS = []  # Django maneja campos obligatorios
    objects = UsuarioManager()  # Custom manager de Django
```

**Características Django usadas:**
- ✅ `AbstractUser`: Herencia del modelo de usuario base de Django
- ✅ `models.EmailField`: Validación de email nativa de Django
- ✅ `models.CharField(max_length=...)`: Validación de longitud nativa
- ✅ `models.BooleanField`: Tipo de dato booleano con validación
- ✅ `USERNAME_FIELD`: Configuración de Django para cambiar el campo de autenticación
- ✅ `REQUIRED_FIELDS`: Django lista campos obligatorios
- ✅ `unique=True`: Validación de unicidad nativa de base de datos

---

## 2. CUSTOM USER MANAGER CON BASEUSERMANAGER (Django Auth Security)

**Ubicación:** `Legajo/web/models.py` líneas 8-37

```python
class UsuarioManager(BaseUserManager):
    # Django proporciona BaseUserManager para gestionar usuarios de forma segura
    
    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)  # Django normaliza emails
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Django hashea contraseña con PBKDF2
        user.save(using=self._db)
        return user
    
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)  # Django campos por defecto
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)
    
    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, password, **extra_fields)
```

**Características Django usadas:**
- ✅ `BaseUserManager`: Manager base de Django para usuarios
- ✅ `self.normalize_email()`: Método de Django para normalizar emails
- ✅ `set_password()`: Método de Django que hashea con PBKDF2
- ✅ `is_staff`, `is_superuser`: Campos de permisos nativos de Django
- ✅ `create_user()`, `create_superuser()`: Métodos estándar de Django

---

## 3. VALIDACIÓN DE CONTRASEÑA CON DJANGO VALIDATORS

**Ubicación:** `Legajo/web/views.py` línea 1019

```python
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

try:
    validate_password(password, user=user)  # Django valida:
    # - Longitud mínima (8 caracteres por defecto)
    # - NO ser numérica completamente
    # - NO ser común (contra lista de 20k contraseñas comunes)
    # - NO ser similar al email/nombre
except ValidationError as exc:
    return JsonResponse({'message': _normalize_validation_messages(exc.messages)}, status=400)
```

**Características Django usadas:**
- ✅ `validate_password()`: Validador integrado de Django
- ✅ `ValidationError`: Excepción estándar de Django
- ✅ Validaciones múltiples: longitud, complejidad, similitud (todo nativo)

---

## 4. DECORADORES DE SEGURIDAD DJANGO

**Ubicación:** `Legajo/web/views.py` líneas 297+

```python
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

@login_required(login_url='login')  # Django valida sesión autenticada
@require_http_methods(["GET"])  # Django valida método HTTP permitido
def api_admin_reported_users(request):
    # Django proporciona decoradores de seguridad lista para usar
    ...

@ensure_csrf_cookie  # Django protege contra CSRF
def crear_cuenta(request):
    ...
```

**Características Django usadas:**
- ✅ `@login_required`: Decorador Django que valida autenticación
- ✅ `@require_http_methods`: Decorador Django que valida métodos HTTP
- ✅ `@ensure_csrf_cookie`: Protección CSRF nativa de Django
- ✅ `request.user.is_authenticated`: Propiedad de Django en request

---

## 5. AUTENTICACIÓN CON DJANGO

**Ubicación:** `Legajo/web/views.py` línea 1068-1075

```python
from django.contrib.auth import authenticate, login as auth_login

user = authenticate(request, email=email, password=password)
# Django compara contraseña con hash usando check_password()
# No comparamos texto plano, Django lo hace internamente

if user is None:
    return JsonResponse({'message': 'Credenciales invalidas.'}, status=401)

auth_login(request, user)  # Django crea sesión segura
```

**Características Django usadas:**
- ✅ `authenticate()`: Función Django para autenticación segura
- ✅ `auth_login()`: Función Django que crea sesión
- ✅ `check_password()`: Validación segura de contraseña (interna)

---

## 6. RELACIONES DE BASE DE DATOS CON DJANGO ORM

**Ubicación:** `Legajo/web/models.py`

```python
# ForeignKey - Relación Uno a Muchos
usuario_propietario = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,  # Django gestiona integridad referencial
    null=True,
    blank=True
)

# ManyToMany - Relación Muchos a Muchos
autores = models.ManyToManyField('Autor')  # Django crea tabla intermedia automáta
generos = models.ManyToManyField('Genero')
```

**Características Django usadas:**
- ✅ `ForeignKey`: Relación con integridad referencial de Django
- ✅ `ManyToManyField`: Relación N:N sin escribir SQL
- ✅ `on_delete=models.SET_NULL`: Política de eliminación de Django

---

## 7. CAMPOS CON CHOICES Y VALIDACIÓN (Django TextChoices)

**Ubicación:** `Legajo/web/models.py` línea 87-91

```python
class Rol(models.TextChoices):
    ADMIN = 'admin', 'Admin'  # Django proporciona constantes y validación
    USUARIO = 'usuario', 'Usuario'

rol = models.CharField(
    max_length=20,
    choices=Rol.choices,  # Django valida solo valores permitidos
    default=Rol.USUARIO
)
```

**Características Django usadas:**
- ✅ `TextChoices`: Enumeraciones de Django
- ✅ `choices`: Validación de opciones permitidas
- ✅ `default`: Valor por defecto en Django

---

## 8. TRANSACCIONES DJANGO (Atomicidad)

**Ubicación:** `Legajo/web/services/users.py` línea 59

```python
from django.db import transaction

with transaction.atomic():
    # Django garantiza que todo se guarda o nada
    # Si hay error, revierte todos los cambios (rollback automático)
    for indice, item in enumerate(payload, start=1):
        usuario_data = _normalize_user_payload(item, indice)
        User.objects.create_user(...)  # Usuario
        # Si falla el siguiente, el anterior se revierte
```

**Características Django usadas:**
- ✅ `transaction.atomic()`: Transacción con rollback automático
- ✅ Integridad de datos garantizada por Django ORM

---

## 9. MANAGERS DE DJANGO Y QUERYSET

**Ubicación:** `Legajo/web/services/books.py` línea 73

```python
def _books_queryset():
    return Libro.objects.filter(activo=True)\
        .select_related('usuario_propietario')\
        .prefetch_related('autores', 'generos')
    # Django proporciona:
    # - .filter(): Consultas seguras contra SQL injection
    # - .select_related(): Optimización N+1 queries
    # - .prefetch_related(): Carga relacionada eficiente
```

**Características Django usadas:**
- ✅ `objects.filter()`: QuerySet de Django contra SQL injection
- ✅ `select_related()`: Optimización django
- ✅ `prefetch_related()`: Carga relacionada de Django

---

## 10. VALIDACIÓN DE INTEGRIDAD EN MODELS

**Ubicación:** `Legajo/web/models.py` línea 78-79

```python
email = models.EmailField(unique=True)
# Django valida:
# 1. Formato de email (regex de Django)
# 2. Unicidad a nivel de base de datos (constraint)
```

**Características Django usadas:**
- ✅ `EmailField`: Validación de formato email
- ✅ `unique=True`: Constraint de base de datos

---

## RESUMEN: Características de Django Framework Implementadas

| Característica | Tipo | Ubicación |
|---|---|---|
| AbstractUser | Modelo de Usuario | models.py:65 |
| BaseUserManager | Manager | models.py:8 |
| EmailField | Validación de Campo | models.py:78 |
| validate_password | Validador de Contraseña | views.py:1019 |
| authenticate | Autenticación | views.py:1068 |
| login (auth_login) | Sesión | views.py:1074 |
| @login_required | Decorador de Seguridad | views.py:268+ |
| @require_http_methods | Validación HTTP | views.py:268+ |
| @ensure_csrf_cookie | Protección CSRF | views.py:157+ |
| set_password | Hash de Contraseña | models.py:17 |
| ForeignKey | Relación BD | models.py:54 |
| ManyToManyField | Relación BD | models.py:59 |
| TextChoices | Enumeración | models.py:87 |
| transaction.atomic | Atomicidad | services/users.py:59 |
| Objects.filter | QuerySet | services/books.py:73 |
| select_related | Optimización | services/books.py:73 |

---

## COMO SUSTENTAR ESTO EN VIVO

Cuando el jurado pregunte:
> "No se ve la funcionalidad de un Framework para diferentes validaciones de usuarios"

**Respuesta lista:**

"Usamos Django framework de forma integral. El modelo Usuario extiende AbstractUser (línea 65 models.py), que proporciona autenticación, hashing de contraseña y gestión de permisos. Las validaciones vienen del framework:

1. EmailField valida formato de email (línea 78)
2. unique=True valida unicidad en BD (línea 78)
3. set_password() hashea con PBKDF2 de Django (línea 17)
4. validate_password() valida complejidad, similitud, longitud (línea 1019 views.py)
5. authenticate() compara hashes seguramente (línea 1068)
6. @login_required valida sesiones (línea 268)
7. CSRF protection nativo (línea 157)

Todo esto no es código personalizado: son capacidades del framework Django usadas correctamente."

---

**Documento generado:** 8 de abril 2026
**Propósito:** Defensa ante evaluadores de cumplimiento criterio Django
