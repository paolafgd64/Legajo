const API = '/api/libros';
const tablaBody = document.getElementById('tablaLibros');

async function cargarLibros() {
  const titulo = document.getElementById('filtroTitulo')?.value.trim() || '';
  const autor = document.getElementById('filtroAutor')?.value.trim() || '';
  const usuario = document.getElementById('filtroUsuario')?.value.trim() || '';
  const genero = document.getElementById('filtroGenero')?.value || '';
  const estado = document.getElementById('filtroEstado')?.value || '';
  const calificacionMin = document.getElementById('filtroCalificacion')?.value || '';

  const params = new URLSearchParams();
  if (titulo) params.append('titulo', titulo);
  if (autor) params.append('autor', autor);
  if (usuario) params.append('usuario', usuario);
  if (genero) params.append('genero', genero);
  if (estado) params.append('estado', estado);

  const url = params.toString() ? `${API}?${params.toString()}` : API;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Error en peticion: ${res.status}`);
    let libros = await res.json();

    if (calificacionMin) {
      libros = libros.filter((libro) => (libro.calificacion || 0) >= parseFloat(calificacionMin));
    }

    mostrarEnTabla(libros);
  } catch (err) {
    console.error(err);
    if (tablaBody) {
      tablaBody.innerHTML = '<tr><td colspan="5">Error cargando datos.</td></tr>';
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

function mostrarEnTabla(libros) {
  if (!tablaBody) return;

  tablaBody.innerHTML = '';
  if (!libros || libros.length === 0) {
    tablaBody.innerHTML = '<tr><td colspan="5">No hay resultados</td></tr>';
    return;
  }

  libros.forEach((libro) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(libro.usuario || '')}</td>
      <td class="clickable" data-lib='${escapeHtml(JSON.stringify(libro))}'>${escapeHtml(libro.titulo || '')}</td>
      <td>${escapeHtml(libro.autor || '')}</td>
      <td>${escapeHtml(libro.genero || '')}</td>
      <td>${escapeHtml(libro.estado || '')}</td>
    `;
    tablaBody.appendChild(tr);
  });

  document.querySelectorAll('.clickable').forEach((td) => {
    td.addEventListener('click', () => {
      const libro = JSON.parse(td.getAttribute('data-lib'));
      abrirModal(libro);
    });
  });
}

const modal = document.getElementById('modalLibro');
const cerrarModal = document.getElementById('cerrarModal');

function abrirModal(libro) {
  document.getElementById('modalImg').src = libro.urlImagen || libro.url_imagen || '';
  document.getElementById('modalTitulo').innerText = libro.titulo || '';
  document.getElementById('modalAutor').innerText = libro.autor || '';
  document.getElementById('modalGenero').innerText = libro.genero || '';
  document.getElementById('modalUsuario').innerText = libro.usuario || '';
  document.getElementById('modalCalificacion').innerText = libro.calificacion ?? 'N/A';
  document.getElementById('modalEstado').innerText = libro.estado || '';
  document.getElementById('modalDescripcion').innerText = libro.sinopsis || libro.descripcion || '';
  if (modal) {
    modal.style.display = 'block';
  }
}

cerrarModal?.addEventListener('click', () => {
  if (modal) {
    modal.style.display = 'none';
  }
});

window.addEventListener('click', (event) => {
  if (event.target === modal) {
    modal.style.display = 'none';
  }
});

document.getElementById('filtroTitulo')?.addEventListener('input', cargarLibros);
document.getElementById('filtroAutor')?.addEventListener('input', cargarLibros);
document.getElementById('filtroUsuario')?.addEventListener('input', cargarLibros);
document.getElementById('filtroGenero')?.addEventListener('change', cargarLibros);
document.getElementById('filtroEstado')?.addEventListener('change', cargarLibros);
document.getElementById('filtroCalificacion')?.addEventListener('change', cargarLibros);

document.getElementById('btnLimpiar')?.addEventListener('click', () => {
  document.getElementById('filtroTitulo').value = '';
  document.getElementById('filtroAutor').value = '';
  document.getElementById('filtroUsuario').value = '';
  document.getElementById('filtroGenero').value = '';
  document.getElementById('filtroEstado').value = '';
  document.getElementById('filtroCalificacion').value = '';
  cargarLibros();
});

document.getElementById('btnGenerarPDF')?.addEventListener('click', () => {
  const titulo = document.getElementById('filtroTitulo')?.value.trim() || '';
  const autor = document.getElementById('filtroAutor')?.value.trim() || '';
  const usuario = document.getElementById('filtroUsuario')?.value.trim() || '';
  const genero = document.getElementById('filtroGenero')?.value || '';
  const estado = document.getElementById('filtroEstado')?.value || '';
  const calificacionMin = document.getElementById('filtroCalificacion')?.value || '';

  const params = new URLSearchParams();
  if (titulo) params.append('titulo', titulo);
  if (autor) params.append('autor', autor);
  if (usuario) params.append('usuario', usuario);
  if (genero) params.append('genero', genero);
  if (estado) params.append('estado', estado);
  if (calificacionMin) params.append('calificacion_min', calificacionMin);

  const url = params.toString() ? `/libros/reporte/pdf?${params.toString()}` : '/libros/reporte/pdf';
  window.location.href = url;
});

window.addEventListener('load', cargarLibros);

