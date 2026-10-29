from .roles import obtener_rol, es_director


def rol_usuario(request):
    """Deja disponibles {{ rol }} y {{ es_director }} en todos los templates."""
    return {
        "rol": obtener_rol(request.user),
        "es_director": es_director(request.user),
    }
