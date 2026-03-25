async function obtenerUsuarioActual() {
    try {
        const resp = await fetch('/api/auth/me', {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (resp.status === 401) {
            return null;
        }

        if (!resp.ok) {
            throw new Error('No se pudo obtener el usuario actual');
        }

        return await resp.json();
    } catch (e) {
        console.error('Error obteniendo usuario actual:', e);
        return undefined;
    }
}

async function cargarLibrosRecomendados() {
    try {
        const resp = await fetch('/api/libros/recomendados', {
            headers: {
                'Accept': 'application/json'
            }
        });
        if (resp.status === 401) {
            return null;
        }
        if (!resp.ok) {
            throw new Error('Error al cargar libros recomendados');
        }
        return await resp.json();
    } catch (e) {
        console.error('Error cargando recomendados:', e);
        return undefined;
    }
}

function crearElementoLibro(libro) {
    const div = document.createElement('div');
    div.className = 'libro';
    div.dataset.id = libro.idLibro || libro.id || '';
    div.dataset.titulo = libro.titulo || '';
    div.dataset.autor = libro.autor || '';
    div.dataset.descripcion = libro.sinopsis || 'Sin descripcion disponible';
    div.dataset.imagen = libro.urlImagen || '/static/web/imgs/libro_de_la_selva.jpg';
    div.dataset.usuario = libro.usuario || 'Propietario desconocido';

    div.innerHTML = `
        <img src="${libro.urlImagen || '/static/web/imgs/libro_de_la_selva.jpg'}" alt="${libro.titulo || 'Libro'}">
        <h3>${libro.titulo || 'Sin titulo'}</h3>
        <p>${libro.autor || 'Autor desconocido'}</p>
        <div class="estrellas-display">Disponible</div>
        <button class="ver-libro"><i class="fa fa-eye"></i> Ver</button>
    `;

    return div;
}

function attachVerLibroListeners() {
    const modal = document.getElementById('modal');
    if (!modal) return;

    const botonesVer = document.querySelectorAll('#recomendados .ver-libro, #generos .ver-libro');
    botonesVer.forEach((btn) => {
        btn.onclick = null;
        btn.addEventListener('click', (e) => {
            e.preventDefault();

            const libroDiv = btn.closest('.libro');
            if (!libroDiv) return;

            const modalImgEl = document.getElementById('modalImg');
            if (modalImgEl) modalImgEl.src = libroDiv.dataset.imagen || '/static/web/imgs/libro_de_la_selva.jpg';
            const modalTituloEl = document.getElementById('modalTitulo');
            if (modalTituloEl) modalTituloEl.textContent = libroDiv.dataset.titulo || 'Sin titulo';
            const modalAutorEl = document.getElementById('modalAutor');
            if (modalAutorEl) modalAutorEl.textContent = libroDiv.dataset.autor || 'Autor desconocido';
            const modalDescEl = document.getElementById('modalDescripcion');
            if (modalDescEl) modalDescEl.textContent = libroDiv.dataset.descripcion || 'Sin descripcion disponible';

            let propietarioEl = document.getElementById('modalPropietario');
            if (!propietarioEl) {
                propietarioEl = document.createElement('h4');
                propietarioEl.id = 'modalPropietario';
                propietarioEl.style.color = '#555';
                propietarioEl.style.marginTop = '6px';
                const modalText = document.querySelector('#modal .modal-text');
                if (modalText) {
                    modalText.appendChild(propietarioEl);
                }
            }
            propietarioEl.textContent = `Propietario: ${libroDiv.dataset.usuario || 'Propietario desconocido'}`;

            const btnSolicitar = document.getElementById('btnSolicitarIntercambio');
            if (btnSolicitar) {
                btnSolicitar.onclick = async () => {
                    try {
                        const resp = await fetch('/api/intercambios/request', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCsrfToken()
                            },
                            body: JSON.stringify({
                                libroId: libroDiv.dataset.id
                            })
                        });

                        const data = await resp.json();
                        if (!resp.ok) {
                            throw new Error(data.message || 'No se pudo enviar la solicitud');
                        }

                        if (window.Swal) {
                            await Swal.fire({
                                icon: 'success',
                                title: 'Solicitud enviada',
                                text: data.message || 'Se envio la solicitud de intercambio'
                            });
                        } else {
                            alert(data.message || 'Se envio la solicitud de intercambio');
                        }

                        modal.style.display = 'none';
                    } catch (error) {
                        console.error('Error solicitando intercambio:', error);
                        if (window.Swal) {
                            Swal.fire({
                                icon: 'error',
                                title: 'No se pudo solicitar',
                                text: error.message || 'Ocurrio un error al solicitar el intercambio'
                            });
                        } else {
                            alert(error.message || 'Ocurrio un error al solicitar el intercambio');
                        }
                    }
                };
            }
            modal.style.display = 'block';
        });
    });
}

function getCsrfToken() {
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (const cookie of cookies) {
        const trimmed = cookie.trim();
        if (trimmed.startsWith('csrftoken=')) {
            return decodeURIComponent(trimmed.substring('csrftoken='.length));
        }
    }
    return '';
}

async function inicializarDashboard() {
    const usuario = await obtenerUsuarioActual();
    if (usuario === null) {
        window.location.href = '/login/';
        return;
    }

    const nombreEl = document.getElementById('nombreRecibido');
    if (nombreEl && usuario) {
        nombreEl.textContent = usuario.primerNombre || 'Usuario';
    }

    const libros = await cargarLibrosRecomendados();
    if (libros === null) {
        window.location.href = '/login/';
        return;
    }

    const carruselRecomendados = document.getElementById('recomendados');
    const carruselGeneros = document.getElementById('generos');

    if (carruselRecomendados && Array.isArray(libros)) {
        carruselRecomendados.innerHTML = '';
        if (libros.length === 0) {
            carruselRecomendados.innerHTML = '<p style="padding:20px;">No hay libros de otros usuarios disponibles por ahora.</p>';
        } else {
            libros.slice(0, 8).forEach((libro) => {
                carruselRecomendados.appendChild(crearElementoLibro(libro));
            });
        }
    }

    if (carruselGeneros && Array.isArray(libros)) {
        carruselGeneros.innerHTML = '';
        libros.slice(0, 8).forEach((libro) => {
            carruselGeneros.appendChild(crearElementoLibro(libro));
        });
    }

    attachVerLibroListeners();
}

document.addEventListener('DOMContentLoaded', inicializarDashboard);
