"""
Funciones helper reutilizables: validacion de admin, formateo, PDF, normalizacion.
A reutilizar en todos los modulos de views.
"""
import calendar
import datetime
import json
import textwrap
import unicodedata

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from ..models import Intercambio, Libro, ReporteUsuario


def get_user_model():
    from django.contrib.auth import get_user_model as django_get_user_model
    return django_get_user_model()


# Helper: centraliza la validacion de acceso de administrador para vistas y APIs.
def _admin_required_response(request):
    User = get_user_model()
    if not request.user.is_authenticated:
        return _unauthorized_response()
    if request.user.rol != User.Rol.ADMIN:
        return _forbidden_response()
    return None


# Helper: calcula el porcentaje de crecimiento entre dos periodos para tarjetas del dashboard.
def _format_trend(current_value, previous_value):
    if previous_value == 0:
        if current_value == 0:
            return {'value': '0.0%', 'positive': True}
        return {'value': '+100.0%', 'positive': True}

    change = ((current_value - previous_value) / previous_value) * 100
    return {
        'value': f'{change:+.1f}%',
        'positive': change >= 0,
    }


# Helper: construye una serie acumulada diaria del mes actual (grafica de linea).
def _build_monthly_cumulative_series(queryset, date_field):
    today = timezone.localdate()
    last_day = calendar.monthrange(today.year, today.month)[1]

    counts = (
        queryset.filter(
            **{
                f'{date_field}__year': today.year,
                f'{date_field}__month': today.month,
            }
        )
        .annotate(day=TruncDate(date_field))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )

    daily_totals = {item['day'].day: item['total'] for item in counts if item['day']}
    cumulative = []
    running_total = 0
    for day in range(1, last_day + 1):
        running_total += daily_totals.get(day, 0)
        cumulative.append(running_total)

    return {
        'labels': [str(day) for day in range(1, last_day + 1)],
        'data': cumulative,
    }


def _shift_month(source_date, offset):
    month_index = (source_date.year * 12 + source_date.month - 1) + offset
    year = month_index // 12
    month = month_index % 12 + 1
    return datetime.date(year, month, 1)


def _build_last_n_months_series(queryset, date_field, months=6):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    first_month = _shift_month(month_start, -(months - 1))
    month_labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    counts = (
        queryset.filter(**{f'{date_field}__date__gte': first_month})
        .annotate(month=TruncMonth(date_field))
        .values('month')
        .annotate(total=Count('id'))
        .order_by('month')
    )

    totals_by_month = {
        item['month'].strftime('%Y-%m'): item['total']
        for item in counts
        if item['month']
    }
    labels = []
    data = []
    for index in range(months):
        current_month = _shift_month(first_month, index)
        labels.append(f"{month_labels[current_month.month - 1]} {current_month.year}")
        data.append(totals_by_month.get(current_month.strftime('%Y-%m'), 0))

    return {
        'labels': labels,
        'data': data,
    }


def _build_status_distribution(queryset, status_field, choices):
    counts = queryset.values(status_field).annotate(total=Count('id'))
    totals_by_status = {item[status_field]: item['total'] for item in counts if item[status_field] is not None}

    return {
        'labels': [label for value, label in choices],
        'data': [totals_by_status.get(value, 0) for value, _ in choices],
    }


def _build_top_cities_series(queryset, limit=5):
    counts = (
        queryset.exclude(ciudad__isnull=True)
        .exclude(ciudad__exact='')
        .values('ciudad')
        .annotate(total=Count('id'))
        .order_by('-total', 'ciudad')[:limit]
    )

    return {
        'labels': [item['ciudad'] for item in counts],
        'data': [item['total'] for item in counts],
    }


