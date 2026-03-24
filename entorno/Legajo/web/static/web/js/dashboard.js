// dashboard.js - Carga dinámica de libros para el dashboard

let usuarioActualId = null;
let todosLosLibros = [];

// Obtener el ID del usuario autenticado
async function obtenerUsuarioActual() {
    try {
        const token = localStorage.getItem('jwtToken');
        if (!token) return null;
        
        const resp = await fetch('/api/auth/me', {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Accept': 'application/json'
            }
        });
        
        if (!resp.ok) return null;
        const user = await resp.json();
        return user.idUsuario || user.id;
    } catch (e) {
        console.error('Error obteniendo usuario actual:', e);
        return null;
    }
}

// Cargar todos los libros de la API
async function cargarTodosLosLibros() {
    try {
        const resp = await fetch('/api/libros');
        if (!resp.ok) throw new Error('Error al cargar libros');
        const libros = await resp.json();
        console.debug('📚 LIBROS CARGADOS DEL API:', libros);
        if (libros && libros.length > 0) {
            console.debug('Primer libro estructura:', libros[0]);
        }
        return libros || [];
    } catch (e) {
        console.error('Error cargando libros:', e);
        return [];
    }
}

// Filtrar libros que NO sean del usuario actual
function filtrarLibrosOtrosUsuarios(libros, usuarioId) {
    if (!usuarioId) {
        console.debug('Sin usuarioId, mostrando todos los libros');
        return libros;
    }
    
    console.debug('=== FILTRADO DE LIBROS ===');
    console.debug('usuarioId actual:', usuarioId);
    console.debug('Total de libros:', libros.length);
    
    // Filtrar: solo mostrar libros que NO sean del usuario actual
    const resultado = libros.filter(libro => {
        // Intentar obtener el ID del propietario de diferentes formas
        const propietarioId = libro.usuarioPropietarioId || libro.propietarioId;
        const esDelUsuario = propietarioId === usuarioId;
        
        console.debug(`Libro: "${libro.titulo}", propietarioId:${propietarioId}, esDelUsuario:${esDelUsuario}`);
        
        return propietarioId !== usuarioId && propietarioId > 0; // Solo mostrar si es diferente Y tiene ID válido
    });
    
    console.debug('Libros que se mostrarán:', resultado.length);
    return resultado;
}

// Crear elementos dinámicos de libros
function crearElementoLibro(libro) {
    const div = document.createElement('div');
    div.className = 'libro';
    div.dataset.id = libro.idLibro || libro.id || '';
    div.dataset.titulo = libro.titulo || '';
    div.dataset.autor = libro.autor || '';
    div.dataset.descripcion = libro.descripcion || libro.sinopsis || 'Sin descripción disponible';
    div.dataset.imagen = libro.urlImagen ||  '/static/web/imgs/libro_de_la_selva.jpg';
    div.dataset.usuario = libro.usuario || 
        (libro.usuarioPropietario ? libro.usuarioPropietario.nombre : 'Propietario desconocido');
    div.dataset.usuarioId = libro.usuarioPropietarioId || 
        (libro.usuarioPropietario && (libro.usuarioPropietario.idUsuario || libro.usuarioPropietario.id)) || '';
    
    div.innerHTML = `
        <img src="${libro.urlImagen || '/static/web/imgs/libro_de_la_selva.jpg'}" alt="${libro.titulo || 'Libro'}">
        <h3>${libro.titulo || 'Sin título'}</h3>
        <p>${libro.autor || 'Autor desconocido'}</p>
        <div class="estrellas-display" data-libro-id="${libro.idLibro || libro.id}">⭐⭐⭐⭐⭐</div>
        <button class="ver-libro"><i class="fa fa-eye"></i> Ver</button>
    `;
    
    return div;
}

