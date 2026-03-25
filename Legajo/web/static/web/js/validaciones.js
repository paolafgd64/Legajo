document.addEventListener('DOMContentLoaded', () => {
    const formLogin = document.getElementById('loginForm');
    if (formLogin) {
        formLogin.addEventListener('submit', (e) => {
            const email = document.getElementById('correo')?.value.trim() || '';
            const password = document.getElementById('clave')?.value.trim() || '';

            if (!validarEmail(email)) {
                alert('Por favor, ingresa un correo electronico valido.');
                e.preventDefault();
                return;
            }

            if (!password) {
                alert('Por favor, ingresa una contrasena.');
            }
        });
    }

    const formRegistro = document.getElementById('registroForm');
    if (formRegistro) {
        formRegistro.addEventListener('submit', (e) => {
            const primerNombre = document.getElementById('primerNombre')?.value.trim() || '';
            const email = document.getElementById('correo')?.value.trim() || '';
            const password = document.getElementById('clave')?.value || '';
            const confirmar = document.getElementById('confirmClave')?.value || '';

            if (!primerNombre) {
                alert('Por favor, ingresa tu primer nombre.');
                e.preventDefault();
                return;
            }

            if (!validarEmail(email)) {
                alert('Por favor, ingresa un correo electronico valido.');
                e.preventDefault();
                return;
            }

            if (password.length < 8) {
                alert('La contrasena debe tener al menos 8 caracteres.');
                e.preventDefault();
                return;
            }

            if (password !== confirmar) {
                alert('Las contrasenas no coinciden.');
                e.preventDefault();
            }
        });
    }
});

function validarEmail(correo) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(correo);
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
