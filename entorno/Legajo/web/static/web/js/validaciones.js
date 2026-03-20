// Validación para Iniciar Sesión
document.addEventListener("DOMContentLoaded", () => {
    const formLogin = document.querySelector('form[action="dashboard_admin.html"]');
    if (formLogin) {
        formLogin.addEventListener("submit", function (e) {
            const email = formLogin.querySelector('input[type="email"]').value.trim();
            const password = formLogin.querySelector('input[type="password"]').value.trim();

            if (!validarEmail(email)) {
                alert("Por favor, ingresa un correo electrónico válido.");
                e.preventDefault();
                return;
            }

            if (password === "") {
                alert("Por favor, ingresa una contraseña.");
                e.preventDefault();
                return;
            }
        });
    }

    // Validación para Crear Cuenta
    const formRegistro = document.querySelector('form[action="dashboard_usuario.html"]');
    if (formRegistro) {
        formRegistro.addEventListener("submit", function (e) {
            const nombre = document.getElementById("textoInput").value.trim();
            const email = formRegistro.querySelector('input[type="email"]').value.trim();
            const password = formRegistro.querySelectorAll('input[type="password"]')[0].value;
            const confirmar = formRegistro.querySelectorAll('input[type="password"]')[1].value;

            if (nombre === "") {
                alert("Por favor, ingresa tu nombre completo.");
                e.preventDefault();
                return;
            }

            if (!validarEmail(email)) {
                alert("Por favor, ingresa un correo electrónico válido.");
                e.preventDefault();
                return;
            }

            if (password.length < 6) {
                alert("La contraseña debe tener al menos 6 caracteres.");
                e.preventDefault();
                return;
            }

            if (password !== confirmar) {
                alert("Las contraseñas no coinciden.");
                e.preventDefault();
                return;
            }
        });
    }
});

// Función para validar formato de email
function validarEmail(correo) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(correo);
}

//función del ojo
function verClave(idCampo, icono) {
    const campo = document.getElementById(idCampo);

    if (campo.type === "password") {
        campo.type = "text";
        icono.classList.remove("fa-eye");
        icono.classList.add("fa-eye-slash");
    } else {
        campo.type = "password";
        icono.classList.remove("fa-eye-slash");
        icono.classList.add("fa-eye");
    }
}
