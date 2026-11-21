"""
Roles del sistema.

Un mismo login sirve para todos. El rol se deduce del usuario:
  - Superusuario o con perfil Administrador  -> "admin"   (director o ejecutivo)
  - Con perfil Docente                       -> "docente"
  - Con perfil Alumno                        -> "alumno"
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
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
    return hasattr(user, "administrador") and user.administrador.cargo == "DIRECTOR"


class RolRequeridoMixin(LoginRequiredMixin):
    """
    Es un LoginRequiredMixin con una condición más: el rol del usuario tiene que estar en `roles`.
    Se usa así:  class MiVista(RolRequeridoMixin, TemplateView): roles = (ROL_DOCENTE,)
    Con `solo_director = True` además tiene que ser director.
    """
    roles = ()
    solo_director = False
    mensaje_denegado = "No tenés permiso para acceder a esa sección."

    def dispatch(self, request, *args, **kwargs):
        usuario = request.user
        if usuario.is_authenticated:
            if obtener_rol(usuario) not in self.roles or (self.solo_director and not es_director(usuario)):
                messages.error(request, self.mensaje_denegado)
                return redirect("utn:redireccion_panel")  # vuelve a su propio panel
        return super().dispatch(request, *args, **kwargs)  # sin login: LoginRequiredMixin lo manda al login