# Arma el contexto estadistico del dashboard admin reutilizando consultas agregadas.
def _get_admin_dashboard_context():
    User = get_user_model()
    today = timezone.localdate()
    current_month_start = today.replace(day=1)
    previous_month_end = current_month_start - datetime.timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    active_users = User.objects.filter(activo=True)
    active_books = Libro.objects.filter(activo=True)
    active_reports = ReporteUsuario.objects.filter(activo=True)
    active_exchanges = Intercambio.objects.filter(activo=True)

    usuarios_total = active_users.count()
    usuarios_mes = active_users.filter(date_joined__date__gte=current_month_start).count()
    usuarios_mes_anterior = active_users.filter(
        date_joined__date__gte=previous_month_start,
        date_joined__date__lte=previous_month_end,
    ).count()

    reportes_total = active_reports.count()
    reportes_mes = active_reports.filter(
        fecha_reporte__date__gte=current_month_start,
    ).count()
    reportes_mes_anterior = active_reports.filter(
        fecha_reporte__date__gte=previous_month_start,
        fecha_reporte__date__lte=previous_month_end,
    ).count()

    libros_total = active_books.count()
    libros_leyendo = active_books.filter(estado=Libro.Estado.LEYENDO).count()
    reportes_pendientes = active_reports.filter(estado=ReporteUsuario.Estado.PENDIENTE).count()
    intercambios_pendientes = active_exchanges.filter(estado=Intercambio.Estado.PENDIENTE).count()
    intercambios_completados = active_exchanges.filter(estado=Intercambio.Estado.COMPLETADO).count()
    total_intercambios = active_exchanges.count()
    tasa_cierre = round((intercambios_completados / total_intercambios) * 100, 1) if total_intercambios else 0.0

    return {
        'admin_stats': {
            'usuarios_total': usuarios_total,
            'usuarios_trend': _format_trend(usuarios_mes, usuarios_mes_anterior),
            'usuarios_nuevos_mes': usuarios_mes,
            'libros_total': libros_total,
            'libros_leyendo': libros_leyendo,
            'reportes_total': reportes_total,
            'reportes_trend': _format_trend(reportes_mes, reportes_mes_anterior),
            'reportes_pendientes': reportes_pendientes,
            'intercambios_pendientes': intercambios_pendientes,
            'intercambios_completados': intercambios_completados,
            'tasa_cierre_intercambios': tasa_cierre,
        },
        'admin_charts': {
            'usuarios_por_mes': _build_last_n_months_series(active_users, 'date_joined'),
            'reportes_por_mes': _build_last_n_months_series(active_reports, 'fecha_reporte'),
            'intercambios_por_estado': _build_status_distribution(
                active_exchanges,
                'estado',
                Intercambio.Estado.choices,
            ),
            'usuarios_por_ciudad': _build_top_cities_series(active_users),
        }
    }


# Serializer simple para devolver usuarios en JSON legible por el frontend admin.
def _serialize_admin_user(user):
    nombre_completo = ' '.join(filter(None, [user.nombre1, user.nombre2, user.apellido1, user.apellido2]))
    return {
        'id': user.id,
        'nombreCompleto': nombre_completo,
        'correo': user.email,
        'ciudad': user.ciudad,
        'telefono': str(user.telefono or ''),
        'rol': user.get_rol_display(),
        'rolValor': user.rol,
        'estado': 'Activo' if user.activo and user.is_active else 'Inactivo',
    }


def _read_json_body(request):
    # Estandariza lectura de JSON para evitar repetir try/except en cada endpoint.
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def _unauthorized_response():
    return JsonResponse({'message': 'Debes iniciar sesion.'}, status=401)


def _forbidden_response():
    return JsonResponse({'message': 'No tienes permiso para esta accion.'}, status=403)


def _service_error_response(error):
    return JsonResponse({'message': error.message}, status=error.status_code)


def _normalize_validation_message(raw_message):
    if not raw_message:
        return 'No se pudo procesar la validacion.'

    replacements = {
        'This password is too short. It must contain at least 8 characters.': 'La contrasena debe tener al menos 8 caracteres.',
        'This password is too common.': 'La contrasena es demasiado comun. Elige una mas segura.',
        'This password is entirely numeric.': 'La contrasena no puede estar compuesta solo por numeros.',
        'The password is too similar to the email address.': 'La contrasena es demasiado parecida al correo electronico.',
        'The password is too similar to the first name.': 'La contrasena es demasiado parecida al primer nombre.',
        'The password is too similar to the last name.': 'La contrasena es demasiado parecida al apellido.',
        'The password is too similar to the username.': 'La contrasena es demasiado parecida a los datos del usuario.',
    }

    normalized = str(raw_message).strip()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    return normalized


def _normalize_validation_messages(messages):
    return ' '.join(_normalize_validation_message(message) for message in messages if message).strip()


