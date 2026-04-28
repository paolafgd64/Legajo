const API_USUARIOS_ADMIN = '/api/admin/usuarios';
const tablaUsuariosAdmin = document.getElementById('tablaUsuariosAdmin');
const formImportacionUsuarios = document.querySelector('#modalImportacionUsuarios form');

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
      tablaUsuariosAdmin.innerHTML = '<tr><td colspan="6">No se pudieron cargar los usuarios.</td></tr>';
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
    tablaUsuariosAdmin.innerHTML = '<tr><td colspan="6">No se encontraron usuarios.</td></tr>';
    return;
  }

  usuarios.forEach((usuario) => {
    const fila = document.createElement('tr');
    fila.innerHTML = `
      <td>${escapeHtml(usuario.nombreCompleto)}</td>
      <td>${escapeHtml(usuario.correo)}</td>
      <td>${escapeHtml(usuario.ciudad)}</td>
      <td>${escapeHtml(usuario.telefono)}</td>
      <td>${escapeHtml(usuario.rol)}</td>
      <td><span class="estado-usuario-badge ${usuario.estado === 'Activo' ? 'activo' : 'inactivo'}">${escapeHtml(usuario.estado)}</span></td>
    `;
    tablaUsuariosAdmin.appendChild(fila);
  });
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
        text: 'Selecciona un archivo JSON o Excel antes de continuar.'
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
        confirmButtonText: 'Continuar'
      });
    }
  } catch (error) {
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'Error en la importacion',
        text: error.message || 'No se pudo importar el archivo.'
      });
    }
  }
}

document.getElementById('filtroNombreUsuario')?.addEventListener('input', cargarUsuariosAdmin);
document.getElementById('filtroCorreoUsuario')?.addEventListener('input', cargarUsuariosAdmin);
document.getElementById('filtroCiudadUsuario')?.addEventListener('input', cargarUsuariosAdmin);
document.getElementById('filtroRolUsuario')?.addEventListener('change', cargarUsuariosAdmin);
document.getElementById('filtroEstadoUsuario')?.addEventListener('change', cargarUsuariosAdmin);

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
