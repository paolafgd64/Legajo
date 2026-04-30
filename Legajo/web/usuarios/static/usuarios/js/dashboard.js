const legajoSwalClasses = {
  popup: 'legajo-swal-popup',
  title: 'legajo-swal-title',
  htmlContainer: 'legajo-swal-html',
  confirmButton: 'legajo-swal-confirm',
  denyButton: 'legajo-swal-deny',
  cancelButton: 'legajo-swal-cancel',
  input: 'legajo-swal-input'
};
const legajoSwalOptions = {
  buttonsStyling: false,
  customClass: legajoSwalClasses
};
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

const dashboardBusqueda = {
    libros: [],
    termino: ''
};

function normalizarTextoBusqueda(valor) {
    return String(valor || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .trim();
}

function obtenerTextoBusquedaLibro(libro) {
    const generos = Array.isArray(libro.generos) ? libro.generos.join(' ') : (libro.genero || '');
    return normalizarTextoBusqueda([
        libro.titulo,
        libro.autor,
        libro.usuario,
        libro.ciudadPropietario,
        libro.ciudad,
        libro.sinopsis,
        generos
    ].join(' '));
}

function filtrarLibrosPorBusqueda(libros, termino) {
    const busqueda = normalizarTextoBusqueda(termino);
    if (!busqueda) return libros;
    return libros.filter((libro) => obtenerTextoBusquedaLibro(libro).includes(busqueda));
}

function escaparHtml(valor) {
    return String(valor || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
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
    div.dataset.ciudad = libro.ciudadPropietario || libro.ciudad || '';
    div.dataset.stock = libro.stock || 1;

    const imagen = escaparHtml(libro.urlImagen || '/static/gestion_libros/imgs/libropredeterminado1.png');
    const titulo = escaparHtml(libro.titulo || 'Sin titulo');
    const autor = escaparHtml(libro.autor || 'Autor desconocido');
    const stock = escaparHtml(String(libro.stock || 1));

    div.innerHTML = `
        <img src="${imagen}" alt="${titulo || 'Libro'}">
        <h3>${titulo}</h3>
        <p>${autor}</p>
        <p class="stock-libro"><strong>Stock:</strong> ${stock}</p>
        <div class="estrellas-display">Disponible</div>
        <button class="ver-libro"><i class="fa fa-eye"></i> Ver</button>
    `;

    return div;
}

function obtenerGenerosLibro(libro) {
    if (Array.isArray(libro.generos) && libro.generos.length) {
        return libro.generos
            .map((genero) => String(genero || '').trim())
            .filter(Boolean);
    }

    const genero = String(libro.genero || '').trim();
    return genero ? [genero] : ['Sin genero'];
}

function construirLibrosPorGenero(libros) {
    const mapa = new Map();

    libros.forEach((libro) => {
        obtenerGenerosLibro(libro).forEach((generoNombre) => {
            const clave = generoNombre || 'Sin genero';
            if (!mapa.has(clave)) {
                mapa.set(clave, []);
            }
            mapa.get(clave).push(libro);
        });
    });

    return Array.from(mapa.entries()).sort(([generoA], [generoB]) => generoA.localeCompare(generoB, 'es'));
}

function crearIdCarruselGenero(genero, indice) {
    const slug = normalizarTextoBusqueda(genero)
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
    return `genero-${slug || 'sin-genero'}-${indice}`;
}

function renderizarRecomendados(libros, esBusquedaActiva) {
    const carruselRecomendados = document.getElementById('recomendados');
    if (!carruselRecomendados) return;

    carruselRecomendados.innerHTML = '';
    if (libros.length === 0) {
        carruselRecomendados.innerHTML = `<p class="mensaje-carrusel-vacio">${
            esBusquedaActiva
                ? 'No encontramos libros que coincidan con tu busqueda.'
                : obtenerMensajeVacio(
                    carruselRecomendados,
                    'No hay libros de otros usuarios disponibles por ahora.',
                    'Hay libros registrados, pero ninguno pertenece a otros usuarios para esta cuenta.'
                )
        }</p>`;
        return;
    }

    const librosVisibles = esBusquedaActiva ? libros : libros.slice(0, 8);
    librosVisibles.forEach((libro) => {
        carruselRecomendados.appendChild(crearElementoLibro(libro));
    });
}

function renderizarLibrosPorGenero(libros, esBusquedaActiva) {
    const contenedorGeneros = document.getElementById('librosPorGenero');
    if (!contenedorGeneros) return;

    contenedorGeneros.innerHTML = '';
    const generos = construirLibrosPorGenero(libros);
    if (generos.length === 0) {
        contenedorGeneros.innerHTML = `<p class="mensaje-carrusel-vacio">${
            esBusquedaActiva
                ? 'No hay libros por genero para la busqueda actual.'
                : obtenerMensajeVacio(
                    contenedorGeneros,
                    'Aun no hay libros por genero para mostrar.',
                    'Hay libros registrados, pero ninguno pertenece a otros usuarios para esta cuenta.'
                )
        }</p>`;
        return;
    }

    generos.forEach(([genero, librosGenero], indice) => {
        const carruselId = crearIdCarruselGenero(genero, indice);
        const seccion = document.createElement('section');
        seccion.className = 'seccion-carrusel genero-libros-seccion';
        seccion.innerHTML = `
            <div class="genero-libros-encabezado">
                <h3 class="titulo-seccion">${escaparHtml(genero)}</h3>
                <span>${librosGenero.length} libro${librosGenero.length === 1 ? '' : 's'}</span>
            </div>
            <div class="contenedor-carrusel">
                <button class="flecha izquierda" type="button" onclick="moverCarrusel('${carruselId}', -1)">&#10094;</button>
                <div class="carrusel-libros" id="${carruselId}"></div>
                <button class="flecha derecha" type="button" onclick="moverCarrusel('${carruselId}', 1)">&#10095;</button>
            </div>
        `;

        const carrusel = seccion.querySelector('.carrusel-libros');
        librosGenero.forEach((libro) => {
            carrusel.appendChild(crearElementoLibro(libro));
        });

        contenedorGeneros.appendChild(seccion);
    });
}

function actualizarEstadoBusqueda(totalResultados, termino) {
    const estadoEl = document.getElementById('resultadoBusquedaInicio');
    const tituloEl = document.getElementById('tituloRecomendados');
    const limpiarBtn = document.getElementById('limpiarBusquedaInicio');
    const hayBusqueda = normalizarTextoBusqueda(termino).length > 0;

    if (tituloEl) {
        tituloEl.textContent = hayBusqueda ? 'Resultados de busqueda' : 'Recomendados';
    }

    if (limpiarBtn) {
        limpiarBtn.classList.toggle('is-visible', hayBusqueda);
    }

    if (!estadoEl) return;
    if (!hayBusqueda) {
        estadoEl.textContent = '';
        return;
    }

    estadoEl.textContent = `${totalResultados} resultado${totalResultados === 1 ? '' : 's'} para "${termino.trim()}"`;
}

function aplicarBusquedaInicio() {
    const resultados = filtrarLibrosPorBusqueda(dashboardBusqueda.libros, dashboardBusqueda.termino);
    const esBusquedaActiva = normalizarTextoBusqueda(dashboardBusqueda.termino).length > 0;

    renderizarRecomendados(resultados, esBusquedaActiva);
    renderizarLibrosPorGenero(resultados, esBusquedaActiva);
    actualizarEstadoBusqueda(resultados.length, dashboardBusqueda.termino);
    attachVerLibroListeners();
}

function configurarBusquedaInicio() {
    const input = document.getElementById('busquedaLibrosInicio');
    const limpiarBtn = document.getElementById('limpiarBusquedaInicio');

    if (input) {
        input.addEventListener('input', () => {
            dashboardBusqueda.termino = input.value;
            aplicarBusquedaInicio();
        });
    }

    if (limpiarBtn) {
        limpiarBtn.addEventListener('click', () => {
            dashboardBusqueda.termino = '';
            if (input) {
                input.value = '';
                input.focus();
            }
            aplicarBusquedaInicio();
        });
    }
}

function attachVerLibroListeners() {
    const modal = document.getElementById('modal');
    if (!modal) return;

    const botonesVer = document.querySelectorAll('.carrusel-libros .ver-libro');
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

            let stockEl = document.getElementById('modalStock');
            if (!stockEl) {
                stockEl = document.createElement('h4');
                stockEl.id = 'modalStock';
                stockEl.style.color = '#555';
                stockEl.style.marginTop = '6px';
                const modalText = document.querySelector('#modal .modal-text');
                if (modalText) {
                    modalText.appendChild(stockEl);
                }
            }
            stockEl.textContent = `Stock: ${libroDiv.dataset.stock || '1'}`;

            let ciudadEl = document.getElementById('modalCiudad');
            if (!ciudadEl) {
                ciudadEl = document.createElement('h4');
                ciudadEl.id = 'modalCiudad';
                ciudadEl.style.color = '#555';
                ciudadEl.style.marginTop = '6px';
                const modalText = document.querySelector('#modal .modal-text');
                if (modalText) {
                    modalText.appendChild(ciudadEl);
                }
            }
            ciudadEl.textContent = `Ciudad: ${libroDiv.dataset.ciudad || 'No especificada'}`;

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
    const libroReportadoId = Number(libroDiv.dataset.id || 0);
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
            libroReportadoId,
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
                    <p><strong>Libro reportado:</strong> ${libroDiv.dataset.titulo || 'Libro sin titulo'}</p>
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

            return { usuarioReportadoId, libroReportadoId, motivo, descripcion };
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

    if (Array.isArray(libros)) {
        dashboardBusqueda.libros = libros;
        configurarBusquedaInicio();
        aplicarBusquedaInicio();
    }
}

document.addEventListener('DOMContentLoaded', inicializarDashboard);

