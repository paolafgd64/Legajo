const API_ADMIN_REPORTES = '/api/admin/reportes-usuarios';

function getCsrfTokenAdmin() {
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith('csrftoken=')) {
      return decodeURIComponent(trimmed.substring('csrftoken='.length));
    }
  }
  const hiddenToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  if (hiddenToken) {
    return hiddenToken;
  }
  return '';
}

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function construirUrlReportes() {
  const params = new URLSearchParams();
  const q = document.getElementById('filtroReporteBusqueda')?.value.trim() || '';
  const estado = document.getElementById('filtroReporteEstado')?.value || '';
  const motivo = document.getElementById('filtroReporteMotivo')?.value.trim() || '';

  if (q) params.set('q', q);
  if (estado) params.set('estado', estado);
  if (motivo) params.set('motivo', motivo);

  return params.toString() ? `${API_ADMIN_REPORTES}?${params.toString()}` : API_ADMIN_REPORTES;
}

function actualizarResumen(reportes) {
  const pendientes = reportes.filter((reporte) => reporte.estado === 'pendiente').length;
  const revisados = reportes.filter((reporte) => reporte.estado === 'revisado').length;
  const descartados = reportes.filter((reporte) => reporte.estado === 'descartado').length;

  const contadorPendientes = document.getElementById('contadorPendientes');
  const contadorRevisados = document.getElementById('contadorRevisados');
  const contadorDescartados = document.getElementById('contadorDescartados');

  if (contadorPendientes) contadorPendientes.textContent = pendientes;
  if (contadorRevisados) contadorRevisados.textContent = revisados;
  if (contadorDescartados) contadorDescartados.textContent = descartados;
}

function obtenerBadgeEstado(estado) {
  if (estado === 'revisado') return '<span class="trend positive">Revisado</span>';
  if (estado === 'descartado') return '<span class="trend negative">Descartado</span>';
  return '<span class="trend positive">Pendiente</span>';
}

function obtenerMensajeResolucion(estado) {
  if (estado === 'revisado') {
    return '<p class="reporte-resolucion revisado"><strong>Se marco como revisado.</strong></p>';
  }
  if (estado === 'descartado') {
    return '<p class="reporte-resolucion descartado"><strong>Se marco como descartado.</strong></p>';
  }
  return '';
}

function obtenerAccionesReporte(reporte) {
  if (reporte.estado !== 'pendiente') {
    return obtenerMensajeResolucion(reporte.estado);
  }

  return `
    <div class="botones-validacion">
      <button class="btn-negativo" type="button" data-action="descartar" data-report-id="${reporte.id}">
        <i class="fas fa-times"></i> Descartar
      </button>
      <button class="btn-positivo" type="button" data-action="revisar" data-report-id="${reporte.id}">
        <i class="fas fa-check"></i> Marcar revisado
      </button>
    </div>
  `;
}

function renderizarReportes(reportes) {
  const contenedor = document.getElementById('gridReportesUsuarios');
  if (!contenedor) return;

  actualizarResumen(reportes);
  contenedor.innerHTML = '';

  if (!Array.isArray(reportes) || reportes.length === 0) {
    contenedor.innerHTML = `
      <div class="reporte-card">
        <p><strong>No hay reportes</strong></p>
        <p>No se encontraron reportes con los filtros actuales.</p>
      </div>
    `;
    return;
  }

  reportes.forEach((reporte) => {
    const card = document.createElement('article');
    card.className = 'reporte-card';
    card.innerHTML = `
      <p><strong>Reportado:</strong> ${escapeHtml(reporte.usuarioReportado)}</p>
      <p><strong>Reportante:</strong> ${escapeHtml(reporte.usuarioReportante)}</p>
      <p><strong>Motivo:</strong> ${escapeHtml(reporte.motivo)}</p>
      <p><strong>Detalle:</strong><br>${escapeHtml(reporte.descripcion)}</p>
      <p><strong>Fecha:</strong> ${escapeHtml(reporte.fechaReporte)}</p>
      <p><strong>Estado:</strong> ${obtenerBadgeEstado(reporte.estado)}</p>
      ${obtenerAccionesReporte(reporte)}
    `;
    contenedor.appendChild(card);
  });
}

async function cargarReportesUsuarios() {
  const contenedor = document.getElementById('gridReportesUsuarios');
  if (contenedor) {
    contenedor.innerHTML = '<div class="reporte-card"><p>Cargando reportes...</p></div>';
  }

  try {
    const response = await fetch(construirUrlReportes(), {
      headers: { 'Accept': 'application/json' }
    });

    if (!response.ok) {
      throw new Error('No se pudieron cargar los reportes.');
    }

    const reportes = await response.json();
    renderizarReportes(reportes);
  } catch (error) {
    console.error('Error cargando reportes de usuarios:', error);
    if (contenedor) {
      contenedor.innerHTML = `
        <div class="reporte-card">
          <p><strong>Error</strong></p>
          <p>${escapeHtml(error.message || 'No se pudieron cargar los reportes.')}</p>
        </div>
      `;
    }
  }
}

async function actualizarEstadoReporte(reportId, estado) {
  const response = await fetch(`${API_ADMIN_REPORTES}/${reportId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfTokenAdmin()
    },
    body: JSON.stringify({ estado })
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || 'No se pudo actualizar el reporte.');
  }
  return data;
}

async function manejarAccionReporte(event) {
  const button = event.target.closest('button[data-action]');
  if (!button) return;

  const reportId = button.dataset.reportId;
  const action = button.dataset.action;
  const estado = action === 'revisar' ? 'revisado' : 'descartado';

  try {
    await actualizarEstadoReporte(reportId, estado);
    if (window.Swal) {
      await Swal.fire({
        icon: 'success',
        title: 'Reporte actualizado',
        text: `El reporte fue marcado como ${estado}.`
      });
    }
    await cargarReportesUsuarios();
  } catch (error) {
    console.error('Error actualizando reporte:', error);
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'No se pudo actualizar',
        text: error.message || 'Ocurrio un error al actualizar el reporte.'
      });
    }
  }
}

document.getElementById('filtroReporteBusqueda')?.addEventListener('input', cargarReportesUsuarios);
document.getElementById('filtroReporteEstado')?.addEventListener('change', cargarReportesUsuarios);
document.getElementById('filtroReporteMotivo')?.addEventListener('input', cargarReportesUsuarios);
document.getElementById('btnRecargarReportes')?.addEventListener('click', cargarReportesUsuarios);
document.getElementById('gridReportesUsuarios')?.addEventListener('click', manejarAccionReporte);

window.addEventListener('load', cargarReportesUsuarios);
