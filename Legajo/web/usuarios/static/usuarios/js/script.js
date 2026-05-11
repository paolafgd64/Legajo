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

/* ==================
    CONTADOR DE NOTIFICACIONES
================== */

function obtenerEnlaceNotificaciones() {
    return Array.from(document.querySelectorAll(".nav-links a")).find((enlace) => {
        const href = enlace.getAttribute("href") || "";
        const texto = enlace.textContent || "";
        return href.includes("notificaciones") || texto.toLowerCase().includes("notificaciones");
    });
}

function asegurarBurbujaNotificaciones(enlace) {
    const item = enlace?.querySelector("li");
    if (!item) return null;

    item.classList.add("nav-notificaciones-item");

    let burbuja = item.querySelector(".nav-notificaciones-badge");
    if (!burbuja) {
        burbuja = document.createElement("span");
        burbuja.className = "nav-notificaciones-badge";
        burbuja.setAttribute("aria-label", "Notificaciones nuevas");
        item.appendChild(burbuja);
    }

    return burbuja;
}

function pintarContadorNotificaciones(cantidad) {
    const enlace = obtenerEnlaceNotificaciones();
    const burbuja = asegurarBurbujaNotificaciones(enlace);
    if (!burbuja) return;

    if (!cantidad) {
        burbuja.textContent = "";
        burbuja.classList.remove("visible");
        return;
    }

    burbuja.textContent = cantidad > 99 ? "99+" : String(cantidad);
    burbuja.classList.add("visible");
}

async function actualizarContadorNotificaciones() {
    const enlace = obtenerEnlaceNotificaciones();
    if (!enlace) return;

    try {
        const respuesta = await fetch("/api/notificaciones", {
            headers: { Accept: "application/json" },
            credentials: "same-origin"
        });

        if (respuesta.status === 401 || !respuesta.ok) {
            pintarContadorNotificaciones(0);
            return;
        }

        const notificaciones = await respuesta.json();
        const nuevas = Array.isArray(notificaciones)
            ? notificaciones.filter((notificacion) => notificacion.esNueva).length
            : 0;

        pintarContadorNotificaciones(nuevas);
    } catch (error) {
        pintarContadorNotificaciones(0);
    }
}

function configurarContadorNotificaciones() {
    if (!obtenerEnlaceNotificaciones()) return;

    actualizarContadorNotificaciones();
    window.setInterval(actualizarContadorNotificaciones, 60000);
    window.actualizarContadorNotificaciones = actualizarContadorNotificaciones;
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", configurarContadorNotificaciones);
} else {
    configurarContadorNotificaciones();
}

