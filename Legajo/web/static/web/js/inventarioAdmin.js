const API = '/api/libros';
const DEFAULT_BOOK_IMAGE = '/static/web/imgs/libro_de_la_selva.jpg';

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

function getCsrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function buildFilters() {
  const search = document.getElementById('buscarLibro')?.value.trim() || '';
  const genero = document.getElementById('filtroGenero')?.value.trim() || '';
  const estado = document.getElementById('filtroEstado')?.value.trim() || '';
  const params = new URLSearchParams();

  if (search) {
    params.set('q', search);
  }
  if (genero) {
    params.set('genero', genero);
  }
  if (estado) {
    params.set('estado', estado);
  }

  return params.toString();
}

async function cargarInventarioAdmin() {
  const grid = document.querySelector('.grid-inventario-admin');
  if (!grid) return;

  grid.innerHTML = '';

  try {
    const query = buildFilters();
    const res = await fetch(query ? `${API}?${query}` : API, {
      headers: {
        Accept: 'application/json'
      }
    });

    if (!res.ok) {
      throw new Error('No se pudo cargar el inventario.');
    }

    const libros = await res.json();
    if (!Array.isArray(libros) || libros.length === 0) {
      grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px;">No hay libros para mostrar.</p>';
      return;
    }

    libros.forEach((libro) => {
      const item = document.createElement('div');
      item.className = 'item-inventario-admin';
      item.dataset.libroId = libro.id;
      item.innerHTML = `
        <img src="${escapeHtml(libro.urlImagen || DEFAULT_BOOK_IMAGE)}" alt="Libro">
        <h3>${escapeHtml(libro.titulo)}</h3>
        <h4>${escapeHtml(libro.autor)}</h4>
        <p>Dueno: <strong>${escapeHtml(libro.usuario)}</strong></p>
        <p class="estado">Estado: ${escapeHtml(libro.estado)}</p>
        <p class="descripcion">${escapeHtml(libro.sinopsis)}</p>
        <div class="acciones-admin">
          <button class="btn-azul" onclick="verLibroAdmin(${libro.id})"><i class="fas fa-eye"></i></button>
          <button class="btn-amarillo" onclick="editarLibroAdmin(${libro.id})"><i class="fas fa-pen"></i></button>
          <button class="btn-rojo" onclick="eliminarLibroAdmin(${libro.id})"><i class="fas fa-trash"></i></button>
        </div>
      `;
      grid.appendChild(item);
    });
  } catch (error) {
    console.error('Error cargando inventario admin:', error);
    grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px;">Error cargando el inventario.</p>';
  }
}

function editarLibroAdmin(id) {
  window.location.href = `/registrar_libro/${id}/?source=admin`;
}

async function verLibroAdmin(id) {
  try {
    const res = await fetch(`${API}/${id}`, {
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json'
      }
    });
    if (!res.ok) {
      throw new Error('No se pudo cargar el libro.');
    }

    const libro = await res.json();
    await Swal.fire({
      title: libro.titulo || 'Libro',
      text: libro.sinopsis || '',
      imageUrl: libro.urlImagen || libro.url_imagen || DEFAULT_BOOK_IMAGE,
      imageAlt: libro.titulo || 'Portada del libro',
      footer: `${libro.autor || 'Autor desconocido'} | ${libro.estado || 'Sin estado'}`,
      confirmButtonText: 'Cerrar'
    });
  } catch (error) {
    console.error('Error cargando libro admin:', error);
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: error.message || 'No se pudo cargar el libro.'
    });
  }
}

async function eliminarLibroAdmin(id) {
  const result = await Swal.fire({
    title: 'Eliminar libro?',
    text: 'Esta accion no se puede deshacer.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Si, eliminar',
    cancelButtonText: 'Cancelar'
  });

  if (!result.isConfirmed) return;

  try {
    const res = await fetch(`${API}/${id}`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCsrfToken()
      }
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || 'No se pudo eliminar el libro.');
    }

    await Swal.fire({
      icon: 'success',
      title: 'Eliminado',
      text: 'El libro ha sido eliminado correctamente.',
      timer: 1800,
      showConfirmButton: false
    });

    cargarInventarioAdmin();
  } catch (error) {
    console.error('Error eliminando libro admin:', error);
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: error.message || 'No se pudo eliminar el libro.'
    });
  }
}

function bindFilters() {
  const controls = [
    document.getElementById('buscarLibro'),
    document.getElementById('filtroGenero'),
    document.getElementById('filtroEstado'),
  ].filter(Boolean);

  let debounceTimer = null;
  const reload = () => {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => {
      cargarInventarioAdmin();
    }, 250);
  };

  controls.forEach((control) => {
    control.addEventListener('input', reload);
    control.addEventListener('change', reload);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  bindFilters();
  cargarInventarioAdmin();
});
