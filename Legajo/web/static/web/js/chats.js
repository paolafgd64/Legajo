function getCsrfTokenChats() {
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith('csrftoken=')) {
      return decodeURIComponent(trimmed.substring('csrftoken='.length));
    }
  }

  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

async function parseJsonResponseChats(response) {
  const rawText = await response.text();
  try {
    return JSON.parse(rawText);
  } catch (error) {
    throw new Error('Respuesta invalida del servidor.');
  }
}

async function obtenerUsuarioActualChats() {
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

async function cargarIntercambios() {
  const lista = document.getElementById('listaIntercambios');
  if (!lista) return;

  try {
    const usuario = await obtenerUsuarioActualChats();
    if (!usuario) return;

    const nombreUsuario = document.getElementById('nombreUsuarioIntercambios');
    if (nombreUsuario) {
      nombreUsuario.textContent = usuario.primerNombre || 'Usuario';
    }

    const res = await fetch('/api/intercambios', {
      headers: {
        Accept: 'application/json'
      }
    });

    const intercambios = await parseJsonResponseChats(res);
    if (!res.ok) {
      throw new Error(intercambios.message || 'No se pudieron cargar los intercambios.');
    }

    lista.innerHTML = '';

    if (!Array.isArray(intercambios) || intercambios.length === 0) {
      lista.innerHTML = `
        <div class="intercambio-empty">
          <i class="fas fa-book"></i>
          <h3>Aun no tienes intercambios registrados</h3>
          <p>Cuando aceptes o solicites un intercambio, aqui veras el seguimiento completo.</p>
        </div>
      `;
      return;
    }

    intercambios.forEach((intercambio) => {
      const item = document.createElement('div');
      const estadoClase = intercambio.yaCompletado
        ? 'estado-completado'
        : intercambio.requiereConfirmacionDoble
          ? 'estado-validacion'
          : 'estado-proceso';
      const estadoTexto = intercambio.yaCompletado
        ? 'Completado'
        : intercambio.requiereConfirmacionDoble
          ? 'Pendiente de confirmacion'
          : 'En proceso';

      item.className = `chat-item intercambio-card${intercambio.estado === 'aceptado' ? ' no-leido' : ''}`;
      item.innerHTML = `
        <div class="chat-avatar intercambio-avatar">
          <img src="/static/web/imgs/profile.png" alt="Perfil">
        </div>
        <div class="chat-main">
          <div class="intercambio-top">
            <div>
              <div class="chat-name">${intercambio.usuario}</div>
              <div class="chat-info">${intercambio.rolUsuario} | ${intercambio.fecha}</div>
            </div>
            <span class="intercambio-estado ${estadoClase}">${estadoTexto}</span>
          </div>
          <div class="chat-last-message intercambio-descripcion">${intercambio.descripcion}</div>
          <div class="intercambio-libros">
            <div class="intercambio-libro-box">
              <span class="intercambio-libro-label">Libro solicitado</span>
              <strong>${intercambio.libroSolicitado}</strong>
            </div>
            <div class="intercambio-libro-box">
              <span class="intercambio-libro-label">Libro de cambio</span>
              <strong>${intercambio.libroCambio}</strong>
            </div>
          </div>
          ${intercambio.requiereConfirmacionDoble ? `
            <div class="pin-confirmacion">
              <div class="pin-copy">
                <span class="pin-copy-label">Confirmacion doble</span>
                <p>${intercambio.confirmoActual
                  ? 'Ya marcaste este intercambio como completado. Falta la otra persona.'
                  : 'Marca este intercambio como completado cuando ya hayas entregado y recibido el libro.'}</p>
                <p>${intercambio.confirmoContraparte
                  ? 'La otra persona ya confirmo.'
                  : 'La otra persona aun no confirma.'}</p>
              </div>
              ${intercambio.confirmoActual
                ? '<button class="btn-verde" type="button" disabled>Ya confirmaste</button>'
                : `<button class="btn-verde btn-confirmar-intercambio" data-intercambio-id="${intercambio.id}">Marcar intercambio completado</button>`}
            </div>
          ` : ''}
          ${intercambio.yaCompletado ? '<div class="intercambio-completado"><i class="fas fa-circle-check"></i> Intercambio completado</div>' : ''}
        </div>
      `;
      lista.appendChild(item);
    });

    lista.querySelectorAll('.btn-confirmar-intercambio').forEach((button) => {
      button.addEventListener('click', () => confirmarIntercambio(button.dataset.intercambioId));
    });
  } catch (error) {
    console.error('Error cargando intercambios:', error);
    lista.innerHTML = `
      <div class="intercambio-empty intercambio-empty-error">
        <i class="fas fa-triangle-exclamation"></i>
        <h3>No se pudieron cargar los intercambios</h3>
        <p>Intenta recargar la pagina para volver a consultar la informacion.</p>
      </div>
    `;
  }
}

async function confirmarIntercambio(intercambioId) {
  const confirmacion = await Swal.fire({
    icon: 'question',
    title: 'Confirmar intercambio',
    text: 'Marca esta accion solo si el intercambio ya se realizo presencialmente.',
    showCancelButton: true,
    confirmButtonText: 'Si, marcar completado',
    cancelButtonText: 'Cancelar'
  });

  if (!confirmacion.isConfirmed) return;

  try {
    const response = await fetch(`/api/intercambios/${intercambioId}/confirm`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfTokenChats()
      },
      body: JSON.stringify({})
    });

    const data = await parseJsonResponseChats(response);
    if (!response.ok) {
      throw new Error(data.message || 'No se pudo confirmar el intercambio.');
    }

    await Swal.fire({
      icon: 'success',
      title: data.completado ? 'Intercambio completado' : 'Confirmacion registrada',
      text: data.message || 'La confirmacion fue registrada correctamente.'
    });

    cargarIntercambios();
  } catch (error) {
    console.error('Error confirmando intercambio:', error);
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: error.message || 'No se pudo confirmar el intercambio.'
    });
  }
}

document.addEventListener('DOMContentLoaded', cargarIntercambios);
