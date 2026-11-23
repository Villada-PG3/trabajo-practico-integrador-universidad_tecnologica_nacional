from datetime import date

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from .forms import LoginForm, CuentaUsuarioForm, CambiarPasswordForm
from .models import Alumno, Carrera, DictadoMateria, Inscripcion, Materia, Turno
from .roles import obtener_rol, RolRequeridoMixin, ROL_ADMIN, ROL_DOCENTE, ROL_ALUMNO


# ---------------------------------------------------------------------------
# Página de inicio
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


def icono_de(nombre):
    """El ícono de la carrera según las palabras que tiene su nombre."""
    nombre = nombre.lower()
    for palabra, icono in ICONOS_CARRERA:
        if palabra in nombre:
            return icono
    return "bi-mortarboard"


class HomeView(TemplateView):
    template_name = "landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["carreras"] = [{"nombre": c.nombre, "icono": icono_de(c.nombre)} for c in Carrera.objects.all()]
        context["fotos"] = FOTOS
        context["noticias"] = NOTICIAS
        return context


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
# Cronograma compartido (alumnos y docentes)
# ---------------------------------------------------------------------------
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
COLORES_CRONOGRAMA = ["primary", "success", "warning", "info", "danger", "secondary"]  # clases text-bg-* de Bootstrap


def armar_cronograma(dictados):
    """Grilla semanal a partir de una lista de DictadoMateria (sirve para alumnos y docentes)."""
    celdas = {}     # (hora de inicio, hora de fin, día) -> lo que se dibuja en esa celda
    materias = []   # las referencias de colores
    for n, dictado in enumerate(dictados):
        color = COLORES_CRONOGRAMA[n % len(COLORES_CRONOGRAMA)]
        materias.append({"dictado": dictado, "color": color})
        for horario in dictado.horarios.all():
            for modulo in horario.modulos.all():
                celdas[(modulo.hora_inicio, modulo.hora_fin, horario.dia)] = {
                    "sigla": dictado.materia.sigla,
                    "curso": dictado.curso.nombre,
                    "color": color,
                }

    dias = []
    for dia in DIAS:
        if dia != "Sábado" or any(clave[2] == "Sábado" for clave in celdas):  # el sábado solo si hay clases
            dias.append(dia)

    franjas = sorted({(desde, hasta) for desde, hasta, dia in celdas})
    filas = []
    for desde, hasta in franjas:
        filas.append({"desde": desde, "hasta": hasta, "celdas": [celdas.get((desde, hasta, dia)) for dia in dias]})
    return {"dias": dias, "filas": filas, "materias": materias}


