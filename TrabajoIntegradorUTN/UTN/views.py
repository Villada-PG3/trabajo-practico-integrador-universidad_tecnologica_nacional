from datetime import date

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
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from .forms import LoginForm, CuentaUsuarioForm, CambiarPasswordForm
from .models import Alumno, Carrera, DictadoMateria, Inscripcion, Materia
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
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
COLORES_CRONOGRAMA = ["primary", "success", "warning", "info", "danger", "secondary"]  # clases text-bg-* de Bootstrap


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

    def armar_cronograma(self):
        """Grilla semanal: una fila por franja horaria y una columna por día, con las materias que cursa."""
        celdas, materias = {}, []
        for n, inscripcion in enumerate(self.alumno.inscripciones_en_curso()):
            dictado, color = inscripcion.dictado_materia, COLORES_CRONOGRAMA[n % len(COLORES_CRONOGRAMA)]
            materias.append({"dictado": dictado, "color": color})
            for horario in dictado.horarios.all():
                for modulo in horario.modulos.all():
                    celdas[(modulo.hora_inicio, modulo.hora_fin, horario.dia)] = {"sigla": dictado.materia.sigla, "color": color}
        dias = [d for d in DIAS if d != "Sábado" or any(clave[2] == d for clave in celdas)]
        franjas = sorted({(desde, hasta) for desde, hasta, _ in celdas})
        filas = [{"desde": d, "hasta": h, "celdas": [celdas.get((d, h, dia)) for dia in dias]} for d, h in franjas]
        return {"dias": dias, "filas": filas, "materias": materias}

    def get_context_data(self, **kwargs):
        return super().get_context_data(inscripciones=self.inscripciones(), cronograma=self.armar_cronograma(), **kwargs)


class InscribirView(AlumnoMixin, ListView):
    """GET: muestra los dictados de la carrera del alumno. POST: lo inscribe en el elegido."""
    context_object_name = "dictados"
    template_name = "inscribir.html"

    def get_queryset(self):
        return (DictadoMateria.objects
                .filter(materia__carrera=self.alumno.carrera,  # solo materias de SU carrera
                        ciclo_lectivo__fecha_fin__gte=date.today())  # y de ciclos que no terminaron
                .select_related("materia", "curso__turno", "ciclo_lectivo")
                .prefetch_related("horarios__modulos", "materia__correlativas"))

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        cumplidas = self.alumno.materias_cumplidas()
        en_curso = [i.dictado_materia for i in self.alumno.inscripciones_en_curso()]
        inscriptas = set(self.alumno.inscripciones.values_list("dictado_materia_id", flat=True))
        cursando = {d.materia_id for d in en_curso}
        for dictado in contexto["dictados"]:
            # El template muestra los motivos y bloquea el botón.
            dictado.ya_inscripto = dictado.id in inscriptas
            dictado.ya_cumplida = dictado.materia_id in cumplidas  # Regular, Aprobación directa, etc.
            dictado.ya_cursando = dictado.materia_id in cursando and not dictado.ya_inscripto
            libre = not (dictado.ya_inscripto or dictado.ya_cumplida or dictado.ya_cursando)
            dictado.faltantes = dictado.materia.faltantes(cumplidas) if libre else []
            dictado.choque = None
            for otro in en_curso if libre else []:
                par = dictado.choque_con(otro) if otro.ciclo_lectivo_id == dictado.ciclo_lectivo_id else None
                if par:
                    dictado.choque = f"{otro.materia.nombre} ({par[1].texto})"
                    break
        return contexto

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


class CorrelativasView(AlumnoMixin, TemplateView):
    """Árbol de la carrera: cada materia cuelga de la que hay que tener antes."""
    template_name = "correlativas.html"
    COLORES = {"cumplida": ("success", "Cumplida"), "cursando": ("primary", "Cursando"),
               "habilitada": ("warning", "Podés inscribirte"), "bloqueada": ("secondary", "Bloqueada")}
    MENSAJES = {"cumplida": "Ya la tenés cumplida. Habilita las materias que cuelgan de ella.",
                "cursando": "La estás cursando. Cuando quedes Regular se habilitan las que siguen.",
                "habilitada": "Cumplís todas las correlativas. Ya podés inscribirte.",
                "bloqueada": "Todavía no cumplís las correlativas."}
    NOTAS = {"cursando": "La estás cursando", "habilitada": "Podés inscribirte ahora",
             "bloqueada": "Primero necesitás sus correlativas"}

    def estado_de(self, materia):
        if materia.id in self.cumplidas:
            return "cumplida"
        if materia.id in self.cursando:
            return "cursando"
        return "bloqueada" if materia.faltantes(self.cumplidas) else "habilitada"

    def previas_pendientes(self, materia):
        """Todo lo que falta antes (directo e indirecto), de la materia más básica a la más avanzada."""
        pendientes, vistas, por_ver = [], set(), list(materia.correlativas.all())
        while por_ver:
            previa = self.por_id[por_ver.pop().id]
            if previa.id not in self.cumplidas and previa.id not in vistas:
                vistas.add(previa.id)
                pendientes.append(previa)
                por_ver.extend(previa.correlativas.all())
        return sorted(pendientes, key=lambda m: (m.nivel, m.nombre))

    def armar_nodo(self, materia, camino=()):
        estado = self.estado_de(materia)
        color, texto = self.COLORES[estado]
        pendientes = self.previas_pendientes(materia) if estado == "bloqueada" else []
        hijos = [self.armar_nodo(h, camino + (materia.id,)) for h in self.hijos_de[materia.id] if h.id not in camino]
        return {
            "materia": materia, "color": color, "texto": texto, "hijos": hijos,
            "faltantes": materia.faltantes(self.cumplidas) if estado == "bloqueada" else [],  # motivo solo si está bloqueada
            "tambien": sorted(materia.correlativas.all(), key=lambda m: (m.nivel, m.nombre))[1:],
            "mensaje": self.MENSAJES[estado],
            # Lo que muestra el panel lateral: "Materia — nota" separado por "|"
            "pendientes": "|".join(f"{m.nombre} — {self.NOTAS[self.estado_de(m)]}" for m in pendientes),
            "puede_inscribirse": estado == "habilitada",
        }

    def get_context_data(self, **kwargs):
        self.cumplidas = self.alumno.materias_cumplidas()
        self.cursando = {i.dictado_materia.materia_id for i in self.inscripciones()
                         if i.ultimo_cambio and not i.ultimo_cambio.condicion.es_condicion_final}
        materias = Materia.objects.filter(carrera=self.alumno.carrera).prefetch_related("correlativas").order_by("nivel", "nombre")
        self.por_id = {m.id: m for m in materias}
        self.hijos_de = {m.id: [] for m in materias}
        for materia in materias:
            correlativas = sorted(materia.correlativas.all(), key=lambda m: (m.nivel, m.nombre))
            if correlativas:  # cuelga de UNA sola (la más básica); las otras se avisan con "También requiere"
                self.hijos_de[correlativas[0].id].append(materia)
        raices = [m for m in materias if not m.correlativas.all()]
        return super().get_context_data(arbol=[self.armar_nodo(m) for m in raices], **kwargs)
