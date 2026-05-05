/**
 * calificaciones.js
 * Sistema de calificaciÃ³n de libros (1-5 estrellas)
 * Solo se puede calificar libros propios en el inventario
 */

// Generar estrellas para mostrar calificaciÃ³n (funciÃ³n compartida)
function generarEstrellasDisplay(calificacion) {
    let html = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= calificacion) {
            html += '<span style="color:#ffc107;">â˜…</span>';
        } else {
            html += '<span style="color:#ddd;">â˜†</span>';
        }
    }
    return html + ` <span style="margin-left:5px; color:#666; font-size:0.9em;">${calificacion}/5</span>`;
}

// Variables globales
let idLibroActual = null;
let calificacionSeleccionada = 0;

/**
 * Abrir modal de calificaciÃ³n
 */
function abrirModalCalificacion(idLibro) {
    idLibroActual = idLibro;
    calificacionSeleccionada = 0;
    
    // Resetear estrellas
    document.querySelectorAll('.estrella').forEach(estrella => {
        estrella.classList.remove('activa');
    });
    
    // Mostrar modal
    const modal = document.getElementById('modalCalificacion');
    if (modal) {
        modal.style.display = 'flex';
    }
}

/**
 * Cerrar modal de calificaciÃ³n
 */
function cerrarModalCalificacion() {
    const modal = document.getElementById('modalCalificacion');
    if (modal) {
        modal.style.display = 'none';
    }
    idLibroActual = null;
    calificacionSeleccionada = 0;
}

/**
 * Seleccionar nÃºmero de estrellas
 */
function seleccionarEstrella(numero) {
    calificacionSeleccionada = numero;
    
    // Actualizar estrellas visuales
    document.querySelectorAll('.estrella').forEach((estrella, index) => {
        if (index < numero) {
            estrella.classList.add('activa');
        } else {
            estrella.classList.remove('activa');
        }
    });
}

/**
 * Efecto hover en las estrellas
 */
function previewEstrella(numero) {
    document.querySelectorAll('.estrella').forEach((estrella, index) => {
        if (index < numero) {
            estrella.classList.add('hover');
        } else {
            estrella.classList.remove('hover');
        }
    });
}

function limpiarPreviewEstrella() {
    document.querySelectorAll('.estrella').forEach((estrella, index) => {
        estrella.classList.remove('hover');
    });
    
    // Restaurar estrellas seleccionadas
    if (calificacionSeleccionada > 0) {
        document.querySelectorAll('.estrella').forEach((estrella, index) => {
            if (index < calificacionSeleccionada) {
                estrella.classList.add('activa');
            }
        });
    }
}

/**
 * Enviar calificaciÃ³n al backend
 */
async function enviarCalificacion() {
    if (calificacionSeleccionada === 0) {
        alert('Por favor selecciona una calificaciÃ³n');
        return;
    }

    const token = localStorage.getItem('jwtToken');
    if (!token) {
        alert('Debes iniciar sesiÃ³n para calificar');
        window.location.href = '/login.';
        return;
    }

    try {
        const respuesta = await fetch('/api/calificaciones', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                idLibro: idLibroActual,
                calificacion: calificacionSeleccionada
            })
        });

        if (respuesta.ok) {
            const data = await respuesta.json();
            console.log('âœ“ CalificaciÃ³n guardada:', data);
            
            // Cerrar modal
            cerrarModalCalificacion();
            
            // Actualizar la UI del libro
            actualizarVisualizacionLibro(idLibroActual);
            
            // Mostrar confirmaciÃ³n
            mostrarNotificacion('Â¡CalificaciÃ³n guardada exitosamente!', 'success');
        } else {
            const error = await respuesta.json();
            mostrarNotificacion(error.error || 'Error al guardar la calificaciÃ³n', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error de conexiÃ³n', 'error');
    }
}

/**
 * Obtener promedio de un libro
 */
async function obtenerPromedioLibro(idLibro) {
    try {
        const respuesta = await fetch(`/api/calificaciones/libros/${idLibro}/promedio`);
        if (respuesta.ok) {
            return await respuesta.json();
        }
        return { promedio: 0, cantidad: 0 };
    } catch (error) {
        console.error('Error al obtener promedio:', error);
        return { promedio: 0, cantidad: 0 };
    }
}

/**
 * Mostrar historial de calificaciones
 */
