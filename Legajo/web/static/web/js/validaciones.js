function validarEmail(correo) {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(String(correo || '').trim());
}

function verClave(idCampo, icono) {
  const campo = document.getElementById(idCampo);
  if (!campo || !icono) {
    return;
  }

  if (campo.type === 'password') {
    campo.type = 'text';
    icono.classList.remove('fa-eye');
    icono.classList.add('fa-eye-slash');
  } else {
    campo.type = 'password';
    icono.classList.remove('fa-eye-slash');
    icono.classList.add('fa-eye');
  }
}

function traducirMensajeValidacion(rawMessage) {
  if (!rawMessage) {
    return 'No se pudo completar la validacion.';
  }

  const replacements = {
    'This password is too short. It must contain at least 8 characters.': 'La contrasena debe tener al menos 8 caracteres.',
    'This password is too common.': 'La contrasena es demasiado comun. Elige una mas segura.',
    'This password is entirely numeric.': 'La contrasena no puede estar compuesta solo por numeros.',
    'The password is too similar to the first name.': 'La contrasena es demasiado parecida al primer nombre.',
    'The password is too similar to the last name.': 'La contrasena es demasiado parecida al apellido.',
    'The password is too similar to the username.': 'La contrasena es demasiado parecida a los datos del usuario.',
  };

  let normalized = String(rawMessage).trim();
  Object.entries(replacements).forEach(([source, target]) => {
    normalized = normalized.replaceAll(source, target);
  });

  return normalized;
}

function obtenerMensajesPassword(password, email) {
  const normalizedPassword = String(password || '');

  return [
    {
      key: 'length',
      text: 'Minimo 8 caracteres',
      valid: normalizedPassword.length >= 8,
    },
    {
      key: 'letters',
      text: 'Al menos una letra',
      valid: /[A-Za-z]/.test(normalizedPassword),
    },
    {
      key: 'numbers',
      text: 'Al menos un numero',
      valid: /\d/.test(normalizedPassword),
    },
    {
      key: 'not_numeric',
      text: 'No solo numeros',
      valid: normalizedPassword.length > 0 && !/^\d+$/.test(normalizedPassword),
    },
  ];
}

function renderPasswordChecklist(container, password, email) {
  if (!container) {
    return true;
  }

  const checks = obtenerMensajesPassword(password, email);
  container.innerHTML = checks.map((item) => `
    <div class="password-check${item.valid ? ' is-valid' : ''}" data-check="${item.key}">
      ${item.text}
    </div>
  `).join('');

  return checks.every((item) => item.valid);
}

function mostrarMensajeFormulario(container, message, type = 'error') {
  if (!container) {
    return;
  }

  const normalizedMessage = traducirMensajeValidacion(message);
  container.className = `form-status form-status--${type} is-visible`;

  if (Array.isArray(normalizedMessage)) {
    container.innerHTML = `<ul>${normalizedMessage.map((item) => `<li>${item}</li>`).join('')}</ul>`;
    return;
  }

  if (String(normalizedMessage).includes('\n')) {
    container.innerHTML = `<ul>${String(normalizedMessage).split('\n').filter(Boolean).map((item) => `<li>${item.trim()}</li>`).join('')}</ul>`;
    return;
  }

  container.textContent = normalizedMessage;
}

function limpiarMensajeFormulario(container) {
  if (!container) {
    return;
  }

  container.className = 'form-status';
  container.textContent = '';
}

function marcarCamposInvalidos(fields) {
  document.querySelectorAll('.input-error').forEach((field) => field.classList.remove('input-error'));
  fields.filter(Boolean).forEach((field) => field.classList.add('input-error'));
}

window.validarEmail = validarEmail;
window.verClave = verClave;
window.traducirMensajeValidacion = traducirMensajeValidacion;
window.renderPasswordChecklist = renderPasswordChecklist;
window.mostrarMensajeFormulario = mostrarMensajeFormulario;
window.limpiarMensajeFormulario = limpiarMensajeFormulario;
window.marcarCamposInvalidos = marcarCamposInvalidos;