// Inicializar dashboard
async function inicializarDashboard() {
    try {
        usuarioActualId = await obtenerUsuarioActual();
        todosLosLibros = await cargarTodosLosLibros();

        const librosOtros = filtrarLibrosOtrosUsuarios(todosLosLibros, usuarioActualId);

        if (librosOtros.length === 0) {
            Swal.fire({
                icon: 'info',
                title: 'Sin libros disponibles',
                text: 'No hay libros disponibles de otros usuarios por ahora.'
            });
            return;
        }

        const carruselRecomendados = document.getElementById('recomendados');
        const carruselGeneros = document.getElementById('generos');

        if (carruselRecomendados) {
            carruselRecomendados.innerHTML = '';
            librosOtros.slice(0, 6).forEach(l => carruselRecomendados.appendChild(crearElementoLibro(l)));
        }

        if (carruselGeneros) {
            carruselGeneros.innerHTML = '';
            librosOtros.slice(6, 12).forEach(l => carruselGeneros.appendChild(crearElementoLibro(l)));
        }

        attachVerLibroListeners();
        
        // Cargar calificaciones de todos los libros
        librosOtros.forEach(libro => {
            cargarPromedioLibroDashboard(libro.idLibro || libro.id);
        });
        
    } catch (e) {
        console.error('Error inicializando dashboard:', e);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Ocurrió un problema cargando el dashboard.'
        });
    }
}

// Generar estrellas para mostrar calificación
function generarEstrellasDisplay(calificacion) {
    let html = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= calificacion) {
            html += '<span style="color:#ffc107;">★</span>';
        } else {
            html += '<span style="color:#ddd;">☆</span>';
        }
    }
    return html + ` <span style="margin-left:5px; color:#666; font-size:0.9em;">${calificacion}/5</span>`;
}

// Cargar promedio de calificación en dashboard
async function cargarPromedioLibroDashboard(idLibro) {
    try {
        const token = localStorage.getItem('jwtToken');
        const headers = {};
        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }
        
        const res = await fetch(`/api/calificaciones/libros/${idLibro}/promedio`, {
            headers: headers
        });
        if (res.ok) {
            const data = await res.json();
            const elemento = document.querySelector(`.estrellas-display[data-libro-id="${idLibro}"]`);
            if (elemento) {
                const promedio = data.promedio;
                const cantidad = data.cantidad;
                if (cantidad > 0) {
                    elemento.innerHTML = generarEstrellasDisplay(Math.round(promedio)) + 
                                        ` <span style="font-size:0.8em; color:#999;">(${cantidad})</span>`;
                } else {
                    elemento.innerHTML = '☆☆☆☆☆ <span style="font-size:0.8em; color:#999;">(sin calificaciones)</span>';
                }
            }
        }
    } catch (error) {
        console.error('Error cargando promedio:', error);
    }
}

// Cargar calificación actual y mostrar historial en modal
async function cargarCalificacionEnModal(idLibro) {
    try {
        const token = localStorage.getItem('jwtToken');
        const headers = {};
        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }
        
        const res = await fetch(`/api/calificaciones/libros/${idLibro}/promedio`, {
            headers: headers
        });
        if (res.ok) {
            const data = await res.json();
            let calificacionEl = document.getElementById('modalCalificacion');
            if (!calificacionEl) {
                calificacionEl = document.createElement('div');
                calificacionEl.id = 'modalCalificacion';
                calificacionEl.style.marginTop = '12px';
                calificacionEl.style.padding = '10px';
                calificacionEl.style.backgroundColor = '#f5f5f5';
                calificacionEl.style.borderRadius = '5px';
                const modalText = document.querySelector('#modal .modal-content .modal-text');
                if (modalText) {
                    const h4Autor = modalText.querySelector('h4');
                    if (h4Autor) {
                        modalText.insertBefore(calificacionEl, h4Autor.nextSibling);
                    }
                }
            }
            
            if (data.cantidad > 0) {
                calificacionEl.innerHTML = `
                    <div style="margin-bottom:10px;">
                        <strong>Calificación promedio:</strong> ${generarEstrellasDisplay(Math.round(data.promedio))} (${data.cantidad} evaluaciones)
                    </div>
                `;
            } else {
                calificacionEl.innerHTML = `<div><strong>Sin calificaciones aún</strong></div>`;
            }
        }
    } catch (error) {
        console.error('Error cargando calificación en modal:', error);
    }
}

