// /js/editarLibro.js
// Maneja la edición de libros desde libros/editar.html
const API = '/api/libros';
const UPLOAD_API = '/api/upload/imagen';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('editarForm');
  const idInput = document.getElementById('idLibro');
  
  // Obtener el ID del libro desde los parámetros de la URL
  const params = new URLSearchParams(window.location.search);
  const libroId = params.get('id');
  
  if (!libroId) {
    Swal.fire({
      icon: "error",
      title: "ID faltante",
      text: "No se proporcionó un ID de libro."
    }).then(() => {
      window.location.href = '../inventario.html';
    });
    return;
  }
  
  // Cargar los datos del libro
  cargarLibro(libroId);
  
  // Manejar el envío del formulario
  form.onsubmit = async (e) => {
    e.preventDefault();
    const titulo = document.getElementById('titulo').value.trim();
    const autor = document.getElementById('autor').value.trim();
    const sinopsis = document.getElementById('sinopsis').value.trim();
    const genero = document.getElementById('genero').value.trim();
    const imagenInput = document.getElementById('imagen');
    const estado = document.getElementById('estadoActual')?.value || 'Publicado';
    
    // Mantener la imagen actual si no se proporciona una nueva
    let urlImagen = document.getElementById('urlImagenActual')?.value || '/imgs/default-book.jpg';
    
    // Si hay archivo de imagen, subirla al servidor
    if (imagenInput.files && imagenInput.files[0]) {
      const file = imagenInput.files[0];
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const uploadRes = await fetch(UPLOAD_API, {
          method: 'POST',
          body: formData
        });
        
        if (!uploadRes.ok) {
          throw new Error('Error al subir la imagen');
        }
        
        const uploadData = await uploadRes.json();
        urlImagen = uploadData.url;
      } catch (err) {
        console.error('Error subiendo imagen:', err);
        Swal.fire({
          icon: "warning",
          title: "Advertencia",
          text: "No se pudo subir la nueva imagen. Se mantendrá la actual."
        });
      }
    }
    
    await enviarActualizacion({ titulo, autor, sinopsis, genero, estado, urlImagen });
  };
  
  async function cargarLibro(id) {
    try {
      const res = await fetch(`${API}/${id}`);
      if (!res.ok) throw new Error('No se pudo cargar el libro');
      const libro = await res.json();
      
      document.getElementById('idLibro').value = libro.idLibro || id;
      document.getElementById('titulo').value = libro.titulo || '';
      document.getElementById('autor').value = libro.autor || '';
      document.getElementById('sinopsis').value = libro.sinopsis || '';
      document.getElementById('genero').value = libro.genero || '';
      
      // Guardar la URL actual de la imagen y el estado para mantenerlos si no se cambian
      const urlActualInput = document.createElement('input');
      urlActualInput.type = 'hidden';
      urlActualInput.id = 'urlImagenActual';
      urlActualInput.value = libro.urlImagen || '/imgs/default-book.jpg';
      form.appendChild(urlActualInput);
      
      const estadoActualInput = document.createElement('input');
      estadoActualInput.type = 'hidden';
      estadoActualInput.id = 'estadoActual';
      estadoActualInput.value = libro.estado || 'Publicado';
      form.appendChild(estadoActualInput);

    } catch (err) {
      console.error('Error:', err);
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "No se pudo cargar el libro: " + err.message
      }).then(() => {
        window.location.href = '../inventario.html';
      });
    }
  }
  
  async function enviarActualizacion(libro) {
    try {
      const token = localStorage.getItem('jwtToken');
      const headers = { 'Content-Type': 'application/json' };
      
      if (token) {
        headers['Authorization'] = 'Bearer ' + token;
      }
      
      const libroId = document.getElementById('idLibro').value;
      const res = await fetch(`${API}/${libroId}`, {
        method: 'PUT',
        headers: headers,
        body: JSON.stringify(libro)
      });
      
      if (!res.ok) {
        const error = await res.text();
        throw new Error('Error al actualizar libro: ' + error);
      }
      
      Swal.fire({
        icon: "success",
        title: "¡Actualizado!",
        text: "El libro ha sido actualizado con éxito.",
        confirmButtonText: "Aceptar"
      }).then(() => {
        window.location.href = '../inventario.html';
      });

    } catch (err) {
      console.error('Error:', err);
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "No se pudo actualizar el libro: " + err.message
      });
    }
  }
});
