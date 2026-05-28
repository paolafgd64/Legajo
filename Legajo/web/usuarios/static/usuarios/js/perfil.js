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

function renderActividadPerfil(actividades) {
  const contenedor = document.querySelector('[data-profile-activity]');
  if (!contenedor) {
    return;
  }

  if (!Array.isArray(actividades) || actividades.length === 0) {
    contenedor.innerHTML = `
      <div class="perfil-empty-state">
        <i class="fa-solid fa-book-open"></i>
        <span>Aun no tienes actividad reciente.</span>
      </div>
    `;
    return;
  }

  contenedor.innerHTML = actividades.map((actividad) => `
    <div class="perfil-activity-row">
      <span><i class="fa-solid ${escapeHtml(actividad.icono || 'fa-book-open')}"></i></span>
      <div>
        <strong>${escapeHtml(actividad.titulo || 'Actividad')}</strong>
        <small>${escapeHtml(actividad.detalle || '')} · ${escapeHtml(actividad.tiempo || 'Reciente')}</small>
      </div>
    </div>
  `).join('');
}

async function actualizarEstadisticasPerfil() {
  const estadisticas = document.querySelectorAll('[data-profile-stat]');
  const actividad = document.querySelector('[data-profile-activity]');
  if (!estadisticas.length && !actividad) {
    return;
  }

  try {
    const response = await fetch('/api/perfil/estadisticas', {
      headers: {
        Accept: 'application/json'
      },
      cache: 'no-store'
    });

    if (!response.ok) {
      throw new Error('No se pudieron actualizar las estadisticas del perfil.');
    }

    const data = await response.json();
    estadisticas.forEach((element) => {
      const key = element.dataset.profileStat;
      if (Object.prototype.hasOwnProperty.call(data, key)) {
        element.textContent = data[key];
      }
    });
    renderActividadPerfil(data.actividadReciente);
  } catch (error) {
    console.error('Error actualizando estadisticas del perfil:', error);
  }
}

function validarEmailPerfil(correo) {
  if (typeof window.validarEmail === 'function') {
    return window.validarEmail(correo);
  }

  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(correo || '').trim());
}

function marcarCamposInvalidosPerfil(fields) {
  document.querySelectorAll('.perfil-modal-input.input-error').forEach((field) => {
    field.classList.remove('input-error');
  });
  fields.filter(Boolean).forEach((field) => field.classList.add('input-error'));
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
        const campos = {
          primerNombre: document.getElementById('swal-primerNombre'),
          primerApellido: document.getElementById('swal-primerApellido'),
          correo: document.getElementById('swal-correo'),
          telefono: document.getElementById('swal-telefono'),
          ciudad: document.getElementById('swal-ciudad'),
          direccion: document.getElementById('swal-direccion')
        };

        const payload = {
          primerNombre: campos.primerNombre.value.trim(),
          segundoNombre: document.getElementById('swal-segundoNombre').value.trim(),
          primerApellido: campos.primerApellido.value.trim(),
          segundoApellido: document.getElementById('swal-segundoApellido').value.trim(),
          correo: campos.correo.value.trim(),
          telefono: campos.telefono.value.trim(),
          ciudad: campos.ciudad.value.trim(),
          direccion: campos.direccion.value.trim()
        };

        marcarCamposInvalidosPerfil([]);

        if (!payload.primerNombre) {
          marcarCamposInvalidosPerfil([campos.primerNombre]);
          Swal.showValidationMessage('Ingresa tu primer nombre para continuar.');
          return false;
        }

        if (!payload.primerApellido) {
          marcarCamposInvalidosPerfil([campos.primerApellido]);
          Swal.showValidationMessage('Ingresa tu primer apellido para continuar.');
          return false;
        }

        if (!validarEmailPerfil(payload.correo)) {
          marcarCamposInvalidosPerfil([campos.correo]);
          Swal.showValidationMessage('Ingresa un correo electronico valido.');
          return false;
        }

        if (!payload.direccion || !payload.ciudad || !payload.telefono) {
          marcarCamposInvalidosPerfil([
            payload.direccion ? null : campos.direccion,
            payload.ciudad ? null : campos.ciudad,
            payload.telefono ? null : campos.telefono
          ]);
          Swal.showValidationMessage('Completa todos los campos obligatorios.');
          return false;
        }

        if (payload.ciudad.length > 20) {
          marcarCamposInvalidosPerfil([campos.ciudad]);
          Swal.showValidationMessage('La ciudad no debe superar 20 caracteres.');
          return false;
        }

        if (!/^\d+$/.test(payload.telefono)) {
          marcarCamposInvalidosPerfil([campos.telefono]);
          Swal.showValidationMessage('El telefono solo debe contener numeros.');
          return false;
        }

        if (payload.telefono.length < 10) {
          marcarCamposInvalidosPerfil([campos.telefono]);
          Swal.showValidationMessage('El telefono debe tener al menos 10 numeros.');
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

  actualizarEstadisticasPerfil();

  window.addEventListener('pageshow', actualizarEstadisticasPerfil);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      actualizarEstadisticasPerfil();
    }
  });
});

