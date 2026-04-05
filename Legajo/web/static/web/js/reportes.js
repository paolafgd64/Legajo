// /js/reportes.js
const API = '/api/libros';
const tablaBody = document.getElementById('tablaLibros');

async function cargarLibros() {
  const titulo = document.getElementById('filtroTitulo').value.trim();
  const autor = document.getElementById('filtroAutor').value.trim();
  const usuario = document.getElementById('filtroUsuario').value.trim();
  const genero = document.getElementById('filtroGenero').value;
  const estado = document.getElementById('filtroEstado').value;
  const calificacionMin = document.getElementById('filtroCalificacion').value;

  const params = new URLSearchParams();
  if (titulo) params.append('titulo', titulo);
  if (autor) params.append('autor', autor);
  if (usuario) params.append('usuario', usuario);
  if (genero) params.append('genero', genero);
  if (estado) params.append('estado', estado);

  const url = params.toString() ? `${API}?${params.toString()}` : API;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error('Error en petición: ' + res.status);
    const libros = await res.json();
    mostrarEnTabla(libros, calificacionMin);
  } catch (err) {
    console.error(err);
    tablaBody.innerHTML = `<tr><td colspan="5">Error cargando datos. Revisa consola.</td></tr>`;
  }
}

function mostrarEnTabla(libros, calificacionMin) {
  tablaBody.innerHTML = '';
  if (!libros || libros.length === 0) {
    tablaBody.innerHTML = '<tr><td colspan="5">No hay resultados</td></tr>';
    return;
  }

  // filtra por calificación si se seleccionó
  if (calificacionMin) {
    libros = libros.filter(l => (l.calificacion || 0) >= parseFloat(calificacionMin));
  }

  libros.forEach(l => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(l.usuario || '')}</td>
      <td class="clickable" data-lib='${escapeHtml(JSON.stringify(l))}'>${escapeHtml(l.titulo || '')}</td>
      <td>${escapeHtml(l.autor || '')}</td>
      <td>${escapeHtml(l.genero || '')}</td>
      <td>${escapeHtml(l.estado || '')}</td>
    `;
    tablaBody.appendChild(tr);
  });

  // click en título para abrir modal
  document.querySelectorAll('.clickable').forEach(td => {
    td.onclick = (e) => {
      const lib = JSON.parse(td.getAttribute('data-lib'));
      abrirModal(lib);
    };
  });
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;');
}

/* Modal (usa ids que ya tienes en tu HTML) */
const modal = document.getElementById('modalLibro');
const cerrarModal = document.getElementById('cerrarModal');
function abrirModal(lib) {
  document.getElementById('modalImg').src = lib.urlImagen || '';
  document.getElementById('modalTitulo').innerText = lib.titulo || '';
  document.getElementById('modalAutor').innerText = lib.autor || '';
  document.getElementById('modalGenero').innerText = lib.genero || '';
  document.getElementById('modalUsuario').innerText = lib.usuario || '';
  document.getElementById('modalCalificacion').innerText = lib.calificacion ?? 'N/A';
  document.getElementById('modalEstado').innerText = lib.estado || '';
  document.getElementById('modalDescripcion').innerText = lib.sinopsis || lib.descripcion || '';
  modal.style.display = 'block';
}
if (cerrarModal) cerrarModal.onclick = () => modal.style.display = 'none';
window.onclick = (e) => { if (e.target === modal) modal.style.display = 'none'; };

/* Event listeners para los filtros - se ejecutan en tiempo real */
document.getElementById('filtroTitulo').addEventListener('input', cargarLibros);
document.getElementById('filtroAutor').addEventListener('input', cargarLibros);
document.getElementById('filtroUsuario').addEventListener('input', cargarLibros);
document.getElementById('filtroGenero').addEventListener('change', cargarLibros);
document.getElementById('filtroEstado').addEventListener('change', cargarLibros);
document.getElementById('filtroCalificacion').addEventListener('change', cargarLibros);

/* Botones */
document.getElementById('btnLimpiar').addEventListener('click', () => {
  document.getElementById('filtroTitulo').value = '';
  document.getElementById('filtroAutor').value = '';
  document.getElementById('filtroUsuario').value = '';
  document.getElementById('filtroGenero').value = '';
  document.getElementById('filtroEstado').value = '';
  document.getElementById('filtroCalificacion').value = '';
  cargarLibros();
});

// Botón para generar PDF con filtros actuales
document.getElementById('btnGenerarPDF').addEventListener('click', () => {
  const titulo = document.getElementById('filtroTitulo').value.trim();
  const autor = document.getElementById('filtroAutor').value.trim();
  const usuario = document.getElementById('filtroUsuario').value.trim();
  const genero = document.getElementById('filtroGenero').value;
  const estado = document.getElementById('filtroEstado').value;

  const params = new URLSearchParams();
  if (titulo) params.append('titulo', titulo);
  if (autor) params.append('autor', autor);
  if (usuario) params.append('usuario', usuario);
  if (genero) params.append('genero', genero);
  if (estado) params.append('estado', estado);

  const url = params.toString() ? `/libros/reporte/pdf?${params.toString()}` : '/libros/reporte/pdf';
  window.location.href = url;
});

// recarga al cargar la página
const modalImportacion = document.getElementById('modalImportacionUsuarios');
const btnAbrirImportacion = document.getElementById('btnAbrirImportacion');
const btnCerrarImportacion = document.getElementById('cerrarModalImportacion');
const btnCancelarImportacion = document.getElementById('cancelarImportacion');
const inputArchivoImportacion = document.getElementById('archivo_usuarios');
const btnSeleccionarArchivo = document.getElementById('seleccionarArchivoImportacion');
const nombreArchivoSeleccionado = document.getElementById('nombreArchivoSeleccionado');
const btnLimpiarArchivoImportacion = document.getElementById('limpiarArchivoImportacion');

function limpiarArchivoImportacion() {
  if (inputArchivoImportacion) {
    inputArchivoImportacion.value = '';
  }
  if (nombreArchivoSeleccionado) {
    nombreArchivoSeleccionado.textContent = 'Sin archivos seleccionados';
  }
}

function abrirModalImportacion() {
  if (!modalImportacion) return;
  modalImportacion.style.display = 'flex';
  modalImportacion.setAttribute('aria-hidden', 'false');
}

function cerrarModalImportacion() {
  if (!modalImportacion) return;
  limpiarArchivoImportacion();
  modalImportacion.style.display = 'none';
  modalImportacion.setAttribute('aria-hidden', 'true');
}

if (btnAbrirImportacion) {
  btnAbrirImportacion.addEventListener('click', abrirModalImportacion);
}

if (btnCerrarImportacion) {
  btnCerrarImportacion.addEventListener('click', cerrarModalImportacion);
}

if (btnCancelarImportacion) {
  btnCancelarImportacion.addEventListener('click', cerrarModalImportacion);
}

if (inputArchivoImportacion && nombreArchivoSeleccionado) {
  inputArchivoImportacion.addEventListener('change', () => {
    const archivo = inputArchivoImportacion.files && inputArchivoImportacion.files[0];
    nombreArchivoSeleccionado.textContent = archivo ? archivo.name : 'Sin archivos seleccionados';
  });
}

if (btnLimpiarArchivoImportacion) {
  btnLimpiarArchivoImportacion.addEventListener('click', limpiarArchivoImportacion);
}

if (modalImportacion) {
  modalImportacion.addEventListener('click', (event) => {
    if (event.target === modalImportacion) {
      cerrarModalImportacion();
    }
  });
}

window.addEventListener('load', () => cargarLibros());
