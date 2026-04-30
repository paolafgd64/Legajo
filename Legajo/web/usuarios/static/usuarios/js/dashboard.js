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

function obtenerMensajeVacio(carrusel, mensajeSinLibros, mensajeSoloPropios) {
    if (!carrusel) return mensajeSinLibros;

    const totalSistema = Number(carrusel.dataset.totalLibrosSistema || 0);
    const totalAjenos = Number(carrusel.dataset.totalLibrosAjenos || 0);

    if (totalSistema > 0 && totalAjenos === 0) {
        return mensajeSoloPropios;
    }

    return mensajeSinLibros;
}

function crearElementoLibro(libro) {
    const div = document.createElement('div');
    div.className = 'libro';
    div.dataset.id = libro.idLibro || libro.id || '';
    div.dataset.usuarioId = libro.usuarioPropietarioId || '';
    div.dataset.titulo = libro.titulo || '';
    div.dataset.autor = libro.autor || '';
    div.dataset.descripcion = libro.sinopsis || 'Sin descripcion disponible';
    div.dataset.imagen = libro.urlImagen || '/static/gestion_libros/imgs/libropredeterminado1.png';
    div.dataset.usuario = libro.usuario || 'Propietario desconocido';

    div.innerHTML = `
        <img src="${libro.urlImagen || '/static/gestion_libros/imgs/libropredeterminado1.png'}" alt="${libro.titulo || 'Libro'}">
        <h3>${libro.titulo || 'Sin titulo'}</h3>
        <p>${libro.autor || 'Autor desconocido'}</p>
        <div class="estrellas-display">Disponible</div>
        <button class="ver-libro"><i class="fa fa-eye"></i> Ver</button>
    `;

    return div;
}

function crearElementoGenero(genero) {
    const div = document.createElement('div');
    div.className = 'libro genero-card';
    div.innerHTML = `
        <img src="${genero.imagen || '/static/gestion_libros/imgs/libropredeterminado1.png'}" alt="${genero.genero || 'Genero'}">
        <h3>${genero.genero || 'Genero'}</h3>
        <p>${genero.totalLibros} libro${genero.totalLibros === 1 ? '' : 's'} disponible${genero.totalLibros === 1 ? '' : 's'}</p>
        <div class="estrellas-display">Explorar</div>
    `;
    return div;
}

function construirGeneros(libros) {
    const mapa = new Map();

    libros.forEach((libro) => {
        const generos = Array.isArray(libro.generos) && libro.generos.length ? libro.generos : [libro.genero || 'Sin genero'];
        generos.forEach((generoNombre) => {
            const clave = String(generoNombre || 'Sin genero').trim() || 'Sin genero';
            if (!mapa.has(clave)) {
                mapa.set(clave, {
                    genero: clave,
                    totalLibros: 0,
                    imagen: libro.urlImagen || '/static/gestion_libros/imgs/libropredeterminado1.png'
                });
            }
            mapa.get(clave).totalLibros += 1;
        });
    });

    return Array.from(mapa.values()).sort((a, b) => a.genero.localeCompare(b.genero, 'es'));
}

