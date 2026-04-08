/* ==================
    BOTON DE TEMA
================== */

function actualizarTextoBotonTema(botones, esModoClaro) {
    botones.forEach((boton) => {
        boton.textContent = esModoClaro ? "🌙 Modo Oscuro" : "☀️ Modo Claro";
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

/* ========================
    GRAFICAS DEL ADMIN
======================== */

function obtenerDashboardAdminData() {
    const dataElement = document.getElementById("admin-dashboard-data");
    if (!dataElement) {
        return null;
    }

    try {
        return JSON.parse(dataElement.textContent);
    } catch (error) {
        console.error("No se pudo leer la data del dashboard admin:", error);
        return null;
    }
}

function crearGraficaAdmin(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const context = canvas.getContext("2d");
    new Chart(context, config);
}

function configurarEjesEnteros() {
    return {
        y: {
            beginAtZero: true,
            ticks: {
                precision: 0,
                stepSize: 1,
            },
        },
        x: {
            grid: { display: false },
        },
    };
}

function renderizarGraficasAdmin() {
    const dashboardData = obtenerDashboardAdminData();
    if (!dashboardData) {
        return;
    }

    crearGraficaAdmin("usersGrowthChart", {
        type: "bar",
        data: {
            labels: dashboardData.usuarios_por_mes.labels,
            datasets: [{
                label: "Usuarios nuevos",
                data: dashboardData.usuarios_por_mes.data,
                backgroundColor: "#d4a017",
                borderColor: "#9a7200",
                borderWidth: 1,
                borderRadius: 8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
            },
            scales: configurarEjesEnteros(),
        },
    });

    crearGraficaAdmin("reportsMonthlyChart", {
        type: "line",
        data: {
            labels: dashboardData.reportes_por_mes.labels,
            datasets: [{
                label: "Reportes creados",
                data: dashboardData.reportes_por_mes.data,
                borderColor: "#d64545",
                backgroundColor: "rgba(214, 69, 69, 0.16)",
                borderWidth: 2,
                fill: true,
                tension: 0.35,
                pointRadius: 4,
                pointBackgroundColor: "#d64545",
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
            },
            scales: configurarEjesEnteros(),
        },
    });

    crearGraficaAdmin("exchangeStatusChart", {
        type: "doughnut",
        data: {
            labels: dashboardData.intercambios_por_estado.labels,
            datasets: [{
                data: dashboardData.intercambios_por_estado.data,
                backgroundColor: ["#f0ad4e", "#5bc0de", "#d9534f", "#5cb85c"],
                borderColor: ["#d99635", "#3ca8c9", "#bf3d39", "#449d44"],
                borderWidth: 1,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: "bottom",
                },
            },
        },
    });

    crearGraficaAdmin("usersCityChart", {
        type: "bar",
        data: {
            labels: dashboardData.usuarios_por_ciudad.labels,
            datasets: [{
                label: "Usuarios activos",
                data: dashboardData.usuarios_por_ciudad.data,
                backgroundColor: "#4f7cff",
                borderColor: "#3158d3",
                borderWidth: 1,
                borderRadius: 8,
            }],
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        stepSize: 1,
                    },
                },
                y: {
                    grid: { display: false },
                },
            },
        },
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderizarGraficasAdmin);
} else {
    renderizarGraficasAdmin();
}
