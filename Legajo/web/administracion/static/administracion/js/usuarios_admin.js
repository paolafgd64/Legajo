const API_USUARIOS_ADMIN = '/api/admin/usuarios';
const tablaUsuariosAdmin = document.getElementById('tablaUsuariosAdmin');
const formImportacionUsuarios = document.querySelector('#modalImportacionUsuarios form');
const legajoSwalClasses = {
  popup: 'legajo-swal-popup',
  title: 'legajo-swal-title',
  htmlContainer: 'legajo-swal-html',
  confirmButton: 'legajo-swal-confirm',
  denyButton: 'legajo-swal-deny',
  cancelButton: 'legajo-swal-cancel',
  input: 'legajo-swal-input'
};

function getCookie(name) {
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith(`${name}=`)) {
      return decodeURIComponent(trimmed.substring(name.length + 1));
    }
  }
  return '';
}

function getCsrfToken() {
  return getCookie('csrftoken')
    || document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || '';
}

async function parseJsonResponse(response) {
  const rawText = await response.text();
  try {
    return JSON.parse(rawText);
  } catch (error) {
    throw new Error('El servidor devolvio una respuesta inesperada.');
  }
}

function construirResumenImportacion(resultado) {
  if (!resultado) {
    return 'La importacion finalizo correctamente.';
  }

  const bloques = [
    `
      <div style="display:grid; grid-template-columns:repeat(3, minmax(110px, 1fr)); gap:12px; margin:8px 0 18px;">
        <div style="background:#ecfdf3; border:1px solid #bbf7d0; border-radius:14px; padding:12px 10px; text-align:center;">
          <div style="font-size:0.86rem; color:#166534; font-weight:700;">Creados</div>
          <div style="font-size:1.35rem; color:#14532d; font-weight:800; margin-top:4px;">${resultado.creados || 0}</div>
        </div>
        <div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:14px; padding:12px 10px; text-align:center;">
          <div style="font-size:0.86rem; color:#1d4ed8; font-weight:700;">Actualizados</div>
          <div style="font-size:1.35rem; color:#1e3a8a; font-weight:800; margin-top:4px;">${resultado.actualizados || 0}</div>
        </div>
        <div style="background:#fff7ed; border:1px solid #fed7aa; border-radius:14px; padding:12px 10px; text-align:center;">
          <div style="font-size:0.86rem; color:#c2410c; font-weight:700;">Omitidos</div>
          <div style="font-size:1.35rem; color:#9a3412; font-weight:800; margin-top:4px;">${resultado.omitidos || 0}</div>
        </div>
      </div>
    `
  ];

  const detalles = resultado.detalles || {};
  const secciones = [
    { key: 'creados', title: 'Usuarios creados' },
    { key: 'actualizados', title: 'Usuarios actualizados' },
    { key: 'omitidos', title: 'Usuarios omitidos' }
  ];

  secciones.forEach(({ key, title }) => {
    const items = Array.isArray(detalles[key]) ? detalles[key] : [];
    if (!items.length) return;

    const listado = items
      .map((item) => `
        <li style="margin:0 0 10px; color:#1e293b; line-height:1.5;">
          <strong style="color:#020617; font-weight:800;">${escapeHtml(item.email)}</strong><br>
          <span style="color:#334155; font-weight:600;">${escapeHtml(item.motivo)}</span>
        </li>
      `)
      .join('');

    bloques.push(`
      <div style="margin-top:14px; text-align:left; background:#f8fafc; border:1px solid #cbd5e1; border-radius:14px; padding:14px 16px;">
        <div style="font-weight:800; color:#020617; margin-bottom:8px; font-size:1rem;">${title}</div>
        <ul style="margin:0; padding-left:18px;">${listado}</ul>
      </div>
    `);
  });

  return `
    <div style="color:#020617;">
      ${bloques[0]}
      <div style="max-height:320px; overflow-y:auto; padding-right:6px;">
        ${bloques.slice(1).join('')}
      </div>
    </div>
  `;
}

