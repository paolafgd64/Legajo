async function obtenerUsuarioActualNotificaciones() {
  const res = await fetch('/api/auth/me', {
    headers: {
      Accept: 'application/json'
    }
  });

  if (res.status === 401) {
    window.location.href = '/login/';
    return null;
  }

  if (!res.ok) {
    throw new Error('No se pudo obtener el usuario actual');
  }

  return await res.json();
}

function getCsrfToken() {
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
    .replaceAll('"', '&quot;');
}

function obtenerMetaNotificacion(notificacion) {
  const tipo = String(notificacion.tipo || '').toLowerCase();
  const estado = String(notificacion.estado || '').toLowerCase();

  if (tipo === 'sistema') {
    return {
      clase: 'sistema',
      icono: 'fa-shield-halved',
      etiqueta: 'Sistema'
    };
  }

  if (estado === 'aceptado') {
    return {
      clase: 'aceptada',
      icono: 'fa-handshake',
      etiqueta: 'Aceptado'
    };
  }

  if (estado === 'rechazado') {
    return {
      clase: 'rechazada',
      icono: 'fa-circle-xmark',
      etiqueta: 'Rechazado'
    };
  }

  if (estado === 'cancelado') {
    return {
      clase: 'cancelada',
      icono: 'fa-ban',
      etiqueta: 'Cancelado'
    };
  }

  if (estado === 'completado') {
    return {
      clase: 'completada',
      icono: 'fa-circle-check',
      etiqueta: 'Completado'
    };
  }

  return {
    clase: 'pendiente',
    icono: 'fa-book-open-reader',
    etiqueta: 'Intercambio'
  };
}

function actualizarResumenNotificaciones(notificaciones) {
  const count = document.getElementById('notificacionesCount');
  const resumen = document.getElementById('notificacionesResumen');
  const total = Array.isArray(notificaciones) ? notificaciones.length : 0;
  const nuevas = Array.isArray(notificaciones) ? notificaciones.filter((item) => item.esNueva).length : 0;

  if (count) {
    count.textContent = `${total} ${total === 1 ? 'notificacion' : 'notificaciones'}`;
  }

  if (resumen) {
    if (!total) {
      resumen.textContent = 'No hay actividad pendiente por revisar.';
    } else if (nuevas) {
      resumen.textContent = `${nuevas} ${nuevas === 1 ? 'nueva' : 'nuevas'} requieren tu atencion.`;
    } else {
      resumen.textContent = 'Estas al dia con tu actividad reciente.';
    }
  }
}

function normalizarTelefonoWhatsapp(telefono) {
  const limpio = String(telefono || '').replace(/\D/g, '');
  if (!limpio) return '';
  if (limpio.startsWith('57')) return limpio;
  return `57${limpio}`;
}

async function parseJsonResponse(response) {
  const rawText = await response.text();
  try {
    return JSON.parse(rawText);
  } catch (error) {
    const isHtml = rawText.trim().startsWith('<!DOCTYPE') || rawText.trim().startsWith('<html');
    if (isHtml) {
      throw new Error(`El servidor devolvio HTML en vez de JSON (estado ${response.status}). Recarga la pagina e intenta de nuevo.`);
    }
    throw new Error('Respuesta invalida del servidor.');
  }
}

async function marcarNotificacionesComoLeidas() {
  const response = await fetch('/api/notificaciones/marcar-leidas', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'X-CSRFToken': getCsrfToken()
    }
  });

  if (!response.ok) {
    throw new Error('No se pudieron marcar las notificaciones como leidas');
  }

  return response.json();
}

