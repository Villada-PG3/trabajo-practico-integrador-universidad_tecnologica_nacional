"""
Roles del sistema.

Un mismo login sirve para todos. El rol se deduce del usuario:
  - Superusuario o con perfil Administrador  -> "admin"   (director o ejecutivo)
  - Con perfil Docente                       -> "docente"
  - Con perfil Alumno                        -> "alumno"
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
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


class RolRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Es un LoginRequiredMixin con una condición más: el rol del usuario tiene que
    estar en `roles`. Se usa así:  class MiVista(RolRequeridoMixin, TemplateView): roles = (ROL_DOCENTE,)
    """
    roles = ()
    mensaje_denegado = "No tenés permiso para acceder a esa sección."

    def test_func(self):
        return obtener_rol(self.request.user) in self.roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:  # logueado pero con otro rol: vuelve a su panel
            messages.error(self.request, self.mensaje_denegado)
            return redirect("utn:redireccion_panel")
        return super().handle_no_permission()  # sin login: va al login