async function mostrarHistorialCalificaciones(idLibro) {
    try {
        const respuesta = await fetch(`/api/calificaciones/libros/${idLibro}/historial`);
        
        if (respuesta.ok) {
            const calificaciones = await respuesta.json();
            
            if (calificaciones.length === 0) {
                mostrarNotificacion('No hay calificaciones aÃºn', 'info');
                return;
            }

            // Crear HTML del historial
            let html = '<div class="historial-modal">';
            html += '<div class="historial-contenido">';
            html += '<button onclick="cerrarHistorial()" class="btn-cerrar">x</button>';
            html += '<h2>Historial de Calificaciones</h2>';
            html += '<div class="lista-calificaciones">';

            calificaciones.forEach(cal => {
                html += `
                    <div class="item-calificacion">
                        <div class="calificador-info">
                            <strong>${cal.nombreUsuarioCalificante}</strong>
                            <span class="fecha">${formatearFecha(cal.fechaCalificacion)}</span>
                        </div>
                        <div class="estrellas-display">
                            ${generarEstrellasDisplay(cal.calificacion)}
                        </div>
                    </div>
                `;
            });

            html += '</div>';
            html += '</div>';
            html += '</div>';

            // Inyectar en el DOM
            const container = document.createElement('div');
            container.innerHTML = html;
            container.id = 'historialModal';
            document.body.appendChild(container);

            // Estilos dinÃ¡micos
            agregarEstilosHistorial();
        }
    } catch (error) {
        console.error('Error al obtener historial:', error);
        mostrarNotificacion('Error al cargar el historial', 'error');
    }
}

/**
 * Cerrar historial modal
 */
function cerrarHistorial() {
    const modal = document.getElementById('historialModal');
    if (modal) {
        modal.remove();
    }
}

/**
 * Generar HTML de estrellas para display
 */
function generarEstrellasDisplay(calificacion) {
    let html = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= calificacion) {
            html += '<span class="estrella-display">â˜…</span>';
        } else {
            html += '<span class="estrella-display-vacia">â˜†</span>';
        }
    }
    return html + ` <span class="valor-calificacion">${calificacion}/5</span>`;
}

/**
 * Actualizar visualizaciÃ³n del libro despuÃ©s de calificar
 */
async function actualizarVisualizacionLibro(idLibro) {
    const promedio = await obtenerPromedioLibro(idLibro);
    
    // Actualizar elemento del libro en la pÃ¡gina
    const elementoLibro = document.querySelector(`[data-libro-id="${idLibro}"]`);
    if (elementoLibro) {
        const promedioElement = elementoLibro.querySelector('.promedio-calificacion');
        if (promedioElement) {
            promedioElement.innerHTML = generarEstrellasDisplay(Math.round(promedio.promedio)) + 
                                       ` <span class="cantidad-resenas">(${promedio.cantidad})</span>`;
        }
    }
}

/**
 * Mostrar notificaciÃ³n temporal
 */
function mostrarNotificacion(mensaje, tipo = 'info') {
    const notif = document.createElement('div');
    notif.className = `notificacion notificacion-${tipo}`;
    notif.textContent = mensaje;
    notif.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        z-index: 9999;
        animation: slideIn 0.3s ease-in-out;
        ${tipo === 'success' ? 'background: #4caf50; color: white;' : 
          tipo === 'error' ? 'background: #f44336; color: white;' : 
          'background: #2196F3; color: white;'}
    `;
    
    document.body.appendChild(notif);
    
    setTimeout(() => {
        notif.style.animation = 'slideOut 0.3s ease-in-out';
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

/**
 * Formatear fecha
 */
function formatearFecha(fecha) {
    const date = new Date(fecha);
    return date.toLocaleDateString('es-ES', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Agregar estilos dinÃ¡micos para el historial
 */
function agregarEstilosHistorial() {
    if (document.getElementById('estilosHistorial')) return;
    
    const style = document.createElement('style');
    style.id = 'estilosHistorial';
    style.textContent = `
        .historial-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        }
        
        .historial-contenido {
            background: white;
            border-radius: 10px;
            padding: 30px;
            max-width: 600px;
            max-height: 70vh;
            overflow-y: auto;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            position: relative;
        }
        
        .historial-contenido h2 {
            margin-top: 0;
            margin-bottom: 20px;
            color: #333;
        }
        
        .btn-cerrar {
            position: absolute;
            top: 10px;
            right: 10px;
            background: none;
            border: none;
            font-size: 28px;
            cursor: pointer;
            color: #999;
        }
        
        .btn-cerrar:hover {
            color: #333;
        }
        
        .lista-calificaciones {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .item-calificacion {
            border-bottom: 1px solid #eee;
            padding-bottom: 15px;
        }
        
        .item-calificacion:last-child {
            border-bottom: none;
        }
        
        .calificador-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .calificador-info strong {
            color: #333;
            font-size: 14px;
        }
        
        .fecha {
            color: #999;
            font-size: 12px;
        }
        
        .estrellas-display {
            color: #ffc107;
            font-size: 18px;
        }
        
        .estrella-display {
            color: #ffc107;
        }
        
        .estrella-display-vacia {
            color: #ddd;
        }
        
        .valor-calificacion {
            margin-left: 8px;
            color: #666;
            font-size: 14px;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    
    document.head.appendChild(style);
}

