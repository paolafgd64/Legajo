/* ==================
    BOTON DE TEMA
================== */

function actualizarTextoBotonTema(botones, esModoClaro) {
    botones.forEach((boton) => {
        boton.textContent = esModoClaro
            ? "\uD83C\uDF19 Modo Oscuro"
            : "\u2600\uFE0F Modo Claro";
    });
}

function configurarTema() {
    const botonesTema = document.querySelectorAll("#toggleModo, #modoToggle");
    const body = document.body;

    if (!body) {
        return;
    }

    const esModoClaro = localStorage.getItem("modo") === "claro";
    body.classList.toggle("modo-claro", esModoClaro);
    actualizarTextoBotonTema(botonesTema, esModoClaro);

    botonesTema.forEach((boton) => {
        boton.addEventListener("click", () => {
            const ahoraEsClaro = !body.classList.contains("modo-claro");
            body.classList.toggle("modo-claro", ahoraEsClaro);
            localStorage.setItem("modo", ahoraEsClaro ? "claro" : "oscuro");
            actualizarTextoBotonTema(botonesTema, ahoraEsClaro);
        });
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", configurarTema);
} else {
    configurarTema();
}


