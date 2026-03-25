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

if (document.getElementById("uR")) {
    fetch("/api/admin/dashboard/reported-users")
        .then((response) => {
            if (!response.ok) {
                throw new Error("Error al obtener datos de reportes");
            }
            return response.json();
        })
        .then((data) => {
            const uR = document.getElementById("uR").getContext("2d");
            new Chart(uR, {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Usuarios reportados (acumulados)",
                        data: data.data,
                        backgroundColor: "#3498db",
                        borderColor: "#2980b9",
                        borderWidth: 1,
                        borderRadius: 6,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { stepSize: 1 }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        })
        .catch((error) => {
            console.error("Error cargando datos de reportes:", error);
            const uR = document.getElementById("uR").getContext("2d");
            new Chart(uR, {
                type: "bar",
                data: {
                    labels: Array.from({ length: 30 }, (_, i) => i + 1),
                    datasets: [{
                        label: "Usuarios reportados (acumulados)",
                        data: Array(30).fill(0),
                        backgroundColor: "#3498db",
                        borderRadius: 6
                    }]
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true },
                        x: { grid: { display: false } }
                    }
                }
            });
        });
}

if (document.getElementById("iC")) {
    fetch("/api/admin/dashboard/completed-exchanges")
        .then((response) => {
            if (!response.ok) {
                throw new Error("Error al obtener datos de intercambios");
            }
            return response.json();
        })
        .then((data) => {
            const iC = document.getElementById("iC").getContext("2d");
            new Chart(iC, {
                type: "line",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Intercambios completados (acumulados)",
                        data: data.data,
                        backgroundColor: "rgba(46, 204, 113, 0.1)",
                        borderColor: "#2ecc71",
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: "#2ecc71",
                        pointBorderColor: "#27ae60"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { stepSize: 1 }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        })
        .catch((error) => {
            console.error("Error cargando datos de intercambios:", error);
            const iC = document.getElementById("iC").getContext("2d");
            new Chart(iC, {
                type: "line",
                data: {
                    labels: Array.from({ length: 30 }, (_, i) => i + 1),
                    datasets: [{
                        label: "Intercambios completados (acumulados)",
                        data: Array(30).fill(0),
                        backgroundColor: "rgba(46, 204, 113, 0.1)",
                        borderColor: "#2ecc71",
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true },
                        x: { grid: { display: false } }
                    }
                }
            });
        });
}
