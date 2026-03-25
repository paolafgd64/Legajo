import datetime
import json
import os
import textwrap
import unicodedata
import uuid

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import Autor, Genero, Intercambio, Libro


User = get_user_model()


def index(request):
    return render(request, 'web/index.html')


def chats(request):
    return render(request, 'web/chats.html')


@ensure_csrf_cookie
def crear_cuenta(request):
    return render(request, 'web/crear_cuenta.html')


def dashboard_admin(request):
    return render(request, 'web/dashboard_admin.html')


@login_required(login_url='login')
def dashboard_usuario(request):
    libros_recomendados = (
        Libro.objects.filter(activo=True)
        .exclude(usuario_propietario=request.user)
        .exclude(usuario_propietario__isnull=True)
        .select_related('usuario_propietario')
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )
    libros_serializados = [_serialize_book(libro) for libro in libros_recomendados]
    return render(
        request,
        'web/dashboard_usuario.html',
        {
            'libros_recomendados': libros_serializados[:8],
            'libros_generos': libros_serializados[:8],
        },
    )


def forgot_password(request):
    return render(request, 'web/forgot-password.html')


def inventario_admi(request):
    return render(request, 'web/inventario_admi.html')


@ensure_csrf_cookie
def inventario(request):
    return render(request, 'web/inventario.html')


@ensure_csrf_cookie
def login(request):
    return render(request, 'web/login.html')


@ensure_csrf_cookie
def notificaciones(request):
    return render(request, 'web/notificaciones.html')


def novedades_usuarios(request):
    return render(request, 'web/novedades_usuarios.html')


@login_required(login_url='login')
def perfil_admin(request):
    user = request.user
    return render(request, 'web/perfil_admin.html', {
        'perfil_usuario': user,
        'nombre_completo': ' '.join(filter(None, [user.nombre1, user.nombre2, user.apellido1, user.apellido2])),
    })


@login_required(login_url='login')
def perfil(request):
    user = request.user
    return render(request, 'web/perfil.html', {
        'perfil_usuario': user,
        'nombre_completo': ' '.join(filter(None, [user.nombre1, user.nombre2, user.apellido1, user.apellido2])),
    })


@ensure_csrf_cookie
def registrar_libro(request, libro_id=None):
    context = {}

    if libro_id is not None:
        if not request.user.is_authenticated:
            return redirect('login')

        try:
            libro = Libro.objects.prefetch_related('autores', 'generos').get(id=libro_id, activo=True)
        except Libro.DoesNotExist:
            return redirect('inventario')

        if libro.usuario_propietario_id != request.user.id and request.user.rol != User.Rol.ADMIN:
            return redirect('inventario')

        autores = list(libro.autores.all())
        generos = list(libro.generos.all())
        context['modo_edicion'] = True
        context['libro_edicion'] = {
            'id': libro.id,
            'titulo': libro.titulo,
            'autor': str(autores[0]) if autores else '',
            'sinopsis': libro.sinopsis,
            'genero': generos[0].nombre if generos else '',
            'estado': libro.estado,
        }

    return render(request, 'web/registrar_libro.html', context)


def reporte_libros(request):
    return render(request, 'web/reporte_libros.html')


