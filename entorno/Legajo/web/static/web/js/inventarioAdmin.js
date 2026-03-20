// /js/inventarioAdmin.js
// CRUD para inventario_admi.html (admin)
const API = '/api/libros';

document.addEventListener('DOMContentLoaded', cargarInventarioAdmin);

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

    libros.forEach(libro => {
      const item = document.createElement('div');
      item.className = 'item-inventario-admin';
      item.innerHTML = `
        <img src="/imgs/libro_de_la_selva.jpg" />
        <h3>${libro.titulo || ''}</h3>
        <h4>${libro.autor || ''}</h4>
        <p>Dueño: <strong>${libro.usuario || ''}</strong></p>
        <p class="estado">Estado: ${libro.estado || ''}</p>
        <div class="estrellas">★★★★★</div>
        <div class="acciones-admin">
          <button class="btn-azul" onclick="verLibroAdmin('${libro.idLibro}')"><i class="fas fa-eye"></i></button>
          <button class="btn-amarillo" onclick="editarLibroAdmin('${libro.idLibro}')"><i class="fas fa-pen"></i></button>
          <button class="btn-rojo" onclick="eliminarLibroAdmin('${libro.idLibro}')"><i class="fas fa-trash"></i></button>
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
    title: '¿Eliminar libro?',
    text: 'Esta acción no se puede deshacer',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#d33',
    cancelButtonColor: '#3085d6',
    confirmButtonText: 'Sí, eliminar',
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
