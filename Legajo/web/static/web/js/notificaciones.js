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

    if (!Array.isArray(notificaciones) || notificaciones.length === 0) {
      lista.innerHTML = '<p style="padding: 20px;">No tienes notificaciones por ahora.</p>';
      return;
    }

    notificaciones.forEach((notificacion) => {
      const item = document.createElement('div');
      item.className = `chat-item${notificacion.esNueva ? ' no-leido' : ''}`;
      item.innerHTML = `
        <div class="chat-main">
          <div class="chat-name">${escapeHtml(notificacion.usuario)}</div>
          <div class="chat-info">${escapeHtml(notificacion.fecha)}</div>
          <div class="chat-last-message">${escapeHtml(notificacion.mensaje)}</div>
        </div>
        ${notificacion.puedeAceptar ? `<div class="chat-actions"><button class="btn-amarillo btn-ver-inventario" data-intercambio-id="${notificacion.id}" data-usuario="${escapeHtml(notificacion.usuario)}">Ver inventario</button></div>` : ''}
      `;
      lista.appendChild(item);
    });

    lista.querySelectorAll('.btn-ver-inventario').forEach((button) => {
      button.addEventListener('click', () => abrirInventarioSolicitante(
        button.dataset.intercambioId,
        button.dataset.usuario
      ));
    });
  } catch (error) {
    console.error('Error cargando notificaciones:', error);
    lista.innerHTML = '<p style="padding: 20px;">No se pudieron cargar las notificaciones.</p>';
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
              <img class="inventory-img" src="${escapeHtml(libro.urlImagen || '/static/web/imgs/libropredeterminado1.png')}" alt="${escapeHtml(libro.titulo)}">
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
          <p class="inventory-modal-help">Selecciona un libro para completar el intercambio.</p>
          <div id="inventorySelectionContainer">${renderizarCards()}</div>
        </div>
      `,
      showCancelButton: true,
      confirmButtonText: 'Aceptar intercambio',
      cancelButtonText: 'Cancelar',
      customClass: {
        popup: 'perfil-swal-popup inventory-swal-popup',
        title: 'perfil-swal-title',
        htmlContainer: 'perfil-swal-html',
        confirmButton: 'perfil-swal-confirm',
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

document.addEventListener('DOMContentLoaded', cargarNotificaciones);
