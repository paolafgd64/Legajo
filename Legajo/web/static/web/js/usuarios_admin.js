const API_USUARIOS_ADMIN = '/api/admin/usuarios';
const tablaUsuariosAdmin = document.getElementById('tablaUsuariosAdmin');

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
