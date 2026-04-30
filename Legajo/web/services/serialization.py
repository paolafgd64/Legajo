def serialize_book(libro):
    autores = list(libro.autores.all())
    generos = list(libro.generos.all())
    autor_nombre = str(autores[0]) if autores else ''
    propietario = libro.usuario_propietario
    promedio_calificacion = getattr(libro, 'promedio_calificacion', None)
    total_calificaciones = getattr(libro, 'total_calificaciones', 0) or 0

    return {
        'id': libro.id,
        'idLibro': libro.id,
        'titulo': libro.titulo,
        'sinopsis': libro.sinopsis,
        'estado': libro.estado,
        'urlImagen': libro.url_imagen,
        'url_imagen': libro.url_imagen,
        'autor': autor_nombre,
        'autores': [str(autor) for autor in autores],
        'genero': generos[0].nombre if generos else '',
        'generos': [genero.nombre for genero in generos],
        'usuarioPropietarioId': libro.usuario_propietario_id,
        'usuario': str(propietario) if propietario else 'Usuario desconocido',
        'ciudadPropietario': propietario.ciudad if propietario else '',
        'ciudad': propietario.ciudad if propietario else '',
        'activo': bool(libro.activo),
        'calificacion': round(promedio_calificacion, 1) if promedio_calificacion is not None else 0,
        'totalCalificaciones': total_calificaciones,
        'stock': getattr(libro, 'stock', 1),
    }
