// alerts.js
// Archivo centralizado para manejar todas las alertas de SweetAlert2

// ============================
// Alertas simples
// ============================

export function alertSuccess(mensaje = "Operación realizada correctamente") {
    Swal.fire({
        icon: "success",
        title: "Éxito",
        text: mensaje,
        confirmButtonText: "Aceptar"
    });
}

export function alertError(mensaje = "Ocurrió un error inesperado") {
    Swal.fire({
        icon: "error",
        title: "Error",
        text: mensaje,
        confirmButtonText: "Aceptar"
    });
}

export function alertInfo(mensaje = "Información importante") {
    Swal.fire({
        icon: "info",
        title: "Información",
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
// Alertas con confirmación (type confirm)
// ============================

/**
 * Confirmación básica para eliminar, guardar, etc.
 * Ejemplo:
 * alertConfirm("¿Seguro?", "Eliminarás este registro").then((ok) => {
 *     if (ok) ejecutarAccion();
 * });
 */
export function alertConfirm(titulo = "¿Estás seguro?", texto = "Esta acción no se puede deshacer") {
    return Swal.fire({
        title: titulo,
        text: texto,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Sí, continuar",
        cancelButtonText: "Cancelar"
    }).then((result) => {
        return result.isConfirmed;
    });
}


// ============================
// Alertas con input (similar a prompt())
// ============================

export function alertPrompt(titulo = "Ingresa un valor", placeholder = "Escribe aquí...") {
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
