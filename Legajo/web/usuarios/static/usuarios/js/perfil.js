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

const ciudadesPerfil = [
  'Bogota',
  'Medellin',
  'Cali',
  'Barranquilla',
  'Bucaramanga',
  'Cartagena',
  'Manizales',
  'Pereira',
  'Santa Marta',
  'Tunja',
  'Ibague',
  'Cucuta',
  'Villavicencio',
  'Pasto',
  'Armenia'
];

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value || '';
  return div.innerHTML;
}

function renderOpcionesCiudad(ciudadActual) {
  const ciudadLimpia = (ciudadActual || '').trim();
  const ciudades = ciudadesPerfil.includes(ciudadLimpia) || !ciudadLimpia
    ? ciudadesPerfil
    : [...ciudadesPerfil, ciudadLimpia];

  return [
    '<option value="">Selecciona una ciudad</option>',
    ...ciudades.map((ciudad) => {
      const selected = ciudad === ciudadLimpia ? ' selected' : '';
      return `<option value="${escapeHtml(ciudad)}"${selected}>${escapeHtml(ciudad)}</option>`;
    })
  ].join('');
}

async function editarInformacionPerfil() {
  try {
    const meResponse = await fetch('/api/me/', {
      headers: {
        Accept: 'application/json'
      }
    });

    const usuario = await meResponse.json();
    if (!meResponse.ok) {
      throw new Error(usuario.message || 'No se pudo cargar tu informacion');
    }

    const resultado = await Swal.fire({
      title: 'Editar informacion',
      width: 680,
      html: `
        <div class="perfil-modal-layout">
          <div class="perfil-modal-avatar">
            <img src="/static/usuarios/imgs/profile.png" alt="Perfil">
            <h3>${usuario.primerNombre || 'Usuario'} ${usuario.primerApellido || ''}</h3>
            <p>Actualiza tu informacion personal</p>
          </div>
          <div class="perfil-modal-form">
            <div class="perfil-modal-grid">
              <div class="perfil-modal-field">
                <label for="swal-primerNombre">Primer nombre</label>
                <input id="swal-primerNombre" class="perfil-modal-input" placeholder="Primer nombre" value="${usuario.primerNombre || ''}">
              </div>
              <div class="perfil-modal-field">
                <label for="swal-segundoNombre">Segundo nombre</label>
                <input id="swal-segundoNombre" class="perfil-modal-input" placeholder="Segundo nombre" value="${usuario.segundoNombre || ''}">
              </div>
              <div class="perfil-modal-field">
                <label for="swal-primerApellido">Primer apellido</label>
                <input id="swal-primerApellido" class="perfil-modal-input" placeholder="Primer apellido" value="${usuario.primerApellido || ''}">
              </div>
              <div class="perfil-modal-field">
                <label for="swal-segundoApellido">Segundo apellido</label>
                <input id="swal-segundoApellido" class="perfil-modal-input" placeholder="Segundo apellido" value="${usuario.segundoApellido || ''}">
              </div>
              <div class="perfil-modal-field perfil-modal-field-full">
                <label for="swal-correo">Correo</label>
                <input id="swal-correo" class="perfil-modal-input" placeholder="Correo" value="${usuario.email || ''}">
              </div>
              <div class="perfil-modal-field">
                <label for="swal-telefono">Telefono</label>
                <input id="swal-telefono" class="perfil-modal-input" placeholder="Telefono" value="${usuario.telefono || ''}">
              </div>
              <div class="perfil-modal-field">
                <label for="swal-ciudad">Ciudad</label>
                <select id="swal-ciudad" class="perfil-modal-input">
                  ${renderOpcionesCiudad(usuario.ciudad)}
                </select>
              </div>
              <div class="perfil-modal-field perfil-modal-field-full">
                <label for="swal-direccion">Direccion</label>
                <input id="swal-direccion" class="perfil-modal-input" placeholder="Direccion" value="${usuario.direccion || ''}">
              </div>
            </div>
          </div>
        </div>
      `,
      showCancelButton: true,
      confirmButtonText: 'Guardar cambios',
      cancelButtonText: 'Cancelar',
      focusConfirm: false,
      customClass: {
        popup: 'perfil-swal-popup',
        title: 'perfil-swal-title',
        htmlContainer: 'perfil-swal-html',
        confirmButton: 'perfil-swal-confirm',
        cancelButton: 'perfil-swal-cancel'
      },
      buttonsStyling: false,
      preConfirm: () => {
        const payload = {
          primerNombre: document.getElementById('swal-primerNombre').value.trim(),
          segundoNombre: document.getElementById('swal-segundoNombre').value.trim(),
          primerApellido: document.getElementById('swal-primerApellido').value.trim(),
          segundoApellido: document.getElementById('swal-segundoApellido').value.trim(),
          correo: document.getElementById('swal-correo').value.trim(),
          telefono: document.getElementById('swal-telefono').value.trim(),
          ciudad: document.getElementById('swal-ciudad').value.trim(),
          direccion: document.getElementById('swal-direccion').value.trim()
        };

        if (!payload.primerNombre || !payload.primerApellido || !payload.correo || !payload.telefono || !payload.ciudad || !payload.direccion) {
          Swal.showValidationMessage('Completa todos los campos obligatorios.');
          return false;
        }

        return payload;
      }
    });

    if (!resultado.isConfirmed) {
      return;
    }

    const csrfToken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    const updateResponse = await fetch('/api/me/', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(resultado.value)
    });

    const data = await updateResponse.json();
    if (!updateResponse.ok) {
      throw new Error(data.message || 'No se pudo actualizar la informacion');
    }

    await Swal.fire({
      icon: 'success',
      title: 'Perfil actualizado',
      text: 'Tus datos fueron actualizados correctamente.',
      confirmButtonText: 'Continuar'
    });

    window.location.reload();
  } catch (error) {
    console.error('Error actualizando perfil:', error);
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: error.message || 'No se pudo actualizar la informacion.'
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.js-editar-perfil').forEach((button) => {
    button.addEventListener('click', editarInformacionPerfil);
  });
});