function attachVerLibroListeners() {
    const modal = document.getElementById('modal');
    if (!modal) return;

    const botonesVer = document.querySelectorAll('#recomendados .ver-libro');
    botonesVer.forEach((btn) => {
        btn.onclick = null;
        btn.addEventListener('click', (e) => {
            e.preventDefault();

            const libroDiv = btn.closest('.libro');
            if (!libroDiv) return;

            const modalImgEl = document.getElementById('modalImg');
            if (modalImgEl) modalImgEl.src = libroDiv.dataset.imagen || '/static/gestion_libros/imgs/libropredeterminado1.png';
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

            const btnReportar = document.getElementById('btnReportarUsuario');
            if (btnReportar) {
                btnReportar.onclick = async () => {
                    try {
                        const payload = await mostrarDialogoReporte(libroDiv);
                        if (!payload) {
                            return;
                        }

                        const data = await enviarReporteUsuario(payload);

                        if (window.Swal) {
                            await Swal.fire({
                                icon: 'success',
                                title: 'Reporte enviado',
                                text: data.message || 'El reporte fue enviado correctamente.'
                            });
                        } else {
                            alert(data.message || 'El reporte fue enviado correctamente.');
                        }
                    } catch (error) {
                        console.error('Error reportando usuario:', error);
                        if (window.Swal) {
                            Swal.fire({
                                icon: 'error',
                                title: 'No se pudo enviar',
                                text: error.message || 'Ocurrio un error al enviar el reporte.'
                            });
                        } else {
                            alert(error.message || 'Ocurrio un error al enviar el reporte.');
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

async function mostrarDialogoReporte(libroDiv) {
    const usuarioReportadoId = Number(libroDiv.dataset.usuarioId || 0);
    if (!usuarioReportadoId) {
        throw new Error('No fue posible identificar al usuario que quieres reportar.');
    }

    if (!window.Swal) {
        const motivoManual = window.prompt('Motivo del reporte');
        if (!motivoManual) return null;
        const descripcionManual = window.prompt('Describe lo ocurrido');
        if (!descripcionManual) return null;
        return {
            usuarioReportadoId,
            motivo: motivoManual.trim(),
            descripcion: descripcionManual.trim(),
        };
    }

    const result = await Swal.fire({
        title: 'Reportar usuario',
        customClass: {
            popup: 'report-swal-popup',
            title: 'report-swal-title',
            htmlContainer: 'report-swal-html',
            confirmButton: 'report-swal-confirm',
            cancelButton: 'report-swal-cancel',
        },
        html: `
            <div class="report-modal-layout">
                <div class="report-modal-intro">
                    <h3>Usuario reportado</h3>
                    <p class="report-modal-user">${libroDiv.dataset.usuario || 'Usuario'}</p>
                    <p>Cuentanos que paso para que el equipo admin pueda revisar el caso.</p>
                </div>
                <div class="report-modal-form">
                    <label for="swal-report-motivo">Motivo</label>
                    <select id="swal-report-motivo" class="report-modal-input">
                        <option value="">Selecciona un motivo</option>
                        <option value="Mal comportamiento">Mal comportamiento</option>
                        <option value="Incumplimiento de intercambio">Incumplimiento de intercambio</option>
                        <option value="Spam o contenido ofensivo">Spam o contenido ofensivo</option>
                        <option value="Suplantacion o fraude">Suplantacion o fraude</option>
                    </select>
                    <label for="swal-report-descripcion">Descripcion</label>
                    <textarea id="swal-report-descripcion" class="report-modal-input report-modal-textarea" placeholder="Describe lo ocurrido con detalle"></textarea>
                </div>
            </div>
        `,
        focusConfirm: false,
        showCancelButton: true,
        buttonsStyling: false,
        confirmButtonText: 'Enviar reporte',
        cancelButtonText: 'Cancelar',
        preConfirm: () => {
            const motivo = document.getElementById('swal-report-motivo')?.value?.trim() || '';
            const descripcion = document.getElementById('swal-report-descripcion')?.value?.trim() || '';

            if (!motivo) {
                Swal.showValidationMessage('Selecciona un motivo.');
                return false;
            }
            if (descripcion.length < 10) {
                Swal.showValidationMessage('Describe lo ocurrido con al menos 10 caracteres.');
                return false;
            }

            return { usuarioReportadoId, motivo, descripcion };
        },
    });

    return result.isConfirmed ? result.value : null;
}

async function enviarReporteUsuario(payload) {
    const resp = await fetch('/api/reportes-usuarios', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(payload)
    });

    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        throw new Error(data.message || 'No se pudo enviar el reporte.');
    }

    return data;
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
            carruselRecomendados.innerHTML = `<p style="padding:20px;">${obtenerMensajeVacio(
                carruselRecomendados,
                'No hay libros de otros usuarios disponibles por ahora.',
                'Hay libros registrados, pero ninguno pertenece a otros usuarios para esta cuenta.'
            )}</p>`;
        } else {
            libros.slice(0, 8).forEach((libro) => {
                carruselRecomendados.appendChild(crearElementoLibro(libro));
            });
        }
    }

    if (carruselGeneros && Array.isArray(libros)) {
        carruselGeneros.innerHTML = '';
        const generos = construirGeneros(libros);
        if (generos.length === 0) {
            carruselGeneros.innerHTML = `<p style="padding:20px;">${obtenerMensajeVacio(
                carruselGeneros,
                'Aun no hay generos para mostrar.',
                'Hay libros registrados, pero no hay generos de otros usuarios para mostrar en esta cuenta.'
            )}</p>`;
        } else {
            generos.forEach((genero) => {
                carruselGeneros.appendChild(crearElementoGenero(genero));
            });
        }
    }

    attachVerLibroListeners();
}

document.addEventListener('DOMContentLoaded', inicializarDashboard);

