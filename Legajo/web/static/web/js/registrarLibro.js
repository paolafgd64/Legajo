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

async function parseJsonResponseRegistrar(response) {
  const rawText = await response.text();
  try {
    return JSON.parse(rawText);
  } catch (error) {
    throw new Error('El servidor devolvio una pagina HTML en lugar de JSON.');
  }
}

async function getRedirectAfterSave(defaultRedirect) {
  try {
    const response = await fetch('/api/auth/me', {
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json'
      }
    });

    if (!response.ok) {
      return defaultRedirect;
    }

    const user = await response.json();
    return user?.rol === 'admin' ? '/inventario_admi/' : '/inventario/';
  } catch (error) {
    return defaultRedirect;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('registrarLibroForm');
  if (!form) return;
  const modoEdicion = document.getElementById('modoEdicion')?.value === 'true';
  const libroId = document.getElementById('libroId')?.value;
  const redirectAfterSave = document.getElementById('redirectAfterSave')?.value || '/inventario/';
  const currentImageUrl = document.getElementById('currentImageUrl')?.value || '';

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const csrfToken = getCookie('csrftoken') || form.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    try {
      let res;

      if (modoEdicion && libroId) {
        const payload = {
          titulo: form.querySelector('#titulo')?.value || '',
          autor: form.querySelector('#autor')?.value || '',
          sinopsis: form.querySelector('#sinopsis')?.value || '',
          genero: form.querySelector('#genero')?.value || '',
          estado: form.querySelector('#estado')?.value || 'Publicado',
          url_imagen: currentImageUrl
        };

        res = await fetch(`${API}/${libroId}`, {
          method: 'PUT',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify(payload)
        });
      } else {
        const formData = new FormData(form);
        res = await fetch(API, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRFToken': csrfToken
          },
          body: formData
        });
      }

      const data = await parseJsonResponseRegistrar(res);
      if (!res.ok) {
        throw new Error(data.message || (modoEdicion ? 'No se pudo actualizar el libro' : 'No se pudo registrar el libro'));
      }

      await Swal.fire({
        icon: 'success',
        title: modoEdicion ? 'Libro actualizado' : 'Libro registrado',
        text: modoEdicion ? 'El libro fue actualizado correctamente' : 'El libro fue guardado correctamente',
        confirmButtonText: 'Continuar'
      });

      form.reset();
      window.location.href = await getRedirectAfterSave(redirectAfterSave);
    } catch (err) {
      console.error('Error registrando libro:', err);
      Swal.fire({
        icon: 'error',
        title: modoEdicion ? 'Error al editar' : 'Error al registrar',
        text: err.message || (modoEdicion ? 'No se pudo actualizar el libro' : 'No se pudo registrar el libro')
      });
    }
  });
});