// Attach listeners a los botones "Ver libro"
function attachVerLibroListeners() {
    const modal = document.getElementById('modal');
    if (!modal) return;

    const botonesVer = document.querySelectorAll('.ver-libro');

    botonesVer.forEach(btn => {
        btn.onclick = null;
        
        btn.addEventListener('click', async (e) => {
            e.preventDefault();

            const libroDiv = btn.closest('.libro');
            if (!libroDiv) return;

                // Cargar calificación del libro
                const libroId = libroDiv.dataset.id;
                await cargarCalificacionEnModal(libroId);

                // Extraer datos del libro desde el elemento (dataset)
                const imagen = libroDiv.dataset.imagen || libroDiv.querySelector('img')?.src || '/static/web/imgs/libro_de_la_selva.jpg';
                const titulo = libroDiv.dataset.titulo || libroDiv.querySelector('h3')?.textContent || 'Sin título';
                const autor = libroDiv.dataset.autor || libroDiv.querySelector('p')?.textContent || 'Autor desconocido';
                const descripcion = libroDiv.dataset.descripcion || 'Sin descripción disponible';
                const usuario = libroDiv.dataset.usuario || '';

                // Añadir botón de solicitar intercambio en modal (si no existe)
                let acciones = document.getElementById('modalAcciones');
                if (!acciones) {
                    acciones = document.createElement('div');
                    acciones.id = 'modalAcciones';
                    acciones.style.marginTop = '12px';
                    const btnSolicitarLocal = document.createElement('button');
                    btnSolicitarLocal.id = 'btnSolicitarIntercambio';
                    btnSolicitarLocal.className = 'btn-amarillo';
                    btnSolicitarLocal.innerHTML = '<i class="fas fa-exchange-alt"></i> Solicitar intercambio';
                    acciones.appendChild(btnSolicitarLocal);
                    const modalText = document.querySelector('#modal .modal-content .modal-text');
                    if (modalText) modalText.appendChild(acciones);
                    console.debug('attachVerLibroListeners: modalAcciones created');
                }

            // Rellenar modal
            const modalImgEl = document.getElementById('modalImg');
            if (modalImgEl) modalImgEl.src = imagen;
            const modalTituloEl = document.getElementById('modalTitulo');
            if (modalTituloEl) modalTituloEl.textContent = titulo;
            const modalAutorEl = document.getElementById('modalAutor');
            if (modalAutorEl) modalAutorEl.textContent = autor;
            const modalDescEl = document.getElementById('modalDescripcion');
            if (modalDescEl) modalDescEl.textContent = descripcion;

            let propietarioEl = document.getElementById('modalPropietario');
            if (!propietarioEl) {
                propietarioEl = document.createElement('h4');
                propietarioEl.id = 'modalPropietario';
                propietarioEl.style.color = '#555';
                propietarioEl.style.marginTop = '6px';

                const modalText = document.querySelector('#modal .modal-text');
                modalText.appendChild(propietarioEl);
            }
            propietarioEl.textContent = `Propietario: ${usuario}`;

            // Botón solicitar intercambio (ya creado arriba si hacía falta)

            const btnSolicitar = document.getElementById('btnSolicitarIntercambio');
            btnSolicitar.onclick = async () => {
                try {
                    const libroId = libroDiv.dataset.id;

                    if (!libroId) {
                        Swal.fire({
                            icon: 'error',
                            title: 'Error',
                            text: 'No se pudo identificar el libro.'
                        });
                        return;
                    }

                    const token = localStorage.getItem('jwtToken');
                    const headers = { 'Content-Type': 'application/json' };
                    if (token) headers['Authorization'] = 'Bearer ' + token;

                    const resp = await fetch('/api/intercambios/request', {
                        method: 'POST',
                        headers: headers,
                        body: JSON.stringify({ libroId })
                    });

                    if (resp.status === 201) {
                        Swal.fire({
                            icon: 'success',
                            title: 'Solicitud enviada',
                            text: 'Se envió la solicitud al propietario.'
                        });
                        modal.style.display = 'none';

                    } else if (resp.status === 400) {
                        const data = await resp.json();
                        Swal.fire({
                            icon: 'warning',
                            title: 'No enviado',
                            text: data.error || 'No se pudo procesar la solicitud.'
                        });

                    } else if (resp.status === 401) {
                        Swal.fire({
                            icon: 'info',
                            title: 'Inicia sesión',
                            text: 'Debes iniciar sesión para solicitar un intercambio.'
                        }).then(() => {
                            window.location.href = '/login/';
                        });

                    } else {
                        const data = await resp.json();
                        Swal.fire({
                            icon: 'error',
                            title: 'Error',
                            text: data.error || 'No se pudo solicitar el intercambio.'
                        });
                    }

                } catch (err) {
                    console.error('Error solicitando intercambio', err);
                    Swal.fire({
                        icon: 'error',
                        title: 'Error inesperado',
                        text: 'No se pudo solicitar el intercambio.'
                    });
                }
            };

            modal.style.display = 'block';
        });
    });
}

// Iniciar dashboard
document.addEventListener('DOMContentLoaded', inicializarDashboard);