async function cargarUsuariosAdmin() {
  const nombre = document.getElementById('filtroNombreUsuario')?.value.trim() || '';
  const correo = document.getElementById('filtroCorreoUsuario')?.value.trim() || '';
  const ciudad = document.getElementById('filtroCiudadUsuario')?.value.trim() || '';
  const rol = document.getElementById('filtroRolUsuario')?.value || '';
  const estado = document.getElementById('filtroEstadoUsuario')?.value || '';

  const params = new URLSearchParams();
  if (nombre) params.append('nombre', nombre);
  if (correo) params.append('correo', correo);
  if (ciudad) params.append('ciudad', ciudad);
  if (rol) params.append('rol', rol);
  if (estado) params.append('estado', estado);

  const url = params.toString() ? `${API_USUARIOS_ADMIN}?${params.toString()}` : API_USUARIOS_ADMIN;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Error consultando usuarios: ${response.status}`);
    }
    const usuarios = await response.json();
    renderizarUsuarios(usuarios);
  } catch (error) {
    console.error(error);
    if (tablaUsuariosAdmin) {
      tablaUsuariosAdmin.innerHTML = '<tr><td colspan="7">No se pudieron cargar los usuarios.</td></tr>';
    }
  }
}

function escapeHtml(valor) {
  return String(valor || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function renderizarUsuarios(usuarios) {
  if (!tablaUsuariosAdmin) return;

  tablaUsuariosAdmin.innerHTML = '';
  if (!usuarios || usuarios.length === 0) {
    tablaUsuariosAdmin.innerHTML = '<tr><td colspan="7">No se encontraron usuarios.</td></tr>';
    return;
  }

  usuarios.forEach((usuario) => {
    const fila = document.createElement('tr');
    const estaActivo = Boolean(usuario.activo);
    const estadoTitle = estaActivo
      ? 'Desactivar usuario'
      : `Inactivo${usuario.motivoDesactivacion ? `: ${usuario.motivoDesactivacion}` : ''}`;
    fila.innerHTML = `
      <td>${escapeHtml(usuario.nombreCompleto)}</td>
      <td>${escapeHtml(usuario.correo)}</td>
      <td>${escapeHtml(usuario.ciudad)}</td>
      <td>${escapeHtml(usuario.telefono)}</td>
      <td>${escapeHtml(usuario.rol)}</td>
      <td>
        <button
          type="button"
          class="estado-usuario-boton ${estaActivo ? 'activo' : 'inactivo'}"
          data-user-id="${usuario.id}"
          data-activo="${estaActivo ? 'true' : 'false'}"
          data-nombre="${escapeHtml(usuario.nombreCompleto)}"
          title="${escapeHtml(estadoTitle)}"
        >
          ${estaActivo ? '<i class="fas fa-check-circle"></i> Activo' : '<i class="fas fa-ban"></i> Inactivo'}
        </button>
      </td>
      <td>
        <button
          type="button"
          class="inventario-usuario-boton"
          data-user-id="${usuario.id}"
          data-nombre="${escapeHtml(usuario.nombreCompleto)}"
          title="Ver inventario"
        >
          <i class="fas fa-book-open"></i> Ver
        </button>
      </td>
    `;
    fila.querySelector('.estado-usuario-boton')?.addEventListener('click', (event) => {
      event.stopPropagation();
      manejarCambioEstadoUsuario(event.currentTarget);
    });
    fila.querySelector('.inventario-usuario-boton')?.addEventListener('click', (event) => {
      event.stopPropagation();
      abrirInventarioUsuario(event.currentTarget);
    });
    tablaUsuariosAdmin.appendChild(fila);
  });
}

function renderizarInventarioUsuario(libros) {
  if (!Array.isArray(libros) || libros.length === 0) {
    return '<p class="inventory-empty">Este usuario no tiene libros en su inventario.</p>';
  }

  return `
    <div class="inventory-grid">
      ${libros.map((libro) => `
        <div class="inventory-item inventory-item-readonly">
          <img class="inventory-img" src="${escapeHtml(libro.urlImagen || '/static/gestion_libros/imgs/libropredeterminado1.png')}" alt="${escapeHtml(libro.titulo)}">
          <div class="inventory-meta">
            <strong class="inventory-title">${escapeHtml(libro.titulo || 'Sin titulo')}</strong>
            <div class="inventory-author">${escapeHtml(libro.autor || 'Autor desconocido')}</div>
            <div class="inventory-state">${escapeHtml(libro.estado || '')}</div>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

async function abrirInventarioUsuario(button) {
  const userId = button.dataset.userId;
  const nombre = button.dataset.nombre || 'Usuario';
  if (!userId) return;

  if (window.Swal) {
    Swal.fire({
      title: 'Cargando inventario',
      text: 'Consultando los libros del usuario.',
      allowOutsideClick: false,
      customClass: legajoSwalClasses,
      didOpen: () => Swal.showLoading()
    });
  }

  try {
    const response = await fetch(`${API_USUARIOS_ADMIN}/${userId}/inventario`, {
      headers: {
        Accept: 'application/json'
      }
    });
    const data = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(data.message || 'No se pudo cargar el inventario.');
    }

    if (window.Swal) {
      await Swal.fire({
        title: `Inventario de ${nombre}`,
        width: 920,
        html: `
          <div class="perfil-modal-form inventory-modal-panel">
            <p class="inventory-modal-help">Libros registrados por este usuario.</p>
            ${renderizarInventarioUsuario(data.libros)}
          </div>
        `,
        confirmButtonText: 'Cerrar',
        buttonsStyling: false,
        customClass: {
          ...legajoSwalClasses,
          popup: 'legajo-swal-popup inventory-swal-popup'
        }
      });
    } else {
      window.alert(`Inventario de ${nombre}: ${Array.isArray(data.libros) ? data.libros.length : 0} libros.`);
    }
  } catch (error) {
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'No se pudo cargar',
        text: error.message || 'No se pudo cargar el inventario.',
        confirmButtonText: 'Continuar',
        buttonsStyling: false,
        customClass: legajoSwalClasses
      });
    } else {
      window.alert(error.message || 'No se pudo cargar el inventario.');
    }
  }
}

async function actualizarEstadoUsuario(userId, payload) {
  const response = await fetch(`${API_USUARIOS_ADMIN}/${userId}/estado`, {
    method: 'PATCH',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify(payload)
  });

  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.message || 'No se pudo actualizar el usuario.');
  }
  return data;
}

async function manejarCambioEstadoUsuario(button) {
  const userId = button.dataset.userId;
  const estaActivo = button.dataset.activo === 'true';
  const nombre = button.dataset.nombre || 'este usuario';

  if (!userId) return;

  if (!estaActivo) {
    if (window.Swal) {
      const result = await Swal.fire({
        icon: 'question',
        title: 'Activar usuario',
        text: `Quieres activar nuevamente a ${nombre}?`,
        showCancelButton: true,
        confirmButtonText: 'Si, activar',
        cancelButtonText: 'Cancelar',
        buttonsStyling: false,
        customClass: legajoSwalClasses
      });
      if (!result.isConfirmed) return;
    } else if (!window.confirm(`Quieres activar nuevamente a ${nombre}?`)) {
      return;
    }

    try {
      await actualizarEstadoUsuario(userId, { activo: true });
      await cargarUsuariosAdmin();
      if (window.Swal) {
        await Swal.fire({
          icon: 'success',
          title: 'Usuario activado',
          timer: 1600,
          showConfirmButton: false,
          customClass: legajoSwalClasses
        });
      } else {
        window.alert('Usuario activado.');
      }
    } catch (error) {
      if (window.Swal) {
        Swal.fire({
          icon: 'error',
          title: 'No se pudo activar',
          text: error.message,
          confirmButtonText: 'Continuar',
          buttonsStyling: false,
          customClass: legajoSwalClasses
        });
      } else {
        window.alert(error.message || 'No se pudo activar.');
      }
    }
    return;
  }

  let motivo = '';
  if (window.Swal) {
    const result = await Swal.fire({
      icon: 'warning',
      title: 'Desactivar usuario',
      html: `<p style="margin-bottom:12px;">Escribe el motivo por el que vas a desactivar a <strong>${escapeHtml(nombre)}</strong>.</p>`,
      input: 'textarea',
      inputPlaceholder: 'Motivo de desactivacion...',
      inputAttributes: {
        'aria-label': 'Motivo de desactivacion'
      },
      showCancelButton: true,
      confirmButtonText: 'Desactivar',
      cancelButtonText: 'Cancelar',
      buttonsStyling: false,
      customClass: legajoSwalClasses,
      inputValidator: (value) => {
        if (!value || value.trim().length < 10) {
          return 'Escribe un motivo de al menos 10 caracteres.';
        }
        return null;
      }
    });

    if (!result.isConfirmed) return;
    motivo = result.value.trim();
  } else {
    const value = window.prompt(`Motivo para desactivar a ${nombre}:`);
    if (value === null) return;
    motivo = value.trim();
    if (motivo.length < 10) {
      window.alert('Escribe un motivo de al menos 10 caracteres.');
      return;
    }
  }

  try {
    await actualizarEstadoUsuario(userId, {
      activo: false,
      motivo
    });
    await cargarUsuariosAdmin();
    if (window.Swal) {
      await Swal.fire({
        icon: 'success',
        title: 'Usuario desactivado',
        text: 'El motivo quedo guardado y se mostrara si intenta iniciar sesion.',
        confirmButtonText: 'Continuar',
        buttonsStyling: false,
        customClass: legajoSwalClasses
      });
    } else {
      window.alert('Usuario desactivado.');
    }
  } catch (error) {
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'No se pudo desactivar',
        text: error.message,
        confirmButtonText: 'Continuar',
        buttonsStyling: false,
        customClass: legajoSwalClasses
      });
    } else {
      window.alert(error.message || 'No se pudo desactivar.');
    }
  }
}

function limpiarArchivoImportacion() {
  const inputArchivo = document.getElementById('archivo_usuarios');
  const nombreArchivo = document.getElementById('nombreArchivoSeleccionado');
  const toggle = document.getElementById('toggleImportacionUsuarios');

  if (inputArchivo) {
    inputArchivo.value = '';
  }
  if (nombreArchivo) {
    nombreArchivo.textContent = 'Sin archivos seleccionados';
  }
  if (toggle) {
    toggle.checked = false;
  }
}

function cerrarModalImportacion() {
  limpiarArchivoImportacion();
}

async function enviarImportacionUsuarios(event) {
  event.preventDefault();

  const inputArchivo = document.getElementById('archivo_usuarios');
  const archivo = inputArchivo?.files && inputArchivo.files[0];
  if (!archivo) {
    if (window.Swal) {
      Swal.fire({
        icon: 'warning',
        title: 'Archivo requerido',
        text: 'Selecciona un archivo JSON o Excel antes de continuar.',
        confirmButtonText: 'Continuar',
        buttonsStyling: false,
        customClass: legajoSwalClasses
      });
    }
    return;
  }

  const formData = new FormData(formImportacionUsuarios);
  const csrfToken = getCookie('csrftoken')
    || formImportacionUsuarios.querySelector('[name=csrfmiddlewaretoken]')?.value
    || '';

  if (window.Swal) {
    Swal.fire({
      title: 'Importando usuarios',
      text: 'Estamos procesando el archivo.',
      allowOutsideClick: false,
      customClass: legajoSwalClasses,
      didOpen: () => Swal.showLoading()
    });
  }

  try {
    const response = await fetch('/usuarios_admin/', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
      },
      body: formData
    });

    const data = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(data.message || 'No se pudo importar el archivo.');
    }

    cerrarModalImportacion();
    await cargarUsuariosAdmin();

    if (window.Swal) {
      await Swal.fire({
        icon: 'success',
        title: 'Usuarios cargados',
        html: construirResumenImportacion(data.resultado),
        confirmButtonText: 'Continuar',
        buttonsStyling: false,
        customClass: legajoSwalClasses
      });
    }
  } catch (error) {
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'Error en la importacion',
        text: error.message || 'No se pudo importar el archivo.',
        confirmButtonText: 'Continuar',
        buttonsStyling: false,
        customClass: legajoSwalClasses
      });
    }
  }
}

document.getElementById('filtroNombreUsuario')?.addEventListener('input', cargarUsuariosAdmin);
document.getElementById('filtroCorreoUsuario')?.addEventListener('input', cargarUsuariosAdmin);
document.getElementById('filtroCiudadUsuario')?.addEventListener('input', cargarUsuariosAdmin);
document.getElementById('filtroRolUsuario')?.addEventListener('change', cargarUsuariosAdmin);
document.getElementById('filtroEstadoUsuario')?.addEventListener('change', cargarUsuariosAdmin);
tablaUsuariosAdmin?.addEventListener('click', (event) => {
  const button = event.target.closest('.estado-usuario-boton');
  if (button && !event.defaultPrevented) {
    manejarCambioEstadoUsuario(button);
  }
});

document.getElementById('btnLimpiarUsuarios')?.addEventListener('click', () => {
  document.getElementById('filtroNombreUsuario').value = '';
  document.getElementById('filtroCorreoUsuario').value = '';
  document.getElementById('filtroCiudadUsuario').value = '';
  document.getElementById('filtroRolUsuario').value = '';
  document.getElementById('filtroEstadoUsuario').value = '';
  cargarUsuariosAdmin();
});

document.getElementById('archivo_usuarios')?.addEventListener('change', () => {
  const inputArchivo = document.getElementById('archivo_usuarios');
  const nombreArchivo = document.getElementById('nombreArchivoSeleccionado');
  const archivo = inputArchivo?.files && inputArchivo.files[0];
  if (nombreArchivo) {
    nombreArchivo.textContent = archivo ? archivo.name : 'Sin archivos seleccionados';
  }
});

document.getElementById('limpiarArchivoImportacion')?.addEventListener('click', limpiarArchivoImportacion);
document.getElementById('cancelarImportacion')?.addEventListener('click', cerrarModalImportacion);
document.getElementById('cerrarModalImportacion')?.addEventListener('click', cerrarModalImportacion);
formImportacionUsuarios?.addEventListener('submit', enviarImportacionUsuarios);
document.getElementById('modalImportacionUsuarios')?.addEventListener('click', (event) => {
  if (event.target && event.target.id === 'modalImportacionUsuarios') {
    cerrarModalImportacion();
  }
});

const mensajeCargaUsuarios = document.getElementById('mensajeCargaUsuarios');
document.querySelector('[data-dismiss-feedback]')?.addEventListener('click', () => {
  mensajeCargaUsuarios?.remove();
});

if (mensajeCargaUsuarios) {
  window.setTimeout(() => {
    mensajeCargaUsuarios.remove();
  }, 7000);
}

window.addEventListener('load', cargarUsuariosAdmin);

