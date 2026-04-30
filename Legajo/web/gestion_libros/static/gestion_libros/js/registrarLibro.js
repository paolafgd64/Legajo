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

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('registrarLibroForm');
  if (!form) return;
  const modoEdicion = document.getElementById('modoEdicion')?.value === 'true';
  const libroId = document.getElementById('libroId')?.value;
  const redirectAfterSave = document.getElementById('redirectAfterSave')?.value || '/inventario/';
  const currentImageUrl = document.getElementById('currentImageUrl')?.value || '';
  const imageInput = form.querySelector('#imagen');
  const portadaPreview = document.getElementById('portadaPreview');

  function updatePreviewState(src) {
    if (!portadaPreview) return;
    if (!src) {
      portadaPreview.removeAttribute('src');
      portadaPreview.style.display = 'none';
      return;
    }
    portadaPreview.src = src;
    portadaPreview.style.display = 'block';
  }

  function handleImagePreview() {
    if (!imageInput || !portadaPreview) return;
    const selectedFile = imageInput.files?.[0];

    if (!selectedFile) {
      updatePreviewState(currentImageUrl);
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      updatePreviewState(event.target?.result || '');
    };
    reader.readAsDataURL(selectedFile);
  }

  if (imageInput) {
    imageInput.addEventListener('change', handleImagePreview);
    handleImagePreview();
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const csrfToken = getCookie('csrftoken') || form.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    try {
      let res;

      if (modoEdicion && libroId) {
        const hasNewImage = Boolean(imageInput?.files?.[0]);

        if (hasNewImage) {
          const formData = new FormData();
          formData.append('titulo', form.querySelector('#titulo')?.value || '');
          formData.append('autor', form.querySelector('#autor')?.value || '');
          formData.append('sinopsis', form.querySelector('#sinopsis')?.value || '');
          formData.append('genero', form.querySelector('#genero')?.value || '');
          formData.append('estado', form.querySelector('#estado')?.value || 'Publicado');
          formData.append('url_imagen', currentImageUrl);
          formData.append('imagen', imageInput.files[0]);

          res = await fetch(`${API}/${libroId}`, {
            method: 'PUT',
            credentials: 'same-origin',
            headers: {
              'X-CSRFToken': csrfToken
            },
            body: formData
          });
        } else {
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
        }
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
      window.location.href = redirectAfterSave;
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