@login_required(login_url='login')
@require_http_methods(["GET"])
def reporte_libros_pdf(request):
    if request.user.rol != User.Rol.ADMIN:
        return _forbidden_response()

    libros = (
        Libro.objects.filter(activo=True)
        .select_related('usuario_propietario')
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )

    titulo = (request.GET.get('titulo') or '').strip()
    autor = (request.GET.get('autor') or '').strip()
    usuario = (request.GET.get('usuario') or '').strip()
    genero = (request.GET.get('genero') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    if titulo:
        libros = libros.filter(titulo__icontains=titulo)
    if autor:
        libros = libros.filter(autores__nombre1__icontains=autor).distinct()
    if usuario:
        libros = libros.filter(usuario_propietario__nombre1__icontains=usuario).distinct()
    if genero:
        libros = libros.filter(generos__nombre__icontains=genero).distinct()
    if estado:
        libros = libros.filter(estado__icontains=estado)

    rows = []
    for libro in libros:
        serialized = _serialize_book(libro)
        rows.append([
            serialized['usuario'],
            serialized['titulo'],
            serialized['autor'],
            serialized['genero'],
            serialized['estado'],
        ])

    return _build_pdf_response('Reporte de libros registrados', rows, 'reporte_libros.pdf')


def reset_password(request):
    return render(request, 'web/reset_password.html')


def _read_json_body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def _unauthorized_response():
    return JsonResponse({'message': 'Debes iniciar sesion.'}, status=401)


def _forbidden_response():
    return JsonResponse({'message': 'No tienes permiso para esta accion.'}, status=403)


def _split_author_name(author_name):
    author_name = (author_name or '').strip()
    if not author_name:
        return '', None, '', None

    parts = [part for part in author_name.split() if part]
    if len(parts) == 1:
        return parts[0], None, parts[0], None
    if len(parts) == 2:
        return parts[0], None, parts[1], None
    if len(parts) == 3:
        return parts[0], parts[1], parts[2], None

    return parts[0], parts[1], parts[2], ' '.join(parts[3:])


def _get_or_create_author(author_name):
    nombre1, nombre2, apellido1, apellido2 = _split_author_name(author_name)
    autor, _ = Autor.objects.get_or_create(
        nombre1=nombre1,
        nombre2=nombre2,
        apellido1=apellido1,
        apellido2=apellido2,
        defaults={'apodo': None},
    )
    return autor


def _save_uploaded_image(uploaded_file):
    extension = os.path.splitext(uploaded_file.name)[1] or '.jpg'
    filename = f"libros/{uuid.uuid4()}{extension}"
    saved_path = default_storage.save(filename, uploaded_file)
    return f"{settings.MEDIA_URL}{saved_path}".replace('\\', '/')


def _serialize_book(libro):
    autores = list(libro.autores.all())
    generos = list(libro.generos.all())
    autor_nombre = str(autores[0]) if autores else ''
    propietario = libro.usuario_propietario

    return {
        'id': libro.id,
        'idLibro': libro.id,
        'titulo': libro.titulo,
        'sinopsis': libro.sinopsis,
        'estado': libro.estado,
        'urlImagen': libro.url_imagen,
        'url_imagen': libro.url_imagen,
        'autor': autor_nombre,
        'autores': [str(autor) for autor in autores],
        'genero': generos[0].nombre if generos else '',
        'generos': [genero.nombre for genero in generos],
        'usuarioPropietarioId': libro.usuario_propietario_id,
        'usuario': str(propietario) if propietario else 'Usuario desconocido',
    }


def _normalize_pdf_text(value):
    normalized = unicodedata.normalize('NFKD', str(value or ''))
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    return ascii_text.replace('\r', ' ').replace('\n', ' ').strip()


def _pdf_escape(value):
    return (
        _normalize_pdf_text(value)
        .replace('\\', '\\\\')
        .replace('(', '\\(')
        .replace(')', '\\)')
    )


def _pdf_color(r, g, b, fill=True):
    operator = 'rg' if fill else 'RG'
    return f'{r / 255:.3f} {g / 255:.3f} {b / 255:.3f} {operator}'


def _pdf_rect(x, y, width, height, fill_color=None, stroke_color=None, line_width=1):
    commands = []
    if line_width:
        commands.append(f'{line_width} w')
    if fill_color:
        commands.append(_pdf_color(*fill_color, fill=True))
    if stroke_color:
        commands.append(_pdf_color(*stroke_color, fill=False))
    paint = 'B' if fill_color and stroke_color else 'f' if fill_color else 'S'
    commands.append(f'{x:.2f} {y:.2f} {width:.2f} {height:.2f} re {paint}')
    return '\n'.join(commands)


def _pdf_text_block(x, y, lines, font_key, size, color):
    if not lines:
        return ''
    commands = [
        'BT',
        f'/{font_key} {size} Tf',
        _pdf_color(*color, fill=True),
        f'1 0 0 1 {x:.2f} {y:.2f} Tm',
    ]
    for index, line in enumerate(lines):
        escaped_line = _pdf_escape(line)
        if index == 0:
            commands.append(f'({escaped_line}) Tj')
        else:
            commands.append(f'0 -{size + 3} Td')
            commands.append(f'({escaped_line}) Tj')
    commands.append('ET')
    return '\n'.join(commands)


def _wrap_pdf_cell(value, width, font_size):
    approx_chars = max(6, int(width / max(font_size * 0.52, 1)))
    normalized = _normalize_pdf_text(value) or '-'
    return textwrap.wrap(normalized, width=approx_chars) or ['-']


def _get_jpeg_size(image_bytes):
    if image_bytes[:2] != b'\xff\xd8':
        raise ValueError('Unsupported image format')
    index = 2
    while index < len(image_bytes):
        if image_bytes[index] != 0xFF:
            index += 1
            continue
        marker = image_bytes[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        length = int.from_bytes(image_bytes[index:index + 2], 'big')
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(image_bytes[index + 3:index + 5], 'big')
            width = int.from_bytes(image_bytes[index + 5:index + 7], 'big')
            return width, height
        index += length
    raise ValueError('JPEG size not found')


def _load_pdf_logo():
    logo_path = settings.BASE_DIR / 'web' / 'static' / 'web' / 'imgs' / 'logo_oscuro1.jpg'
    if not logo_path.exists():
        return None
    image_bytes = logo_path.read_bytes()
    width, height = _get_jpeg_size(image_bytes)
    return {
        'bytes': image_bytes,
        'width': width,
        'height': height,
    }


def _build_pdf_response(title, rows, filename):
    page_width = 612
    page_height = 792
    margin = 36
    header_height = 86
    footer_height = 28
    row_padding = 6
    cell_font_size = 8
    header_font_size = 10
    body_color = (20, 20, 20)
    white = (255, 255, 255)
    gold = (242, 174, 46)
    soft_gold = (255, 242, 214)
    navy = (9, 19, 38)
    light_border = (220, 220, 220)
    row_alt = (248, 248, 248)
    logo = _load_pdf_logo()

    columns = [
        ('Usuario', 120),
        ('Titulo', 150),
        ('Autor', 120),
        ('Genero', 90),
        ('Estado', 60),
    ]

    table_width = sum(width for _, width in columns)
    table_x = margin
    current_y = page_height - margin
    pages_commands = []
    current_commands = []
    page_number = 1

    def start_page():
        nonlocal current_y, current_commands, page_number
        current_commands = []
        current_commands.append(_pdf_rect(0, page_height - header_height, page_width, header_height, fill_color=navy))
        current_commands.append(_pdf_rect(0, page_height - header_height, page_width, 6, fill_color=gold))
        if logo:
            logo_width = 52
            logo_height = logo_width * logo['height'] / logo['width']
            logo_x = margin
            logo_y = page_height - header_height + 16
            current_commands.append(
                '\n'.join([
                    'q',
                    f'{logo_width:.2f} 0 0 {logo_height:.2f} {logo_x:.2f} {logo_y:.2f} cm',
                    '/Im1 Do',
                    'Q',
                ])
            )
        current_commands.append(_pdf_text_block(margin + 64, page_height - 42, ['LEGAJO'], 'F2', 22, gold))
        current_commands.append(_pdf_text_block(margin + 64, page_height - 60, [title], 'F1', 11, white))
        current_commands.append(
            _pdf_text_block(
                page_width - 180,
                page_height - 48,
                [f'Generado: {datetime.datetime.now():%Y-%m-%d %H:%M}', f'Pagina {page_number}'],
                'F1',
                9,
                white,
            )
        )

        table_top = page_height - header_height - 18
        current_commands.append(_pdf_rect(table_x, table_top - 26, table_width, 26, fill_color=gold))
        x_cursor = table_x
        for label, width in columns:
            current_commands.append(_pdf_text_block(x_cursor + 6, table_top - 17, [label], 'F2', header_font_size, navy))
            x_cursor += width
        current_y = table_top - 26
        page_number += 1

    def finish_page():
        footer_y = 12
        current_commands.append(_pdf_rect(0, footer_y + 12, page_width, 2, fill_color=gold))
        current_commands.append(_pdf_text_block(margin, footer_y, ['Legajo - Reporte administrativo'], 'F1', 8, body_color))
        pages_commands.append('\n'.join(command for command in current_commands if command))

    start_page()

    if not rows:
        row_height = 28
        current_commands.append(_pdf_rect(table_x, current_y - row_height, table_width, row_height, fill_color=soft_gold, stroke_color=light_border))
        current_commands.append(
            _pdf_text_block(table_x + 8, current_y - 18, ['No hay libros registrados con los filtros seleccionados.'], 'F1', 10, body_color)
        )
        current_y -= row_height
    else:
        for row_index, row in enumerate(rows):
            cell_lines = []
            max_lines = 1
            for (_, width), value in zip(columns, row):
                wrapped = _wrap_pdf_cell(value, width - 10, cell_font_size)
                cell_lines.append(wrapped)
                max_lines = max(max_lines, len(wrapped))

            row_height = max(24, max_lines * (cell_font_size + 3) + (row_padding * 2))
            if current_y - row_height < margin + footer_height:
                finish_page()
                start_page()

            fill = white if row_index % 2 == 0 else row_alt
            current_commands.append(_pdf_rect(table_x, current_y - row_height, table_width, row_height, fill_color=fill, stroke_color=light_border))

            x_cursor = table_x
            for column_index, ((_, width), wrapped_lines) in enumerate(zip(columns, cell_lines)):
                if column_index > 0:
                    current_commands.append(_pdf_rect(x_cursor, current_y - row_height, 0.7, row_height, fill_color=light_border))
                text_color = gold if column_index == 1 else body_color
                current_commands.append(
                    _pdf_text_block(
                        x_cursor + 6,
                        current_y - 14,
                        wrapped_lines,
                        'F2' if column_index == 1 else 'F1',
                        cell_font_size,
                        text_color,
                    )
                )
                x_cursor += width

            current_y -= row_height

    finish_page()

    objects = []

    def add_object(content):
        if isinstance(content, str):
            content = content.encode('latin-1', errors='replace')
        objects.append(content)
        return len(objects)

    catalog_obj = add_object('')
    pages_obj = add_object('')
    font_regular_obj = add_object('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    font_bold_obj = add_object('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>')
    image_obj = None
    if logo:
        image_obj = add_object(
            b'<< /Type /XObject /Subtype /Image /Width '
            + str(logo['width']).encode('ascii')
            + b' /Height '
            + str(logo['height']).encode('ascii')
            + b' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length '
            + str(len(logo['bytes'])).encode('ascii')
            + b' >>\nstream\n'
            + logo['bytes']
            + b'\nendstream'
        )

    page_object_numbers = []
    content_object_numbers = []
    for page_commands in pages_commands:
        stream_content = page_commands.encode('latin-1', errors='replace')
        content_obj = add_object(
            b'<< /Length ' + str(len(stream_content)).encode('ascii') + b' >>\nstream\n' + stream_content + b'\nendstream'
        )
        page_obj = add_object('')
        content_object_numbers.append(content_obj)
        page_object_numbers.append(page_obj)

    kids = ' '.join(f'{page_obj} 0 R' for page_obj in page_object_numbers)
    objects[catalog_obj - 1] = f'<< /Type /Catalog /Pages {pages_obj} 0 R >>'.encode('latin-1')
    objects[pages_obj - 1] = f'<< /Type /Pages /Kids [{kids}] /Count {len(page_object_numbers)} >>'.encode('latin-1')

    xobject_part = f'/XObject << /Im1 {image_obj} 0 R >> ' if image_obj else ''
    for page_obj, content_obj in zip(page_object_numbers, content_object_numbers):
        objects[page_obj - 1] = (
            f'<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {page_width} {page_height}] '
            f'/Resources << /Font << /F1 {font_regular_obj} 0 R /F2 {font_bold_obj} 0 R >> {xobject_part}>> '
            f'/Contents {content_obj} 0 R >>'
        ).encode('latin-1')

    pdf = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f'{index} 0 obj\n'.encode('ascii'))
        pdf.extend(obj)
        pdf.extend(b'\nendobj\n')

    xref_start = len(pdf)
    pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
    pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))

    pdf.extend(
        (
            f'trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n'
            f'startxref\n{xref_start}\n%%EOF'
        ).encode('ascii')
    )

    response = HttpResponse(bytes(pdf), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@require_http_methods(["POST"])
def api_usuarios(request):
    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    password = (data.get('clave') or '').strip()
    email = (data.get('correo') or '').strip().lower()

    required_fields = {
        'primerNombre': 'El primer nombre es obligatorio.',
        'primerApellido': 'El primer apellido es obligatorio.',
        'correo': 'El correo es obligatorio.',
        'clave': 'La contrasena es obligatoria.',
        'direccion': 'La direccion es obligatoria.',
        'ciudad': 'La ciudad es obligatoria.',
        'telefono': 'El telefono es obligatorio.',
    }

    for field, message in required_fields.items():
        value = data.get(field)
        if value is None or str(value).strip() == '':
            return JsonResponse({'message': message}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({'message': 'Ya existe un usuario registrado con ese correo.'}, status=400)

    telefono = str(data.get('telefono')).strip()
    if not telefono.isdigit():
        return JsonResponse({'message': 'El telefono debe contener solo numeros.'}, status=400)

    user = User(
        email=email,
        nombre1=data.get('primerNombre', '').strip(),
        nombre2=(data.get('segundoNombre') or '').strip() or None,
        apellido1=data.get('primerApellido', '').strip(),
        apellido2=(data.get('segundoApellido') or '').strip() or None,
        direccion=data.get('direccion', '').strip(),
        ciudad=data.get('ciudad', '').strip(),
        telefono=int(telefono),
        rol=User.Rol.USUARIO,
    )

    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return JsonResponse({'message': ' '.join(exc.messages)}, status=400)

    user.set_password(password)
    user.save()

    return JsonResponse({'mensaje': 'Usuario registrado correctamente'})


@require_http_methods(["POST"])
def api_login(request):
    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    email = (data.get('correo') or '').strip().lower()
    password = data.get('clave') or ''

    if not email or not password:
        return JsonResponse({'message': 'Correo y contrasena son obligatorios.'}, status=400)

    user = authenticate(request, email=email, password=password)
    if user is None:
        return JsonResponse({'message': 'Credenciales invalidas.'}, status=401)

    if not user.is_active or not getattr(user, 'activo', True):
        return JsonResponse({'message': 'Tu cuenta esta inactiva.'}, status=403)

    auth_login(request, user)

    redirect_url = '/dashboard_admin/' if user.rol == User.Rol.ADMIN else '/dashboard_usuario/'
    return JsonResponse({
        'message': 'Inicio de sesion exitoso.',
        'role': user.rol,
        'redirect_url': redirect_url,
        'token': 'session-authenticated',
    })


@require_http_methods(["GET", "PUT"])
def api_me(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    user = request.user
    if request.method == 'PUT':
        data = _read_json_body(request)
        if data is None:
            return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

        required_fields = {
            'primerNombre': 'El primer nombre es obligatorio.',
            'primerApellido': 'El primer apellido es obligatorio.',
            'correo': 'El correo es obligatorio.',
            'direccion': 'La direccion es obligatoria.',
            'ciudad': 'La ciudad es obligatoria.',
            'telefono': 'El telefono es obligatorio.',
        }

        for field, message in required_fields.items():
            value = data.get(field)
            if value is None or str(value).strip() == '':
                return JsonResponse({'message': message}, status=400)

        email = (data.get('correo') or '').strip().lower()
        telefono = str(data.get('telefono')).strip()

        if not telefono.isdigit():
            return JsonResponse({'message': 'El telefono debe contener solo numeros.'}, status=400)

        if User.objects.exclude(id=user.id).filter(email=email).exists():
            return JsonResponse({'message': 'Ya existe un usuario registrado con ese correo.'}, status=400)

        user.email = email
        user.nombre1 = (data.get('primerNombre') or '').strip()
        user.nombre2 = (data.get('segundoNombre') or '').strip() or None
        user.apellido1 = (data.get('primerApellido') or '').strip()
        user.apellido2 = (data.get('segundoApellido') or '').strip() or None
        user.direccion = (data.get('direccion') or '').strip()
        user.ciudad = (data.get('ciudad') or '').strip()
        user.telefono = int(telefono)
        user.save()

    return JsonResponse({
        'id': user.id,
        'idUsuario': user.id,
        'email': user.email,
        'primerNombre': user.nombre1,
        'segundoNombre': user.nombre2,
        'primerApellido': user.apellido1,
        'segundoApellido': user.apellido2,
        'direccion': user.direccion,
        'ciudad': user.ciudad,
        'telefono': user.telefono,
        'rol': user.rol,
    })


@require_http_methods(["GET", "POST"])
def api_libros(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    if request.method == 'GET':
        libros = Libro.objects.filter(activo=True).prefetch_related('autores', 'generos').select_related('usuario_propietario')

        if request.user.rol != User.Rol.ADMIN:
            libros = libros.filter(usuario_propietario=request.user)

        titulo = (request.GET.get('titulo') or '').strip()
        autor = (request.GET.get('autor') or '').strip()
        usuario = (request.GET.get('usuario') or '').strip()
        genero = (request.GET.get('genero') or '').strip()
        estado = (request.GET.get('estado') or '').strip()

        if titulo:
            libros = libros.filter(titulo__icontains=titulo)
        if autor:
            libros = libros.filter(
                Q(autores__nombre1__icontains=autor) |
                Q(autores__nombre2__icontains=autor) |
                Q(autores__apellido1__icontains=autor) |
                Q(autores__apellido2__icontains=autor) |
                Q(autores__apodo__icontains=autor)
            )
        if usuario:
            libros = libros.filter(
                Q(usuario_propietario__nombre1__icontains=usuario) |
                Q(usuario_propietario__nombre2__icontains=usuario) |
                Q(usuario_propietario__apellido1__icontains=usuario) |
                Q(usuario_propietario__apellido2__icontains=usuario) |
                Q(usuario_propietario__email__icontains=usuario)
            )
        if genero:
            libros = libros.filter(generos__nombre__icontains=genero)
        if estado:
            libros = libros.filter(estado__iexact=estado)

        libros = libros.order_by('-id').distinct()
        return JsonResponse([_serialize_book(libro) for libro in libros], safe=False)

    titulo = (request.POST.get('titulo') or '').strip()
    autor_nombre = (request.POST.get('autor') or '').strip()
    sinopsis = (request.POST.get('sinopsis') or '').strip()
    genero_nombre = (request.POST.get('genero') or '').strip()
    estado = (request.POST.get('estado') or Libro.Estado.PUBLICADO).strip()

    if not titulo or not autor_nombre or not genero_nombre:
        return JsonResponse({'message': 'Titulo, autor y genero son obligatorios.'}, status=400)

    if estado not in Libro.Estado.values:
        estado = Libro.Estado.PUBLICADO

    image_file = request.FILES.get('imagen')
    if image_file:
        url_imagen = _save_uploaded_image(image_file)
    else:
        url_imagen = '/static/web/imgs/libro_de_la_selva.jpg'

    libro = Libro.objects.create(
        titulo=titulo,
        sinopsis=sinopsis,
        estado=estado,
        url_imagen=url_imagen,
        usuario_propietario=request.user,
    )

    autor = _get_or_create_author(autor_nombre)
    genero, _ = Genero.objects.get_or_create(nombre=genero_nombre.title())
    libro.autores.add(autor)
    libro.generos.add(genero)

    return JsonResponse(_serialize_book(libro), status=201)


@require_http_methods(["GET"])
def api_libros_recomendados(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    libros = (
        Libro.objects.filter(activo=True)
        .exclude(usuario_propietario=request.user)
        .exclude(usuario_propietario__isnull=True)
        .select_related('usuario_propietario')
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )
    return JsonResponse([_serialize_book(libro) for libro in libros], safe=False)


@require_http_methods(["GET", "PUT", "DELETE"])
def api_libro_detalle(request, libro_id):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    try:
        libro = Libro.objects.prefetch_related('autores', 'generos').get(id=libro_id, activo=True)
    except Libro.DoesNotExist:
        return JsonResponse({'message': 'Libro no encontrado.'}, status=404)

    if libro.usuario_propietario_id != request.user.id and request.user.rol != User.Rol.ADMIN:
        return JsonResponse({'message': 'No tienes permiso para este libro.'}, status=403)

    if request.method == 'GET':
        return JsonResponse(_serialize_book(libro))

    if request.method == 'PUT':
        data = _read_json_body(request)
        if data is None:
            return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

        titulo = (data.get('titulo') or '').strip()
        autor_nombre = (data.get('autor') or '').strip()
        sinopsis = (data.get('sinopsis') or '').strip()
        genero_nombre = (data.get('genero') or '').strip()
        estado = (data.get('estado') or libro.estado).strip()

        if not titulo or not autor_nombre or not genero_nombre:
            return JsonResponse({'message': 'Titulo, autor y genero son obligatorios.'}, status=400)

        if estado not in Libro.Estado.values:
            estado = Libro.Estado.PUBLICADO

        libro.titulo = titulo
        libro.sinopsis = sinopsis
        libro.estado = estado
        libro.save(update_fields=['titulo', 'sinopsis', 'estado'])

        autor = _get_or_create_author(autor_nombre)
        genero, _ = Genero.objects.get_or_create(nombre=genero_nombre.title())
        libro.autores.set([autor])
        libro.generos.set([genero])

        return JsonResponse(_serialize_book(libro))

    libro.activo = False
    libro.save(update_fields=['activo'])
    return JsonResponse({'message': 'Libro eliminado correctamente.'})


@require_http_methods(["GET"])
def api_notificaciones(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    notificaciones = (
        Intercambio.objects.filter(
            usuario_receptor=request.user,
            activo=True,
        )
        .select_related('usuario_solicitante', 'libro_solicitado')
        .order_by('-fecha_solicitud')
    )

    resultado = []
    for intercambio in notificaciones:
        solicitante = intercambio.usuario_solicitante
        libro = intercambio.libro_solicitado
        nombre_solicitante = str(solicitante) if solicitante else 'Usuario desconocido'
        titulo_libro = libro.titulo if libro else 'Libro sin titulo'

        if intercambio.estado == Intercambio.Estado.PENDIENTE:
            mensaje = f'{nombre_solicitante} solicito intercambio por tu libro "{titulo_libro}".'
        elif intercambio.estado == Intercambio.Estado.ACEPTADO:
            mensaje = f'Tienes un intercambio aceptado para "{titulo_libro}".'
        elif intercambio.estado == Intercambio.Estado.RECHAZADO:
            mensaje = f'La solicitud por "{titulo_libro}" fue rechazada.'
        else:
            mensaje = f'El intercambio por "{titulo_libro}" fue completado.'

        resultado.append({
            'id': intercambio.id,
            'usuario': nombre_solicitante,
            'libro': titulo_libro,
            'estado': intercambio.estado,
            'mensaje': mensaje,
            'fecha': intercambio.fecha_solicitud.strftime('%Y-%m-%d %H:%M'),
            'esNueva': intercambio.estado == Intercambio.Estado.PENDIENTE,
            'puedeAceptar': intercambio.estado == Intercambio.Estado.PENDIENTE,
        })

    return JsonResponse(resultado, safe=False)


@require_http_methods(["GET"])
def api_inventario_solicitante_intercambio(request, intercambio_id):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    try:
        intercambio = Intercambio.objects.select_related('usuario_receptor', 'usuario_solicitante').get(
            id=intercambio_id,
            activo=True,
        )
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if intercambio.usuario_receptor_id != request.user.id:
        return JsonResponse({'message': 'No tienes permiso para ver este inventario.'}, status=403)

    libros = (
        Libro.objects.filter(
            usuario_propietario=intercambio.usuario_solicitante,
            activo=True,
        )
        .prefetch_related('autores', 'generos')
        .order_by('-id')
    )

    return JsonResponse([_serialize_book(libro) for libro in libros], safe=False)


@require_http_methods(["POST"])
def api_aceptar_intercambio(request, intercambio_id):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    try:
        intercambio = Intercambio.objects.select_related(
            'usuario_receptor',
            'usuario_solicitante',
            'libro_solicitado',
        ).get(id=intercambio_id, activo=True)
    except Intercambio.DoesNotExist:
        return JsonResponse({'message': 'Intercambio no encontrado.'}, status=404)

    if intercambio.usuario_receptor_id != request.user.id:
        return JsonResponse({'message': 'No tienes permiso para aceptar este intercambio.'}, status=403)

    if intercambio.estado != Intercambio.Estado.PENDIENTE:
        return JsonResponse({'message': 'Este intercambio ya no esta pendiente.'}, status=400)

    libro_cambio_id = data.get('libroCambioId')
    if not libro_cambio_id:
        return JsonResponse({'message': 'Debes seleccionar un libro del solicitante.'}, status=400)

    try:
        libro_cambio = Libro.objects.get(
            id=libro_cambio_id,
            usuario_propietario=intercambio.usuario_solicitante,
            activo=True,
        )
    except Libro.DoesNotExist:
        return JsonResponse({'message': 'El libro seleccionado no pertenece al solicitante.'}, status=400)

    intercambio.libro_cambio = libro_cambio
    intercambio.estado = Intercambio.Estado.ACEPTADO
    intercambio.fecha_confirmacion = timezone.now()
    intercambio.save(update_fields=['libro_cambio', 'estado', 'fecha_confirmacion'])

    solicitante = intercambio.usuario_solicitante
    receptor = intercambio.usuario_receptor
    telefono_solicitante = str(solicitante.telefono) if solicitante and solicitante.telefono else ''
    nombre_receptor = str(receptor) if receptor else 'el propietario'
    titulo_solicitado = intercambio.libro_solicitado.titulo if intercambio.libro_solicitado else 'tu libro'
    mensaje_whatsapp = (
        f'Hola {str(solicitante) if solicitante else ""}, '
        f'{nombre_receptor} acepto tu solicitud de intercambio por "{titulo_solicitado}". '
        f'El libro seleccionado para el intercambio es "{libro_cambio.titulo}". '
        f'Ponganse de acuerdo para continuar.'
    )

    return JsonResponse({
        'message': 'Intercambio aceptado correctamente.',
        'idIntercambio': intercambio.id,
        'libroCambio': libro_cambio.titulo,
        'telefonoWhatsapp': telefono_solicitante,
        'mensajeWhatsapp': mensaje_whatsapp,
    })


@require_http_methods(["POST"])
def api_solicitar_intercambio(request):
    if not request.user.is_authenticated:
        return _unauthorized_response()

    data = _read_json_body(request)
    if data is None:
        return JsonResponse({'message': 'El cuerpo de la solicitud no es JSON valido.'}, status=400)

    libro_id = data.get('libroId')
    if not libro_id:
        return JsonResponse({'message': 'Debes indicar el libro solicitado.'}, status=400)

    try:
        libro = Libro.objects.select_related('usuario_propietario').get(id=libro_id, activo=True)
    except Libro.DoesNotExist:
        return JsonResponse({'message': 'El libro solicitado no existe.'}, status=404)

    if libro.usuario_propietario_id == request.user.id:
        return JsonResponse({'message': 'No puedes solicitar intercambio por tu propio libro.'}, status=400)

    existente = Intercambio.objects.filter(
        usuario_solicitante=request.user,
        libro_solicitado=libro,
        estado=Intercambio.Estado.PENDIENTE,
        activo=True,
    ).exists()
    if existente:
        return JsonResponse({'message': 'Ya tienes una solicitud pendiente para este libro.'}, status=400)

    intercambio = Intercambio.objects.create(
        estado=Intercambio.Estado.PENDIENTE,
        usuario_solicitante=request.user,
        usuario_receptor=libro.usuario_propietario,
        libro_solicitado=libro,
        libro_cambio=None,
    )

    return JsonResponse({
        'message': 'Solicitud de intercambio enviada correctamente.',
        'idIntercambio': intercambio.id,
    }, status=201)