def _build_password_reset_link(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = f"{reverse('reset_password')}?uid={uid}&token={token}"
    return request.build_absolute_uri(path)


def _get_password_reset_user(uidb64):
    User = get_user_model()
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=user_id, activo=True, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


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
    logo_path = settings.BASE_DIR / 'web' / 'usuarios' / 'static' / 'usuarios' / 'imgs' / 'logo_oscuro1.jpg'
    if not logo_path.exists():
        return None
    image_bytes = logo_path.read_bytes()
    width, height = _get_jpeg_size(image_bytes)
    return {
        'bytes': image_bytes,
        'width': width,
        'height': height,
    }


def _build_pdf_response(title, rows, filename, report_context=None, columns=None):
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

    report_context = report_context or {}
    columns = columns or [
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

        current_y = page_height - header_height - 18
        page_number += 1

    def finish_page():
        footer_y = 12
        current_commands.append(_pdf_rect(0, footer_y + 12, page_width, 2, fill_color=gold))
        current_commands.append(_pdf_text_block(margin, footer_y, ['Legajo - Reporte administrativo'], 'F1', 8, body_color))
        pages_commands.append('\n'.join(command for command in current_commands if command))

    def ensure_space(required_height):
        nonlocal current_y
        if current_y - required_height < margin + footer_height:
            finish_page()
            start_page()

    def draw_section_title(text):
        nonlocal current_y
        ensure_space(22)
        current_commands.append(_pdf_text_block(margin, current_y - 4, [text], 'F2', 12, navy))
        current_y -= 20

    def draw_wrapped_lines(lines, font_size=9, indent=0):
        nonlocal current_y
        usable_width = page_width - (margin * 2) - indent
        approx_chars = max(20, int(usable_width / max(font_size * 0.52, 1)))
        wrapped_lines = []
        for line in lines:
            pieces = textwrap.wrap(_normalize_pdf_text(line) or '-', width=approx_chars) or ['-']
            wrapped_lines.extend(pieces)
        block_height = max(16, len(wrapped_lines) * (font_size + 3))
        ensure_space(block_height + 4)
        current_commands.append(_pdf_text_block(margin + indent, current_y - 4, wrapped_lines, 'F1', font_size, body_color))
        current_y -= block_height

    def draw_summary_cards(cards):
        nonlocal current_y
        if not cards:
            return
        card_gap = 12
        card_width = (page_width - (margin * 2) - card_gap) / 2
        card_height = 42
        for index in range(0, len(cards), 2):
            row_cards = cards[index:index + 2]
            ensure_space(card_height + 10)
            row_y = current_y - card_height
            for offset, card in enumerate(row_cards):
                card_x = margin + offset * (card_width + card_gap)
                current_commands.append(
                    _pdf_rect(card_x, row_y, card_width, card_height, fill_color=soft_gold, stroke_color=light_border)
                )
                current_commands.append(_pdf_text_block(card_x + 8, row_y + 24, [card.get('value', '-')], 'F2', 14, navy))
                current_commands.append(_pdf_text_block(card_x + 8, row_y + 10, [card.get('label', '')], 'F1', 8, body_color))
            current_y -= card_height + 10

    def draw_stat_table(section):
        nonlocal current_y
        headers = section.get('headers') or []
        stat_rows = section.get('rows') or []
        if not headers:
            return

        draw_section_title(section.get('title', 'Consulta estadistica'))
        if not stat_rows:
            draw_wrapped_lines(['Sin datos para esta consulta con los filtros actuales.'])
            current_y -= 4
            return

        col_count = len(headers)
        stat_table_width = page_width - (margin * 2)
        stat_col_width = stat_table_width / max(col_count, 1)
        header_height = 20

        ensure_space(header_height + 24)
        current_commands.append(
            _pdf_rect(margin, current_y - header_height, stat_table_width, header_height, fill_color=gold, stroke_color=light_border)
        )
        x_cursor = margin
        for header in headers:
            current_commands.append(_pdf_text_block(x_cursor + 6, current_y - 13, [header], 'F2', 9, navy))
            x_cursor += stat_col_width
        current_y -= header_height

        for row_index, row in enumerate(stat_rows):
            wrapped_cells = []
            max_lines = 1
            for value in row:
                wrapped = _wrap_pdf_cell(value, stat_col_width - 10, 8)
                wrapped_cells.append(wrapped)
                max_lines = max(max_lines, len(wrapped))
            row_height = max(22, max_lines * 11 + 8)
            ensure_space(row_height + 2)
            fill = white if row_index % 2 == 0 else row_alt
            current_commands.append(
                _pdf_rect(margin, current_y - row_height, stat_table_width, row_height, fill_color=fill, stroke_color=light_border)
            )
            x_cursor = margin
            for column_index, wrapped in enumerate(wrapped_cells):
                if column_index > 0:
                    current_commands.append(_pdf_rect(x_cursor, current_y - row_height, 0.7, row_height, fill_color=light_border))
                current_commands.append(_pdf_text_block(x_cursor + 6, current_y - 12, wrapped, 'F1', 8, body_color))
                x_cursor += stat_col_width
            current_y -= row_height
        current_y -= 8

    def draw_table_header():
        nonlocal current_y
        ensure_space(30)
        current_commands.append(_pdf_rect(table_x, current_y - 26, table_width, 26, fill_color=gold))
        x_cursor = table_x
        for label, width in columns:
            current_commands.append(_pdf_text_block(x_cursor + 6, current_y - 17, [label], 'F2', header_font_size, navy))
            x_cursor += width
        current_y -= 26

    start_page()

    filters_lines = report_context.get('filters_lines') or []
    summary_cards = report_context.get('summary_cards') or []
    stat_sections = report_context.get('stat_sections') or []
    insights = report_context.get('insights') or []

    if filters_lines:
        draw_section_title('Filtros aplicados')
        draw_wrapped_lines(filters_lines)
        current_y -= 6

    if summary_cards:
        draw_section_title('Resumen ejecutivo')
        draw_summary_cards(summary_cards)
        current_y -= 4

    if stat_sections:
        for section in stat_sections:
            draw_stat_table(section)

    if insights:
        draw_section_title('Hallazgos para toma de decisiones')
        draw_wrapped_lines([f'- {insight}' for insight in insights], indent=8)
        current_y -= 8

    draw_section_title('Detalle de registros')
    draw_table_header()

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
                draw_table_header()

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