class CronogramaCuentaMixin:
    """Inyecta el cronograma en Mi Cuenta tanto para alumnos como para docentes."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rol = obtener_rol(self.request.user)
        if rol == ROL_ALUMNO:
            dictados = [i.dictado_materia for i in self.request.user.alumno.inscripciones_en_curso()]
            context["cronograma"] = armar_cronograma(dictados)
        elif rol == ROL_DOCENTE:
            dictados = (
                self.request.user.docente.dictados
                .select_related("materia", "curso", "ciclo_lectivo")
                .prefetch_related("horarios__modulos")
            )
            context["cronograma"] = armar_cronograma(dictados)
        return context
    
# ---------------------------------------------------------------------------
# Mi cuenta: cambiar usuario y contraseña (alumnos, docentes y administradores)
# ---------------------------------------------------------------------------
class CuentaUsuarioView(LoginRequiredMixin, CronogramaCuentaMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = CuentaUsuarioForm
    template_name = "mi_cuenta.html"
    success_url = reverse_lazy("utn:mi_cuenta")
    success_message = "Listo, tu nombre de usuario se actualizó."

    def get_object(self, queryset=None):
        return self.request.user  # siempre edita al usuario logueado, nunca a otro


class CuentaPasswordView(CronogramaCuentaMixin, SuccessMessageMixin, PasswordChangeView):
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

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and obtener_rol(request.user) in self.roles:
            self.alumno = get_object_or_404(Alumno.objects.select_related("carrera"), pk=kwargs["pk"])
            if obtener_rol(request.user) != ROL_ADMIN and self.alumno.usuario_id != request.user.id:
                raise PermissionDenied  # 403: es el panel de otro alumno
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(alumno=self.alumno, **kwargs)

    def inscripciones(self):
        # select_related / prefetch_related traen lo relacionado de una vez (evitan una consulta por fila)
        return (self.alumno.inscripciones
                .select_related("dictado_materia__materia", "dictado_materia__curso", "dictado_materia__ciclo_lectivo")
                .prefetch_related("evaluaciones__instancia__tipo_evaluacion", "historial_condiciones__condicion"))


class PanelAlumnoView(AlumnoMixin, DetailView):
    model = Alumno
    template_name = "panel_alumno.html"

    def get_object(self, queryset=None):
        return self.alumno

    def get_context_data(self, **kwargs):
        dictados = [i.dictado_materia for i in self.alumno.inscripciones_en_curso()]
        return super().get_context_data(
            inscripciones=self.inscripciones(),
            cronograma=armar_cronograma(dictados),
            **kwargs
        )


class InscribirView(AlumnoMixin, ListView):
    """GET: muestra los dictados de la carrera del alumno (filtrables por materia y turno). POST: lo inscribe."""
    context_object_name = "dictados"
    template_name = "inscribir.html"

    def get_queryset(self):
        qs = (DictadoMateria.objects
              .filter(materia__carrera=self.alumno.carrera,
                      ciclo_lectivo__fecha_fin__gte=date.today())
              .select_related("materia", "curso__turno", "ciclo_lectivo")
              .prefetch_related("horarios__modulos", "materia__correlativas"))
        materia_id = self.request.GET.get("materia")
        turno_id = self.request.GET.get("turno")
        if materia_id and materia_id.isdigit():
            qs = qs.filter(materia_id=materia_id)
        if turno_id and turno_id.isdigit():
            qs = qs.filter(curso__turno_id=turno_id)
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["materias"] = Materia.objects.filter(carrera=self.alumno.carrera).order_by("nivel", "nombre")
        contexto["turnos"] = Turno.objects.all()
        contexto["materia_sel"] = self.request.GET.get("materia", "")
        contexto["turno_sel"] = self.request.GET.get("turno", "")

        cumplidas = self.alumno.materias_cumplidas()
        en_curso = [i.dictado_materia for i in self.alumno.inscripciones_en_curso()]
        inscriptas = set(self.alumno.inscripciones.values_list("dictado_materia_id", flat=True))
        cursando = {d.materia_id for d in en_curso}
        for dictado in contexto["dictados"]:
            dictado.ya_inscripto = dictado.id in inscriptas
            dictado.ya_cumplida = dictado.materia_id in cumplidas
            dictado.ya_cursando = dictado.materia_id in cursando and not dictado.ya_inscripto
            dictado.faltantes = []
            dictado.choque = None
            if dictado.ya_inscripto or dictado.ya_cumplida or dictado.ya_cursando:
                continue
            dictado.faltantes = dictado.materia.faltantes(cumplidas)
            for otro in en_curso:
                if otro.ciclo_lectivo_id == dictado.ciclo_lectivo_id:
                    par = dictado.choque_con(otro)
                    if par:
                        dictado.choque = f"{otro.materia.nombre} ({par[1].texto})"
                        break
        return contexto

    def post(self, request, *args, **kwargs):
        dictado = get_object_or_404(self.get_queryset(), pk=request.POST.get("dictado_id"))
        inscripcion = Inscripcion(alumno=self.alumno, dictado_materia=dictado)
        try:
            inscripcion.full_clean()  # corre las reglas de Inscripcion.clean() (models.py)
        except ValidationError as error:
            messages.warning(request, " ".join(error.messages))
            return redirect("utn:inscribir_materia", pk=self.alumno.pk)
        inscripcion.save()

        messages.success(request, f"¡Inscripción exitosa! Tu código es: {inscripcion.codigo_inscripcion}")
        return redirect("utn:panel_alumno", pk=self.alumno.pk)


class ReporteRegularesView(AlumnoMixin, ListView):
    context_object_name = "regulares"
    template_name = "reporte_regulares.html"

    def get_queryset(self):
        return [i for i in self.inscripciones() if i.condicion_actual == "Regular"]


def por_nivel(materias):
    """Las materias ordenadas de la más básica a la más avanzada (primero por nivel, después por nombre)."""
    return sorted(materias, key=lambda materia: (materia.nivel, materia.nombre))


class CorrelativasView(AlumnoMixin, TemplateView):
    """Árbol de la carrera: cada materia cuelga de la que hay que tener antes."""
    template_name = "correlativas.html"
    COLORES = {"cumplida": ("success", "Cumplida"), "cursando": ("primary", "Cursando"),
               "habilitada": ("warning", "Podés inscribirte"), "bloqueada": ("secondary", "Bloqueada")}
    MENSAJES = {"cumplida": "Ya la tenés cumplida. Habilita las materias que cuelgan de ella.",
                "cursando": "La estás cursando. Cuando quedes Regular se habilitan las que siguen.",
                "habilitada": "Cumplís todas las correlativas. Ya podés inscribirte.",
                "bloqueada": "Todavía no cumplís las correlativas."}
    NOTAS = {"cumplida": "Ya la tenés", "cursando": "La estás cursando", "habilitada": "Podés inscribirte ahora",
             "bloqueada": "Primero necesitás sus correlativas"}

    def estado_de(self, materia):
        if materia.id in self.cumplidas:
            return "cumplida"
        if materia.id in self.cursando:
            return "cursando"
        if materia.faltantes(self.cumplidas):
            return "bloqueada"
        return "habilitada"

    def previas_pendientes(self, materia):
        """Todo lo que falta antes (directo e indirecto) de una materia bloqueada."""
        pendientes, por_ver = [], list(materia.correlativas.all())
        while por_ver:
            previa = self.materias[por_ver.pop().id]  # la versión con las correlativas ya traídas
            if previa.id not in self.cumplidas and previa not in pendientes:
                pendientes.append(previa)
                por_ver.extend(previa.correlativas.all())
        return por_nivel(pendientes)

    def armar_nodo(self, materia, camino=()):
        """Un nodo del árbol: la materia, su estado y las materias que cuelgan de ella (recursivo)."""
        estado = self.estado_de(materia)
        color, texto = self.COLORES[estado]
        faltantes, pendientes = [], []
        if estado == "bloqueada":
            faltantes = materia.faltantes(self.cumplidas)
            pendientes = self.previas_pendientes(materia)
        hijos = []
        for hija in self.hijos_de[materia.id]:
            if hija.id not in camino:  # defensa contra ciclos
                hijos.append(self.armar_nodo(hija, camino + (materia.id,)))
        return {
            "materia": materia, "color": color, "texto": texto, "hijos": hijos,
            "faltantes": faltantes,
            "tambien": por_nivel(materia.correlativas.all())[1:],  # las demás correlativas (la primera es de la que cuelga)
            "mensaje": self.MENSAJES[estado],
            # Lo que muestra el panel lateral: "Materia — nota" separado por "|"
            "pendientes": "|".join(f"{m.nombre} — {self.NOTAS[self.estado_de(m)]}" for m in pendientes),
            "puede_inscribirse": estado == "habilitada",
        }

    def get_context_data(self, **kwargs):
        self.cumplidas = self.alumno.materias_cumplidas()
        self.cursando = {i.dictado_materia.materia_id for i in self.alumno.inscripciones_en_curso()}
        materias = Materia.objects.filter(carrera=self.alumno.carrera).prefetch_related("correlativas").order_by("nivel", "nombre")
        self.materias = {m.id: m for m in materias}
        self.hijos_de = {m.id: [] for m in materias}  # materia -> las que cuelgan de ella
        raices = []
        for materia in materias:
            correlativas = por_nivel(materia.correlativas.all())
            if correlativas:  # cuelga de UNA sola (la más básica); las otras se avisan con "También requiere"
                self.hijos_de[correlativas[0].id].append(materia)
            else:
                raices.append(materia)
        return super().get_context_data(arbol=[self.armar_nodo(m) for m in raices], **kwargs)
