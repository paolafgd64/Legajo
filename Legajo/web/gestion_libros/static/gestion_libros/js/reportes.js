const API = '/api/admin/libros/reporte';
const tablaBody = document.getElementById('tablaLibros');
const legajoSwalClasses = {
  popup: 'legajo-swal-popup',
  title: 'legajo-swal-title',
  htmlContainer: 'legajo-swal-html',
  confirmButton: 'legajo-swal-confirm',
  denyButton: 'legajo-swal-deny',
  cancelButton: 'legajo-swal-cancel',
  input: 'legajo-swal-input'
};

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

function getCsrfToken() {
  return getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

async function parseJsonResponse(response) {
  const rawText = await response.text();
  try {
    return JSON.parse(rawText);
  } catch (error) {
    throw new Error('El servidor devolvio una respuesta inesperada.');
  }
}

async function cargarLibros() {
  const titulo = document.getElementById('filtroTitulo')?.value.trim() || '';
  const autor = document.getElementById('filtroAutor')?.value.trim() || '';
  const usuario = document.getElementById('filtroUsuario')?.value.trim() || '';
  const genero = document.getElementById('filtroGenero')?.value || '';
  const estado = document.getElementById('filtroEstado')?.value || '';

  const params = new URLSearchParams();
  if (titulo) params.append('titulo', titulo);
  if (autor) params.append('autor', autor);
  if (usuario) params.append('usuario', usuario);
  if (genero) params.append('genero', genero);
  if (estado) params.append('estado', estado);

  const url = params.toString() ? `${API}?${params.toString()}` : API;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Error en peticion: ${res.status}`);
    const libros = await res.json();

    mostrarEnTabla(libros);
  } catch (err) {
    console.error(err);
    if (tablaBody) {
      tablaBody.innerHTML = '<tr><td colspan="6">Error cargando datos.</td></tr>';
    }
  }
}

function escapeHtml(valor) {
  return String(valor || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function mostrarEnTabla(libros) {
  if (!tablaBody) return;

  tablaBody.innerHTML = '';
  if (!libros || libros.length === 0) {
    tablaBody.innerHTML = '<tr><td colspan="6">No hay resultados</td></tr>';
    return;
  }

  libros.forEach((libro) => {
    const tr = document.createElement('tr');
    const estaActivo = Boolean(libro.activo);
    tr.innerHTML = `
      <td>${escapeHtml(libro.usuario || '')}</td>
      <td class="clickable" data-lib='${escapeHtml(JSON.stringify(libro))}'>${escapeHtml(libro.titulo || '')}</td>
      <td>${escapeHtml(libro.autor || '')}</td>
      <td>${escapeHtml(libro.genero || '')}</td>
      <td>${escapeHtml(libro.estado || '')}</td>
      <td>
        <button
          type="button"
          class="estado-libro-boton ${estaActivo ? 'activo' : 'inactivo'}"
          data-libro-id="${libro.id}"
          data-activo="${estaActivo ? 'true' : 'false'}"
          data-titulo="${escapeHtml(libro.titulo || 'este libro')}"
          title="${estaActivo ? 'Desactivar libro' : 'Activar libro'}"
        >
          ${estaActivo ? '<i class="fas fa-check-circle"></i> Activo' : '<i class="fas fa-ban"></i> Desactivado'}
        </button>
      </td>
    `;
    tablaBody.appendChild(tr);
  });

  document.querySelectorAll('.clickable').forEach((td) => {
    td.addEventListener('click', () => {
      const libro = JSON.parse(td.getAttribute('data-lib'));
      abrirModal(libro);
    });
  });

  document.querySelectorAll('.estado-libro-boton').forEach((button) => {
    button.addEventListener('click', () => manejarCambioActivoLibro(button));
  });
}

async function actualizarActivoLibro(libroId, payload) {
  const response = await fetch(`/api/admin/libros/${libroId}/estado`, {
    method: 'PATCH',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify(payload)
  });

  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.message || 'No se pudo actualizar el libro.');
  }
  return data;
}

async function manejarCambioActivoLibro(button) {
  const libroId = button.dataset.libroId;
  const estaActivo = button.dataset.activo === 'true';
  const titulo = button.dataset.titulo || 'este libro';

  if (!libroId) return;

  if (!estaActivo) {
    const result = window.Swal
      ? await Swal.fire({
          icon: 'question',
          title: 'Activar libro',
          text: `Quieres activar nuevamente "${titulo}"?`,
          showCancelButton: true,
          confirmButtonText: 'Si, activar',
          cancelButtonText: 'Cancelar',
          buttonsStyling: false,
          customClass: legajoSwalClasses
        })
      : { isConfirmed: window.confirm(`Quieres activar nuevamente "${titulo}"?`) };

    if (!result.isConfirmed) return;

    try {
      await actualizarActivoLibro(libroId, { activo: true });
      await cargarLibros();
      if (window.Swal) {
        await Swal.fire({
          icon: 'success',
          title: 'Libro activado',
          timer: 1600,
          showConfirmButton: false,
          customClass: legajoSwalClasses
        });
      }
    } catch (error) {
      mostrarErrorEstadoLibro(error);
    }
    return;
  }

  let motivo = '';
  if (window.Swal) {
    const result = await Swal.fire({
      icon: 'warning',
      title: 'Desactivar libro',
      html: `<p style="margin-bottom:12px;">Escribe el motivo por el que vas a desactivar <strong>${escapeHtml(titulo)}</strong>.</p>`,
      input: 'textarea',
      inputPlaceholder: 'Motivo de desactivacion...',
      inputAttributes: {
        'aria-label': 'Motivo de desactivacion'
      },
      showCancelButton: true,
      confirmButtonText: 'Desactivar',
      cancelButtonText: 'Cancelar',
      buttonsStyling: false,
      customClass: legajoSwalClasses,
      inputValidator: (value) => {
        if (!value || value.trim().length < 10) {
          return 'Escribe un motivo de al menos 10 caracteres.';
        }
        return null;
      }
    });

    if (!result.isConfirmed) return;
    motivo = result.value.trim();
  } else {
    const value = window.prompt(`Motivo para desactivar "${titulo}":`);
    if (value === null) return;
    motivo = value.trim();
    if (motivo.length < 10) {
      window.alert('Escribe un motivo de al menos 10 caracteres.');
      return;
    }
  }

  try {
    await actualizarActivoLibro(libroId, {
      activo: false,
      motivo
    });
    await cargarLibros();
    if (window.Swal) {
      await Swal.fire({
        icon: 'success',
        title: 'Libro desactivado',
        text: 'El motivo fue enviado al usuario en sus notificaciones.',
        confirmButtonText: 'Continuar',
        buttonsStyling: false,
        customClass: legajoSwalClasses
      });
    }
  } catch (error) {
    mostrarErrorEstadoLibro(error);
  }
}

function mostrarErrorEstadoLibro(error) {
  if (window.Swal) {
    Swal.fire({
      icon: 'error',
      title: 'No se pudo actualizar',
      text: error.message || 'No se pudo actualizar el libro.',
      confirmButtonText: 'Continuar',
      buttonsStyling: false,
      customClass: legajoSwalClasses
    });
  } else {
    window.alert(error.message || 'No se pudo actualizar el libro.');
  }
}

const modal = document.getElementById('modalLibro');
const cerrarModal = document.getElementById('cerrarModal');

function abrirModal(libro) {
  document.getElementById('modalImg').src = libro.urlImagen || libro.url_imagen || '';
  document.getElementById('modalTitulo').innerText = libro.titulo || '';
  document.getElementById('modalAutor').innerText = libro.autor || '';
  document.getElementById('modalGenero').innerText = libro.genero || '';
  document.getElementById('modalUsuario').innerText = libro.usuario || '';
  document.getElementById('modalEstado').innerText = libro.estado || '';
  document.getElementById('modalDescripcion').innerText = libro.sinopsis || libro.descripcion || '';
  if (modal) {
    modal.style.display = 'block';
  }
}

cerrarModal?.addEventListener('click', () => {
  if (modal) {
    modal.style.display = 'none';
  }
});

window.addEventListener('click', (event) => {
  if (event.target === modal) {
    modal.style.display = 'none';
  }
});

document.getElementById('filtroTitulo')?.addEventListener('input', cargarLibros);
document.getElementById('filtroAutor')?.addEventListener('input', cargarLibros);
document.getElementById('filtroUsuario')?.addEventListener('input', cargarLibros);
document.getElementById('filtroGenero')?.addEventListener('change', cargarLibros);
document.getElementById('filtroEstado')?.addEventListener('change', cargarLibros);

document.getElementById('btnLimpiar')?.addEventListener('click', () => {
  document.getElementById('filtroTitulo').value = '';
  document.getElementById('filtroAutor').value = '';
  document.getElementById('filtroUsuario').value = '';
  document.getElementById('filtroGenero').value = '';
  document.getElementById('filtroEstado').value = '';
  cargarLibros();
});

document.getElementById('btnGenerarPDF')?.addEventListener('click', () => {
  const titulo = document.getElementById('filtroTitulo')?.value.trim() || '';
  const autor = document.getElementById('filtroAutor')?.value.trim() || '';
  const usuario = document.getElementById('filtroUsuario')?.value.trim() || '';
  const genero = document.getElementById('filtroGenero')?.value || '';
  const estado = document.getElementById('filtroEstado')?.value || '';

  const params = new URLSearchParams();
  if (titulo) params.append('titulo', titulo);
  if (autor) params.append('autor', autor);
  if (usuario) params.append('usuario', usuario);
  if (genero) params.append('genero', genero);
  if (estado) params.append('estado', estado);

  const url = params.toString() ? `/libros/reporte/pdf?${params.toString()}` : '/libros/reporte/pdf';
  window.location.href = url;
});

window.addEventListener('load', cargarLibros);
