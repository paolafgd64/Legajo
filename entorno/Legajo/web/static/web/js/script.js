/* ==================
    BOTON DE TEMA
================== */

const toggle = document.getElementById("toggleModo");
const body = document.body;

// Verificar si ya hay un modo guardado
if (localStorage.getItem("modo") === "claro") {
    body.classList.add("modo-claro");
    if (toggle) toggle.textContent = "🌙 Modo Oscuro";
}

if (toggle) {
    toggle.addEventListener("click", () => {
        body.classList.toggle("modo-claro");
        const esClaro = body.classList.contains("modo-claro");
        toggle.textContent = esClaro ? "🌙 Modo Oscuro" : "☀️ Modo Claro";
        localStorage.setItem("modo", esClaro ? "claro" : "oscuro");
    });
}

/* ========================
    GRAFICAS DEL ADMIN
======================== */

if (document.getElementById('uR')) {
    // Cargar datos de usuarios reportados desde el backend
    fetch('/api/admin/dashboard/reported-users')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al obtener datos de reportes');
            }
            return response.json();
        })
        .then(data => {
            const uR = document.getElementById('uR').getContext('2d');
            new Chart(uR, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Usuarios reportados (acumulados)',
                        data: data.data,
                        backgroundColor: '#3498db',
                        borderColor: '#2980b9',
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
        .catch(error => {
            console.error('Error cargando datos de reportes:', error);
            // Mostrar gráfica con datos de ejemplo en caso de error
            const uR = document.getElementById('uR').getContext('2d');
            new Chart(uR, {
                type: 'bar',
                data: {
                    labels: Array.from({length: 30}, (_, i) => i + 1),
                    datasets: [{
                        label: 'Usuarios reportados (acumulados)',
                        data: Array(30).fill(0),
                        backgroundColor: '#3498db',
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

if (document.getElementById('iC')) {
    // Cargar datos de intercambios completados desde el backend
    fetch('/api/admin/dashboard/completed-exchanges')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al obtener datos de intercambios');
            }
            return response.json();
        })
        .then(data => {
            const iC = document.getElementById('iC').getContext('2d');
            new Chart(iC, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Intercambios completados (acumulados)',
                        data: data.data,
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        borderColor: '#2ecc71',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: '#2ecc71',
                        pointBorderColor: '#27ae60'
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
        .catch(error => {
            console.error('Error cargando datos de intercambios:', error);
            // Mostrar gráfica con datos de ejemplo en caso de error
            const iC = document.getElementById('iC').getContext('2d');
            new Chart(iC, {
                type: 'line',
                data: {
                    labels: Array.from({length: 30}, (_, i) => i + 1),
                    datasets: [{
                        label: 'Intercambios completados (acumulados)',
                        data: Array(30).fill(0),
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        borderColor: '#2ecc71',
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