async function cargarNotificaciones() {
  const lista = document.getElementById('listaNotificaciones');
  if (!lista) return;

  try {
    const usuario = await obtenerUsuarioActualNotificaciones();
    if (!usuario) return;

    const nombrePanel = document.getElementById('n2');
    const nombrePerfil = document.getElementById('n3');
    if (nombrePanel) nombrePanel.textContent = usuario.primerNombre || 'Usuario';
    if (nombrePerfil) nombrePerfil.textContent = usuario.primerNombre || 'Usuario';

    const res = await fetch('/api/notificaciones', {
      headers: {
        Accept: 'application/json'
      }
    });

    if (!res.ok) {
      throw new Error('No se pudieron cargar las notificaciones');
    }

    const notificaciones = await res.json();
    lista.innerHTML = '';
    actualizarResumenNotificaciones(notificaciones);
    window.actualizarContadorNotificaciones?.();

    if (!Array.isArray(notificaciones) || notificaciones.length === 0) {
      lista.innerHTML = `
        <div class="notificaciones-state notificaciones-empty">
          <i class="fas fa-inbox" aria-hidden="true"></i>
          <strong>No tienes notificaciones por ahora</strong>
          <span>Cuando alguien solicite un intercambio o el equipo responda una novedad, aparecera aqui.</span>
        </div>
      `;
      return;
    }

    notificaciones.forEach((notificacion) => {
      const meta = obtenerMetaNotificacion(notificacion);
      const item = document.createElement('div');
      item.className = `notificacion-card ${meta.clase}${notificacion.esNueva ? ' no-leido' : ''}`;
      item.innerHTML = `
        <div class="notificacion-icon" aria-hidden="true">
          <i class="fas ${meta.icono}"></i>
        </div>
        <div class="notificacion-main">
          <div class="notificacion-topline">
            <span class="notificacion-badge">${escapeHtml(meta.etiqueta)}</span>
            ${notificacion.esNueva ? '<span class="notificacion-new">Nuevo</span>' : ''}
          </div>
          <h3>${escapeHtml(notificacion.usuario)}</h3>
          <p>${escapeHtml(notificacion.mensaje)}</p>
          <time>${escapeHtml(notificacion.fecha)}</time>
        </div>
        ${notificacion.puedeAceptar ? `<div class="notificacion-actions"><button class="btn-amarillo btn-ver-inventario" data-intercambio-id="${notificacion.id}" data-usuario="${escapeHtml(notificacion.usuario)}"><i class="fas fa-book" aria-hidden="true"></i><span>Ver inventario</span></button></div>` : ''}
      `;
      lista.appendChild(item);
    });

    lista.querySelectorAll('.btn-ver-inventario').forEach((button) => {
      button.addEventListener('click', () => abrirInventarioSolicitante(
        button.dataset.intercambioId,
        button.dataset.usuario
      ));
    });

    try {
      await marcarNotificacionesComoLeidas();
      window.actualizarContadorNotificaciones?.();
    } catch (error) {
      console.warn('No se pudieron marcar las notificaciones como leidas:', error);
    }
  } catch (error) {
    console.error('Error cargando notificaciones:', error);
    actualizarResumenNotificaciones([]);
    window.actualizarContadorNotificaciones?.();
    lista.innerHTML = `
      <div class="notificaciones-state notificaciones-error">
        <i class="fas fa-triangle-exclamation" aria-hidden="true"></i>
        <strong>No se pudieron cargar las notificaciones</strong>
        <span>Recarga la pagina o intenta de nuevo en unos segundos.</span>
      </div>
    `;
  }
}

