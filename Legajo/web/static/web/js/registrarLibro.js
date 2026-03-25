const API = '/api/libros';

function getCookie(name) {
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith(`${name}=`)) {
      return decodeURIComponent(trimmed.substring(name.length + 1));
    }
  }
  return '';
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('registrarLibroForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(form);
    const csrfToken = getCookie('csrftoken') || form.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    try {
      const res = await fetch(API, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': csrfToken
        },
        body: formData
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.message || 'No se pudo registrar el libro');
      }

      await Swal.fire({
        icon: 'success',
        title: 'Libro registrado',
        text: 'El libro fue guardado correctamente',
        confirmButtonText: 'Continuar'
      });

      form.reset();
      window.location.href = '/inventario/';
    } catch (err) {
      console.error('Error registrando libro:', err);
      Swal.fire({
        icon: 'error',
        title: 'Error al registrar',
        text: err.message || 'No se pudo registrar el libro'
      });
    }
  });
});
