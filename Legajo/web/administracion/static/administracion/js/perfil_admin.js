function getAdminContactCookie(name) {
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith(`${name}=`)) {
      return decodeURIComponent(trimmed.substring(name.length + 1));
    }
  }
  return '';
}

function setAdminContactMessage(message, type = 'error') {
  const container = document.getElementById('adminContactMensaje');
  if (!container) return;
  container.className = `admin-contact-message is-visible ${type}`;
  container.textContent = message;
}

function clearAdminContactMessage() {
  const container = document.getElementById('adminContactMensaje');
  if (!container) return;
  container.className = 'admin-contact-message';
  container.textContent = '';
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('adminContactForm');
  if (!form) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearAdminContactMessage();

    const payload = {
      whatsapp: document.getElementById('contactWhatsapp')?.value.trim() || '',
      telefono: document.getElementById('contactTelefono')?.value.trim() || '',
      correo: document.getElementById('contactCorreo')?.value.trim() || ''
    };

    try {
      const response = await fetch('/api/admin/contacto', {
        method: 'PUT',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getAdminContactCookie('csrftoken')
        },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'No se pudo guardar el contacto.');
      }
      setAdminContactMessage('Contacto del index actualizado correctamente.', 'success');
    } catch (error) {
      setAdminContactMessage(error.message || 'No se pudo guardar el contacto.');
    }
  });
});
