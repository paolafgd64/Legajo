// /js/inventario.js
// CRUD para inventario.html (usuario)
const API = '/api/libros';

// Generar estrellas para mostrar calificación
function generarEstrellasDisplay(calificacion) {
    let html = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= calificacion) {
            html += '<span style="color:#ffc107;">★</span>';
        } else {
            html += '<span style="color:#ddd;">☆</span>';
        }
    }
    return html + ` <span style="margin-left:5px; color:#666; font-size:0.9em;">${calificacion}/5</span>`;
}

// Obtener usuario actual y cargar su inventario
async function obtenerUsuarioActual() {
  try {
    const token = localStorage.getItem('jwtToken');
    if (!token) {
      window.location.href = '/login.html';
      return null;
    }
    const res = await fetch('/api/auth/me', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) {
      localStorage.removeItem('jwtToken');
      window.location.href = '/login.html';
      return null;
    }
    return await res.json();
  } catch (e) {
    console.error('Error obteniendo usuario actual:', e);
    return null;
  }
}

async function cargarInventario() {
  const grid = document.querySelector('.grid-inventario');
  if (!grid) return;
  grid.innerHTML = '';
  
  try {
    // Obtener usuario actual
    const usuario = await obtenerUsuarioActual();
    if (!usuario) return;
    
    // Cargar todos los libros
    const res = await fetch(API);
    if (!res.ok) throw new Error('Error al cargar libros');
    const libros = await res.json();
    
    // Filtrar solo los libros que pertenecen al usuario actual
    const misLibros = libros.filter(l => l.usuarioPropietarioId === usuario.idUsuario);
    
    if (!misLibros.length) {
      grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px;">No tienes libros en tu inventario.</p>';
      return;
    }
    
    misLibros.forEach(libro => {
      const item = document.createElement('div');
      item.className = 'item-inventario';
      const libroId = libro.idLibro || libro.id || '';
      item.setAttribute('data-libro-id', libroId);
      console.log('📚 Creando item para libro:', libro.titulo, 'ID:', libroId);
      

      item.innerHTML = `
        <img src="${libro.urlImagen || '/imgs/libro_de_la_selva.jpg'}" alt="Libro">
        <h3>${libro.titulo || ''}</h3>
        <h4>${libro.autor || ''}</h4>
        <div class="estrellas" data-libro-id="${libroId}"></div>
        <div class="promedio-calificacion"></div>
        <p class="descripcion">${libro.sinopsis || ''}</p>
        <button class="btn-verde" onclick="verLibro('${libroId}')"><i class="fas fa-eye"></i> Ver</button>
        <button class="btn-amarillo" onclick="editarLibro('${libroId}')"><i class="fas fa-edit"></i> Editar</button>
        <button class="btn-azul" onclick="abrirModalCalificacion(${libroId})"><i class="fas fa-star"></i> Calificar</button>
        <button class="btn-rojo" onclick="eliminarLibro('${libroId}')"><i class="fas fa-trash"></i> Eliminar</button>
      `;

      grid.appendChild(item);
      
      // Cargar promedio de calificación después de crear el elemento
      console.log('⏳ Llamando cargarPromedioCalificacion para:', libroId);
      cargarPromedioCalificacion(libroId);
    });

  } catch (e) {
    console.error('Error cargando inventario:', e);
    grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px;">Error cargando tu inventario.</p>';
  }
}

async function eliminarLibro(id) {

  // 🔥 Reemplazo confirm() por SweetAlert2
  const result = await Swal.fire({
    title: "¿Eliminar libro?",
    text: "Esta acción no se puede deshacer.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Sí, eliminar",
    cancelButtonText: "Cancelar"
  });

  if (!result.isConfirmed) return;

  const token = localStorage.getItem('jwtToken');
  const headers = {};

  if (token) {
    headers['Authorization'] = 'Bearer ' + token;
  }

  const res = await fetch(`${API}/${id}`, { 
    method: 'DELETE',
    headers: headers
  });

  if (res.ok) {
    Swal.fire({
      icon: "success",
      title: "Eliminado",
      text: "El libro ha sido eliminado correctamente",
      timer: 1800,
      showConfirmButton: false
    });
    cargarInventario();
  } else {
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo eliminar el libro."
    });
  }
}

// Modal para mostrar detalles del libro
const modal = document.getElementById('modal');
const closeModal = document.getElementById('closeModal');

if (closeModal) {
  closeModal.addEventListener('click', () => {
    if (modal) modal.style.display = 'none';
  });
}

window.addEventListener('click', (event) => {
  if (modal && event.target === modal) {
    modal.style.display = 'none';
  }
});

async function verLibro(id) {
  try {
    console.log('👁️ Ver libro ID:', id);
    const res = await fetch(`${API}/${id}`);
    if (!res.ok) throw new Error('Error al cargar libro');

    const libro = await res.json();
    console.log('📖 Libro cargado:', libro);
    
    // Rellenar modal con datos del libro
    const modalImg = document.getElementById('modalImg');
    const modalTitulo = document.getElementById('modalTitulo');
    const modalAutor = document.getElementById('modalAutor');
    const modalDescripcion = document.getElementById('modalDescripcion');
    
    if (modalImg) modalImg.src = libro.urlImagen || '/imgs/default-book.jpg';
    if (modalTitulo) modalTitulo.textContent = libro.titulo || '';
    if (modalAutor) modalAutor.textContent = libro.autor || '';
    if (modalDescripcion) modalDescripcion.textContent = libro.sinopsis || '';
    
    // Mostrar modal
    const modal = document.getElementById('modal');
    if (modal) {
      modal.style.display = 'block';
      console.log('✅ Modal mostrado');
    } else {
      console.error('❌ Modal no encontrado');
    }

  } catch (e) {
    console.error('Error:', e);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo cargar el libro."
    });
  }
}

function editarLibro(id) {
  window.location.href = `/libros/editar.html?id=${id}`;
}

// Función para cargar el promedio de calificación de un libro
async function cargarPromedioCalificacion(idLibro) {
  try {
    console.log('🔵 Cargando promedio para libro:', idLibro);
    
    const token = localStorage.getItem('jwtToken');
    const headers = {};
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    
    const res = await fetch(`/api/calificaciones/libros/${idLibro}/promedio`, {
      headers: headers
    });
    console.log('Respuesta status:', res.status);
    
    if (res.ok) {
      const data = await res.json();
      console.log('Datos recibidos:', data);
      
      const elemento = document.querySelector(`[data-libro-id="${idLibro}"] .estrellas`);
      console.log('Elemento encontrado:', elemento ? 'SÍ' : 'NO');
      
      if (elemento) {
        if (data.cantidad > 0) {
          const html = generarEstrellasDisplay(Math.round(data.promedio)) + 
                       ` <span class="cantidad-resenas" style="font-size:0.8em; color:#999;">(${data.cantidad})</span>`;
          elemento.innerHTML = html;
          console.log('✅ Estrellas insertadas:', html);
        } else {
          elemento.innerHTML = '☆☆☆☆☆ <span style="font-size:0.8em; color:#999;">(sin calificaciones)</span>';
          console.log('📭 Sin calificaciones aún');
        }
      } else {
        console.error('❌ No se encontró elemento .estrellas para libro', idLibro);
      }
    } else {
      console.error('Error en respuesta:', res.status, res.statusText);
    }
  } catch (error) {
    console.error('❌ Error cargando promedio:', error);
  }
}

document.addEventListener('DOMContentLoaded', cargarInventario);