async function abrirInventarioSolicitante(intercambioId, nombreUsuario) {
  try {
    const response = await fetch(`/api/intercambios/${intercambioId}/inventario`, {
      headers: {
        Accept: 'application/json'
      }
    });

    const libros = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(libros.message || 'No se pudo cargar el inventario del solicitante.');
    }

    let libroSeleccionadoId = null;

    const renderizarCards = () => {
      if (!Array.isArray(libros) || libros.length === 0) {
        return '<p class="inventory-empty">Esta persona no tiene libros disponibles para intercambio.</p>';
      }

      return `
        <div class="inventory-grid">
          ${libros.map((libro) => `
            <button type="button" class="inventory-item js-select-libro${String(libroSeleccionadoId) === String(libro.id) ? ' selected' : ''}" data-libro-id="${libro.id}">
              <img class="inventory-img" src="${escapeHtml(libro.urlImagen || '/static/gestion_libros/imgs/libropredeterminado1.png')}" alt="${escapeHtml(libro.titulo)}">
              <div class="inventory-meta">
                <strong class="inventory-title">${escapeHtml(libro.titulo)}</strong>
                <div class="inventory-author">${escapeHtml(libro.autor || 'Autor desconocido')}</div>
                <div class="inventory-state">${escapeHtml(libro.estado || '')}</div>
              </div>
            </button>
          `).join('')}
        </div>
      `;
    };

    const modal = await Swal.fire({
      title: `Inventario de ${nombreUsuario}`,
      width: 920,
      html: `
        <div class="perfil-modal-form inventory-modal-panel">
          <p class="inventory-modal-help">Selecciona un libro para aceptar el intercambio. Si no te interesa ninguno, puedes rechazar la solicitud.</p>
          <div id="inventorySelectionContainer">${renderizarCards()}</div>
        </div>
      `,
      showCancelButton: true,
      showDenyButton: true,
      confirmButtonText: 'Aceptar intercambio',
      denyButtonText: 'Rechazar intercambio',
      cancelButtonText: 'Volver',
      customClass: {
        popup: 'perfil-swal-popup inventory-swal-popup',
        title: 'perfil-swal-title',
        htmlContainer: 'perfil-swal-html',
        confirmButton: 'perfil-swal-confirm',
        denyButton: 'perfil-swal-deny',
        cancelButton: 'perfil-swal-cancel'
      },
      buttonsStyling: false,
      didOpen: () => {
        const container = document.getElementById('inventorySelectionContainer');
        const attachSelection = () => {
          container.querySelectorAll('.js-select-libro').forEach((card) => {
            card.addEventListener('click', () => {
              libroSeleccionadoId = card.dataset.libroId;
              container.innerHTML = renderizarCards();
              attachSelection();
            });
          });
        };
        attachSelection();
      },
      preConfirm: () => {
        if (!libroSeleccionadoId) {
          Swal.showValidationMessage('Selecciona un libro del solicitante antes de aceptar.');
          return false;
        }
        return { libroCambioId: libroSeleccionadoId };
      }
    });

    if (modal.isDenied) {
      await rechazarIntercambio(intercambioId);
      return;
    }

    if (!modal.isConfirmed) return;

    const acceptResponse = await fetch(`/api/intercambios/${intercambioId}/accept`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(modal.value)
    });

    const result = await parseJsonResponse(acceptResponse);
    if (!acceptResponse.ok) {
      throw new Error(result.message || 'No se pudo aceptar el intercambio.');
    }

    await Swal.fire({
      icon: 'success',
      title: 'Intercambio aceptado',
      text: result.message || 'El intercambio fue aceptado correctamente.'
    });

    const telefonoWhatsapp = normalizarTelefonoWhatsapp(result.telefonoWhatsapp);
    if (telefonoWhatsapp && result.mensajeWhatsapp) {
      const urlWhatsapp = `https://wa.me/${telefonoWhatsapp}?text=${encodeURIComponent(result.mensajeWhatsapp)}`;
      window.open(urlWhatsapp, '_blank', 'noopener');
    }

    cargarNotificaciones();
  } catch (error) {
    console.error('Error aceptando intercambio:', error);
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: error.message || 'No se pudo procesar el intercambio.'
    });
  }
}

async function rechazarIntercambio(intercambioId) {
  const confirmacion = await Swal.fire({
    icon: 'warning',
    title: 'Rechazar intercambio',
    text: 'Esta solicitud se marcara como rechazada y ya no podra ser aceptada.',
    showCancelButton: true,
    confirmButtonText: 'Si, rechazar',
    cancelButtonText: 'Volver',
    customClass: {
      popup: 'legajo-swal-popup',
      title: 'legajo-swal-title',
      htmlContainer: 'legajo-swal-html',
      confirmButton: 'legajo-swal-deny',
      cancelButton: 'legajo-swal-cancel'
    },
    buttonsStyling: false
  });

  if (!confirmacion.isConfirmed) return;

  const rejectResponse = await fetch(`/api/intercambios/${intercambioId}/reject`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({})
  });

  const result = await parseJsonResponse(rejectResponse);
  if (!rejectResponse.ok) {
    throw new Error(result.message || 'No se pudo rechazar el intercambio.');
  }

  await Swal.fire({
    icon: 'success',
    title: 'Intercambio rechazado',
    text: result.message || 'La solicitud fue rechazada correctamente.'
  });

  cargarNotificaciones();
}

document.addEventListener('DOMContentLoaded', cargarNotificaciones);

