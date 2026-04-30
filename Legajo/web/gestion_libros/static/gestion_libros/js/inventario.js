const legajoSwalClasses = {
  popup: 'legajo-swal-popup',
  title: 'legajo-swal-title',
  htmlContainer: 'legajo-swal-html',
  confirmButton: 'legajo-swal-confirm',
  denyButton: 'legajo-swal-deny',
  cancelButton: 'legajo-swal-cancel',
  input: 'legajo-swal-input'
};
const legajoSwalOptions = {
  buttonsStyling: false,
  customClass: legajoSwalClasses
};
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
      const estaPublicado = libro.estado === 'Publicado';
      item.className = 'item-inventario';
      item.dataset.libroId = libro.id;
      item.innerHTML = `
        <img src="${escapeHtml(libro.urlImagen || '/static/gestion_libros/imgs/libropredeterminado1.png')}" alt="Libro">
        <h3>${escapeHtml(libro.titulo)}</h3>
        <h4>${escapeHtml(libro.autor)}</h4>
        <p class="stock-libro"><strong>Stock:</strong> ${escapeHtml(String(libro.stock || 1))}</p>
        <p class="descripcion">${escapeHtml(libro.sinopsis)}</p>
        <div class="estado-libro-control">
          <span class="estado-libro-texto">${escapeHtml(libro.estado || 'Publicado')}</span>
          <label class="switch-estado-libro" title="Cambiar estado del libro">
            <input class="js-estado-libro" type="checkbox" ${estaPublicado ? 'checked' : ''} aria-label="Cambiar estado entre Leyendo y Publicado">
            <span class="switch-estado-slider"></span>
          </label>
        </div>
        <button class="btn-verde" onclick="verLibro(${libro.id})"><i class="fas fa-eye"></i> Ver</button>
        <button class="btn-amarillo" onclick="editarLibro(${libro.id})"><i class="fas fa-pen"></i> Editar</button>
        <button class="btn-rojo" onclick="eliminarLibro(${libro.id})"><i class="fas fa-trash"></i> Eliminar</button>
      `;
      grid.appendChild(item);

      const estadoSwitch = item.querySelector('.js-estado-libro');
      if (estadoSwitch) {
        estadoSwitch.addEventListener('change', () => {
          const nuevoEstado = estadoSwitch.checked ? 'Publicado' : 'Leyendo';
          actualizarEstadoLibro(libro, nuevoEstado, item, estadoSwitch);
        });
      }
    });
  } catch (error) {
    console.error('Error cargando inventario:', error);
    grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px;">Error cargando tu inventario.</p>';
  }
}

async function actualizarEstadoLibro(libro, nuevoEstado, item, estadoSwitch) {
  const estadoAnterior = libro.estado || 'Publicado';
  const estadoTexto = item.querySelector('.estado-libro-texto');
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

  estadoSwitch.disabled = true;
  if (estadoTexto) estadoTexto.textContent = nuevoEstado;

  try {
    const payload = {
      titulo: libro.titulo || '',
      autor: libro.autor || '',
      sinopsis: libro.sinopsis || '',
      genero: libro.genero || '',
      estado: nuevoEstado,
      url_imagen: libro.urlImagen || libro.url_imagen || ''
    };

    const res = await fetch(`${API}/${libro.id}`, {
      method: 'PUT',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || 'No se pudo actualizar el estado del libro');
    }

    libro.estado = data.estado || nuevoEstado;
    if (estadoTexto) estadoTexto.textContent = libro.estado;
    estadoSwitch.checked = libro.estado === 'Publicado';
  } catch (error) {
    console.error('Error actualizando estado del libro:', error);
    libro.estado = estadoAnterior;
    estadoSwitch.checked = estadoAnterior === 'Publicado';
    if (estadoTexto) estadoTexto.textContent = estadoAnterior;
    Swal.fire({
      icon: 'error',
      title: 'No se pudo cambiar el estado',
      text: error.message || 'Intenta de nuevo.'
    });
  } finally {
    estadoSwitch.disabled = false;
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

    if (modalImg) modalImg.src = libro.urlImagen || '/static/gestion_libros/imgs/libropredeterminado1.png';
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

