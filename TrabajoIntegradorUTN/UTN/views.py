from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import DetailView, ListView, UpdateView

from .forms import LoginForm, CuentaUsuarioForm, CambiarPasswordForm
from .models import Alumno, Carrera, DictadoMateria, Inscripcion
from .roles import obtener_rol, RolRequeridoMixin, ROL_ADMIN, ROL_DOCENTE, ROL_ALUMNO


# ---------------------------------------------------------------------------
# Landing (vista basada en función: no necesita nada de lo que ofrecen las genéricas)
# ---------------------------------------------------------------------------
ICONOS_CARRERA = [
    ("sistemas", "bi-cpu"),
    ("electr", "bi-motherboard"),
    ("eléctr", "bi-lightning-charge"),
    ("industrial", "bi-gear-wide-connected"),
    ("mecánica", "bi-tools"),
    ("mecanica", "bi-tools"),
    ("civil", "bi-building"),
    ("química", "bi-droplet-half"),
    ("quimica", "bi-droplet-half"),
    ("metal", "bi-fire"),
    ("aero", "bi-airplane"),
]

FOTOS = [
    {"url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQBs5zALy7bHbwEEZsIhmb9i5f21WzYBQ6MZJGj6Xc1TwnSzE7rZ3LpkXw&s=10", "alt": "Edificio central"},
    {"url": "https://fra.utn.edu.ar/wp-content/uploads/2024/08/1-23.jpg", "alt": "Laboratorios"},
    {"url": "https://www.academia.frc.utn.edu.ar/pub/image/IMG_20130311_191734.jpg", "alt": "Aulas"},
    {"url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT2RUdpeXiPMmSXxtQ9h1UFbWLNPHloJ0he6mTBYxiCGu-vmVasVK9umAHk&s=10", "alt": "Ciudad Universitaria"},
]

NOTICIAS = [
    {"categoria": "Ingreso", "titulo": "Ingreso a Ingenierías 2027",
     "resumen": "Requisitos, fechas y clases grabadas de apoyo para el Ciclo Introductorio.",
     "link": "https://www.frc.utn.edu.ar/ingreso-ingenierias-2027/"},
    {"categoria": "Investigación", "titulo": "Sombras y Sonidos - VR",
     "resumen": "Aplicación de realidad virtual desarrollada en el Centro de Investigación y Transferencia en Acústica de la FRC.",
     "link": "https://www.frc.utn.edu.ar/"},
    {"categoria": "Comunidad", "titulo": "Radio FM 94.3",
     "resumen": "La radio de la Facultad, con contenidos de la comunidad universitaria.",
     "link": "https://www.frc.utn.edu.ar/"},
]


def _icono_carrera(nombre):
    nombre = nombre.lower()
    return next((icono for palabra, icono in ICONOS_CARRERA if palabra in nombre), "bi-mortarboard")


def landing(request):
    carreras = [{"nombre": c.nombre, "icono": _icono_carrera(c.nombre)} for c in Carrera.objects.all()]
    return render(request, "landing.html", {"carreras": carreras, "fotos": FOTOS, "noticias": NOTICIAS})


# ---------------------------------------------------------------------------
# Login único + redirección según el rol
# ---------------------------------------------------------------------------
class LoginUnificadoView(LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


@login_required
def redireccion_panel(request):
    """Después del login, manda a cada usuario a su panel según su rol."""
    rol = obtener_rol(request.user)
    if rol == ROL_ADMIN:
        return redirect("utn:admin_dashboard")
    if rol == ROL_DOCENTE:
        return redirect("utn:panel_docente")
    if rol == ROL_ALUMNO:
        return redirect("utn:panel_alumno", pk=request.user.alumno.pk)

    logout(request)
    messages.error(request, "Tu usuario no tiene un perfil asignado. Contactá a administración.")
    return redirect("utn:login")


# ---------------------------------------------------------------------------
# Mi cuenta: cambiar usuario y contraseña (alumnos, docentes y administradores)
# ---------------------------------------------------------------------------
class CuentaUsuarioView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = CuentaUsuarioForm
    template_name = "mi_cuenta.html"
    success_url = reverse_lazy("utn:mi_cuenta")
    success_message = "Listo, tu nombre de usuario se actualizó."

    def get_object(self, queryset=None):
        return self.request.user  # siempre edita al usuario logueado, nunca a otro


class CuentaPasswordView(SuccessMessageMixin, PasswordChangeView):
    """PasswordChangeView ya viene hecha por Django: exige login, valida la clave actual y no cierra la sesión."""
    form_class = CambiarPasswordForm
    template_name = "mi_cuenta.html"
    success_url = reverse_lazy("utn:mi_cuenta_password")
    success_message = "Tu contraseña se cambió correctamente."


# ---------------------------------------------------------------------------
# Panel del alumno
# ---------------------------------------------------------------------------
class AlumnoMixin(RolRequeridoMixin):
    """Vistas de un alumno: él ve solo lo suyo; el administrador puede ver a cualquiera."""
    roles = (ROL_ALUMNO, ROL_ADMIN)

    @cached_property
    def alumno(self):
        alumno = get_object_or_404(Alumno.objects.select_related("carrera"), pk=self.kwargs["pk"])
        if obtener_rol(self.request.user) != ROL_ADMIN and alumno.usuario_id != self.request.user.id:
            raise PermissionDenied  # 403: es el panel de otro alumno
        return alumno

    def get_context_data(self, **kwargs):
        return super().get_context_data(alumno=self.alumno, **kwargs)

    def inscripciones(self):
        return (self.alumno.inscripciones
                .select_related("dictado_materia__materia", "dictado_materia__curso", "dictado_materia__ciclo_lectivo")
                .prefetch_related("evaluaciones__instancia__tipo_evaluacion", "historial_condiciones__condicion"))


class PanelAlumnoView(AlumnoMixin, DetailView):
    model = Alumno
    template_name = "panel_alumno.html"

    def get_object(self, queryset=None):
        return self.alumno

    def get_context_data(self, **kwargs):
        return super().get_context_data(inscripciones=self.inscripciones(), **kwargs)


class InscribirView(AlumnoMixin, ListView):
    """GET: muestra los dictados de la carrera del alumno. POST: lo inscribe en el elegido."""
    context_object_name = "dictados"
    template_name = "inscribir.html"

    def get_queryset(self):
        return (DictadoMateria.objects
                .filter(materia__carrera=self.alumno.carrera)  # solo materias de SU carrera
                .select_related("materia", "curso__turno", "ciclo_lectivo")
                .prefetch_related("horarios__modulos"))

    def post(self, request, *args, **kwargs):
        dictado = get_object_or_404(self.get_queryset(), pk=request.POST.get("dictado_id"))
        inscripcion = Inscripcion(alumno=self.alumno, dictado_materia=dictado)
        try:
            with transaction.atomic():
                inscripcion.full_clean()  # valida carrera y duplicados (models.py)
                inscripcion.save()
        except (ValidationError, IntegrityError) as error:
            mensaje = " ".join(error.messages) if isinstance(error, ValidationError) else "Ya estás inscripto en esta materia."
            messages.warning(request, mensaje)
            return redirect("utn:inscribir_materia", pk=self.alumno.pk)

        messages.success(request, f"¡Inscripción exitosa! Tu código es: {inscripcion.codigo_inscripcion}")
        return redirect("utn:panel_alumno", pk=self.alumno.pk)


class ReporteRegularesView(AlumnoMixin, ListView):
    context_object_name = "regulares"
    template_name = "reporte_regulares.html"

    def get_queryset(self):
        return [i for i in self.inscripciones() if i.condicion_actual == "Regular"]
