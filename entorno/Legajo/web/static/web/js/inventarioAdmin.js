// /js/inventarioAdmin.js
// CRUD para inventario_admi.html (admin)
const API = '/api/libros';
const DEFAULT_BOOK_IMAGE = '/static/web/imgs/libro_de_la_selva.jpg';

document.addEventListener('DOMContentLoaded', cargarInventarioAdmin);

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function cargarInventarioAdmin() {
  const grid = document.querySelector('.grid-inventario-admin');
  if (!grid) return;

  grid.innerHTML = '';

  try {
    const res = await fetch(API);
    if (!res.ok) throw new Error('Error al cargar libros');

    const libros = await res.json();

    if (!libros.length) {
      grid.innerHTML = '<p>No hay libros en el inventario.</p>';
      return;
    }

    libros.forEach((libro) => {
      const item = document.createElement('div');
      const imagen = libro.urlImagen || libro.url_imagen || DEFAULT_BOOK_IMAGE;

      item.className = 'item-inventario-admin';
      item.innerHTML = `
        <img src="${escapeHtml(imagen)}" alt="${escapeHtml(libro.titulo || 'Libro')}" />
        <h3>${escapeHtml(libro.titulo || '')}</h3>
        <h4>${escapeHtml(libro.autor || '')}</h4>
        <p>Dueno: <strong>${escapeHtml(libro.usuario || '')}</strong></p>
        <p class="estado">Estado: ${escapeHtml(libro.estado || '')}</p>
        <div class="estrellas">★★★★★</div>
        <div class="acciones-admin">
          <button class="btn-azul" onclick="verLibroAdmin('${escapeHtml(libro.idLibro)}')"><i class="fas fa-eye"></i></button>
          <button class="btn-amarillo" onclick="editarLibroAdmin('${escapeHtml(libro.idLibro)}')"><i class="fas fa-pen"></i></button>
          <button class="btn-rojo" onclick="eliminarLibroAdmin('${escapeHtml(libro.idLibro)}')"><i class="fas fa-trash"></i></button>
        </div>
      `;

      grid.appendChild(item);
    });
  } catch (e) {
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: 'No se pudo cargar el inventario'
    });
  }
}

async function eliminarLibroAdmin(id) {
  const result = await Swal.fire({
    title: 'Eliminar libro?',
    text: 'Esta accion no se puede deshacer',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#d33',
    cancelButtonColor: '#3085d6',
    confirmButtonText: 'Si, eliminar',
    cancelButtonText: 'Cancelar'
  });

  if (!result.isConfirmed) return;

  const res = await fetch(`${API}/${id}`, { method: 'DELETE' });

  if (res.ok) {
    Swal.fire({
      icon: 'success',
      title: 'Eliminado',
      text: 'El libro ha sido eliminado correctamente',
      timer: 1500,
      showConfirmButton: false
    });
    cargarInventarioAdmin();
  } else {
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: 'No se pudo eliminar el libro'
    });
  }
}

function verLibroAdmin(id) {
  Swal.fire({
    icon: 'info',
    title: 'Ver libro',
    text: `ID: ${id}`
  });
}

function editarLibroAdmin(id) {
  Swal.fire({
    icon: 'warning',
    title: 'Editar libro',
    text: `ID: ${id}`
  });
}
