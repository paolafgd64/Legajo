"""Funciones auxiliares del panel administrativo."""

import calendar
import datetime

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth

from ..gestion_libros.models import Libro
from ..intercambios.models import Intercambio
from .models import ReporteUsuario


User = get_user_model()


def _admin_required_response(request):
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Debes iniciar sesion para continuar.'}, status=401)
    if request.user.rol != User.Rol.ADMIN:
        return JsonResponse({'message': 'No tienes permisos de administrador para esta accion.'}, status=403)
    return None


def _serialize_admin_user(usuario):
    return {
        'id': usuario.id,
        'nombreCompleto': ' '.join(filter(None, [usuario.nombre1, usuario.nombre2, usuario.apellido1, usuario.apellido2])),
        'correo': usuario.email,
        'ciudad': usuario.ciudad,
        'telefono': usuario.telefono,
        'rol': usuario.get_rol_display(),
        'rolValor': usuario.rol,
        'estado': 'Activo' if usuario.activo and usuario.is_active else 'Inactivo',
        'activo': bool(usuario.activo and usuario.is_active),
        'motivoDesactivacion': usuario.motivo_desactivacion or '',
    }


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


def _build_monthly_cumulative_series(queryset, field_name):
    today = timezone.localdate()
    last_day = calendar.monthrange(today.year, today.month)[1]

    counts = (
        queryset.filter(
            **{
                f'{field_name}__year': today.year,
                f'{field_name}__month': today.month,
            }
        )
        .annotate(day=TruncDate(field_name))
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


def _get_admin_dashboard_context():
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
    reportes_mes = active_reports.filter(fecha_reporte__date__gte=current_month_start).count()
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
        },
    }
