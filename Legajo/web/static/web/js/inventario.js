const API = '/api/libros';

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

async function obtenerUsuarioActual() {
  const res = await fetch('/api/auth/me', {
    headers: {
      'Accept': 'application/json'
    }
  });

  if (!res.ok) {
    window.location.href = '/login/';
    return null;
  }

  return await res.json();
}

async function cargarInventario() {
  const grid = document.querySelector('.grid-inventario');
  if (!grid) return;

  grid.innerHTML = '';

  try {
    const usuario = await obtenerUsuarioActual();
    if (!usuario) return;

    const nombrePanel = document.getElementById('n2');
    const nombrePerfil = document.getElementById('n3');
    if (nombrePanel) nombrePanel.textContent = usuario.primerNombre || 'Usuario';
    if (nombrePerfil) nombrePerfil.textContent = usuario.primerNombre || 'Usuario';

    const res = await fetch(API);
    if (!res.ok) throw new Error('No se pudo cargar el inventario');

    const libros = await res.json();
    if (!Array.isArray(libros) || libros.length === 0) {
      grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px;">No tienes libros en tu inventario.</p>';
      return;
    }

    libros.forEach((libro) => {
      const item = document.createElement('div');
      item.className = 'item-inventario';
      item.dataset.libroId = libro.id;
      item.innerHTML = `
        <img src="${escapeHtml(libro.urlImagen || '/static/web/imgs/libro_de_la_selva.jpg')}" alt="Libro">
        <h3>${escapeHtml(libro.titulo)}</h3>
        <h4>${escapeHtml(libro.autor)}</h4>
        <p class="descripcion">${escapeHtml(libro.sinopsis)}</p>
        <button class="btn-verde" onclick="verLibro(${libro.id})"><i class="fas fa-eye"></i> Ver</button>
        <button class="btn-amarillo" onclick="editarLibro(${libro.id})"><i class="fas fa-pen"></i> Editar</button>
        <button class="btn-rojo" onclick="eliminarLibro(${libro.id})"><i class="fas fa-trash"></i> Eliminar</button>
      `;
      grid.appendChild(item);
    });
  } catch (error) {
    console.error('Error cargando inventario:', error);
    grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px;">Error cargando tu inventario.</p>';
  }
}

async function editarLibro(id) {
  window.location.href = `/registrar_libro/${id}/`;
}

async function verLibro(id) {
  try {
    const res = await fetch(`${API}/${id}`);
    if (!res.ok) throw new Error('No se pudo cargar el libro');

    const libro = await res.json();
    const modal = document.getElementById('modal');
    const modalImg = document.getElementById('modalImg');
    const modalTitulo = document.getElementById('modalTitulo');
    const modalAutor = document.getElementById('modalAutor');
    const modalDescripcion = document.getElementById('modalDescripcion');

    if (modalImg) modalImg.src = libro.urlImagen || '/static/web/imgs/libro_de_la_selva.jpg';
    if (modalTitulo) modalTitulo.textContent = libro.titulo || '';
    if (modalAutor) modalAutor.textContent = libro.autor || '';
    if (modalDescripcion) modalDescripcion.textContent = libro.sinopsis || '';
    if (modal) modal.style.display = 'block';
  } catch (error) {
    console.error('Error cargando libro:', error);
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: 'No se pudo cargar el libro.'
    });
  }
}

async function eliminarLibro(id) {
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
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    const res = await fetch(`${API}/${id}`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': csrfToken
      }
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || 'No se pudo eliminar el libro');
    }

    await Swal.fire({
      icon: 'success',
      title: 'Eliminado',
      text: 'El libro ha sido eliminado correctamente',
      timer: 1800,
      showConfirmButton: false
    });

    cargarInventario();
  } catch (error) {
    console.error('Error eliminando libro:', error);
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: error.message || 'No se pudo eliminar el libro.'
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const closeModal = document.getElementById('closeModal');
  const modal = document.getElementById('modal');

  if (closeModal && modal) {
    closeModal.addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  window.addEventListener('click', (event) => {
    if (modal && event.target === modal) {
      modal.style.display = 'none';
    }
  });

  cargarInventario();
});
