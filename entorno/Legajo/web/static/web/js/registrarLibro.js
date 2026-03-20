// /js/registrarLibro.js
// Maneja el registro de libros desde registrar_libro.html
const API = '/api/libros';
const UPLOAD_API = '/api/upload/imagen';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  if (!form) return;

  form.onsubmit = async (e) => {
    e.preventDefault();

    const titulo = document.getElementById('titulo').value.trim();
    const autor = document.getElementById('autor').value.trim();
    const sinopsis = document.getElementById('sinopsis').value.trim();
    const genero = document.getElementById('genero').value.trim();
    const imagenInput = document.getElementById('imagen');
    const estado = 'Publicado';

    // Imagen por defecto
    let urlImagen = '/imgs/default-book.jpg';

    // Subir imagen si existe
    if (imagenInput.files && imagenInput.files[0]) {
      const file = imagenInput.files[0];
      const formData = new FormData();
      formData.append('file', file);

      try {
        const uploadRes = await fetch(UPLOAD_API, {
          method: 'POST',
          body: formData
        });

        if (!uploadRes.ok) throw new Error('Error al subir la imagen');

        const uploadData = await uploadRes.json();
        urlImagen = uploadData.url;

      } catch (err) {
        console.error('Error subiendo imagen:', err);

        await Swal.fire({
          icon: 'warning',
          title: 'Advertencia',
          text: 'No se pudo subir la imagen, se usará una imagen por defecto'
        });
      }
    }

    await enviarLibro({ titulo, autor, sinopsis, genero, estado, urlImagen });
  };

  async function enviarLibro(libro) {
    try {
      const token = localStorage.getItem('jwtToken');
      const headers = { 'Content-Type': 'application/json' };

      if (token) {
        headers['Authorization'] = 'Bearer ' + token;
      }

      const res = await fetch(API, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(libro)
      });

      if (!res.ok) {
        const error = await res.text();
        throw new Error(error || 'Error desconocido');
      }

      await Swal.fire({
        icon: 'success',
        title: 'Libro registrado',
        text: 'El libro ha sido registrado exitosamente',
        confirmButtonText: 'Aceptar'
      });

      form.reset();
      window.location.href = 'inventario.html';

    } catch (err) {
      console.error('Error:', err);

      Swal.fire({
        icon: 'error',
        title: 'Error al registrar',
        text: err.message || 'No se pudo registrar el libro'
      });
    }
  }
});
