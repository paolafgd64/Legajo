// alerts.js
// Archivo centralizado para manejar todas las alertas de SweetAlert2

// ============================
// Alertas simples
// ============================

export function alertSuccess(mensaje = "OperaciÃ³n realizada correctamente") {
    Swal.fire({
        icon: "success",
        title: "Ã‰xito",
        text: mensaje,
        confirmButtonText: "Aceptar"
    });
}

export function alertError(mensaje = "OcurriÃ³ un error inesperado") {
    Swal.fire({
        icon: "error",
        title: "Error",
        text: mensaje,
        confirmButtonText: "Aceptar"
    });
}

export function alertInfo(mensaje = "InformaciÃ³n importante") {
    Swal.fire({
        icon: "info",
        title: "InformaciÃ³n",
        text: mensaje,
        confirmButtonText: "Aceptar"
    });
}

export function alertWarning(mensaje = "Advertencia") {
    Swal.fire({
        icon: "warning",
        title: "Advertencia",
        text: mensaje,
        confirmButtonText: "Aceptar"
    });
}


// ============================
// Alertas con confirmaciÃ³n (type confirm)
// ============================

/**
 * ConfirmaciÃ³n bÃ¡sica para eliminar, guardar, etc.
 * Ejemplo:
 * alertConfirm("Â¿Seguro?", "EliminarÃ¡s este registro").then((ok) => {
 *     if (ok) ejecutarAccion();
 * });
 */
export function alertConfirm(titulo = "Â¿EstÃ¡s seguro?", texto = "Esta acciÃ³n no se puede deshacer") {
    return Swal.fire({
        title: titulo,
        text: texto,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "SÃ­, continuar",
        cancelButtonText: "Cancelar"
    }).then((result) => {
        return result.isConfirmed;
    });
}


// ============================
// Alertas con input (similar a prompt())
// ============================

export function alertPrompt(titulo = "Ingresa un valor", placeholder = "Escribe aquÃ­...") {
    return Swal.fire({
        title: titulo,
        input: "text",
        inputPlaceholder: placeholder,
        showCancelButton: true,
        confirmButtonText: "Aceptar",
        cancelButtonText: "Cancelar"
    }).then((result) => {
        return result.value || null;
    });
}


// ============================
// Alertas tipo carga (loading)
// ============================

export function alertLoading(mensaje = "Cargando...") {
    Swal.fire({
        title: mensaje,
        allowOutsideClick: false,
        allowEscapeKey: false,
        didOpen: () => Swal.showLoading()
    });
}

export function closeLoading() {
    Swal.close();
}

