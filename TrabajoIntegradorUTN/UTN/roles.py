"""
Lógica de roles del sistema.

Un mismo login sirve para todos. El rol se deduce del usuario:
  - Superusuario o con perfil Administrador  -> "admin"   (director o ejecutivo)
  - Con perfil Docente                       -> "docente"
  - Con perfil Alumno                        -> "alumno"
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

ROL_ADMIN = "admin"
ROL_DOCENTE = "docente"
ROL_ALUMNO = "alumno"


def obtener_rol(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser or hasattr(user, "administrador"):
        return ROL_ADMIN
    if hasattr(user, "docente"):
        return ROL_DOCENTE
    if hasattr(user, "alumno"):
        return ROL_ALUMNO
    return None


def es_director(user):
    """El superusuario cuenta como director."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    admin = getattr(user, "administrador", None)
    return admin is not None and admin.cargo == "DIRECTOR"


def rol_requerido(*roles):
    """Decorador: deja pasar solo a los usuarios con alguno de los roles indicados."""
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if obtener_rol(request.user) not in roles:
                messages.error(request, "No tenés permiso para acceder a esa sección.")
                return redirect("redireccion_panel")
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador
