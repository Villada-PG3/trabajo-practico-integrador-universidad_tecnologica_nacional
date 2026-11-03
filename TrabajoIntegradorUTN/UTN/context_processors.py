from .entidades import menu_para
from .roles import obtener_rol, es_director, ROL_ADMIN


def panel(request):
    """
    Datos disponibles en TODOS los templates:
      rol, es_director -> para mostrar u ocultar cosas según quién es el usuario
      base_template, menu -> el administrador usa el diseño con menú lateral
    """
    rol = obtener_rol(request.user)
    contexto = {"rol": rol, "es_director": es_director(request.user), "base_template": "base.html"}
    if rol == ROL_ADMIN:
        contexto.update(base_template="admin_base.html", menu=menu_para(request.user))
    return contexto
