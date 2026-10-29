"""
Panel de administración propio (directores y ejecutivos).

Funciona con un "registro" de entidades: cada entrada de ENTIDADES describe
un modelo (qué columnas mostrar, por qué campos buscar, qué formulario usar).
Con eso, las mismas 4 vistas (listar, crear, editar, eliminar) sirven para
todos los modelos del sistema.
"""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404

from .forms import (
    aplicar_estilos, widgets_modernos,
    AlumnoForm, DocenteForm, AdministradorForm, HorarioForm,
)
from .models import (
    Carrera, Alumno, Materia, Turno, Curso, CicloLectivo, DictadoMateria,
    Modulo, Horario, Docente, Administrador, Condicion, TipoEvaluacion,
    Inscripcion, CambioCondicion, Evaluacion, InstanciaEvaluacion,
)
from .roles import rol_requerido, es_director, ROL_ADMIN


# ---------------------------------------------------------------------------
# Registro de entidades administrables
# columnas: lista de (ruta_del_atributo, título). La ruta acepta puntos: "carrera.sigla"
# ---------------------------------------------------------------------------
ENTIDADES = {
    # --- Personas ---
    "alumnos": {
        "modelo": Alumno, "grupo": "Personas", "icono": "bi-person-badge",
        "titulo": "Alumnos", "singular": "alumno",
        "columnas": [("nombre_completo", "Nombre"), ("documento", "DNI"), ("email", "Email"),
                     ("carrera.sigla", "Carrera"), ("usuario.username", "Usuario")],
        "busqueda": ["nombre_completo", "documento", "email", "usuario__username"],
        "form": AlumnoForm,
    },
    "docentes": {
        "modelo": Docente, "grupo": "Personas", "icono": "bi-person-workspace",
        "titulo": "Docentes", "singular": "docente",
        "columnas": [("legajo", "Legajo"), ("apellido", "Apellido"), ("nombre", "Nombre"),
                     ("usuario.username", "Usuario")],
        "busqueda": ["legajo", "nombre", "apellido", "usuario__username"],
        "form": DocenteForm,
    },
    "administradores": {
        "modelo": Administrador, "grupo": "Personas", "icono": "bi-shield-lock",
        "titulo": "Administradores", "singular": "administrador",
        "columnas": [("apellido", "Apellido"), ("nombre", "Nombre"),
                     ("get_cargo_display", "Cargo"), ("usuario.username", "Usuario")],
        "busqueda": ["nombre", "apellido", "usuario__username"],
        "form": AdministradorForm,
        "solo_director": True,
    },
    # --- Estructura académica ---
    "carreras": {
        "modelo": Carrera, "grupo": "Estructura académica", "icono": "bi-mortarboard",
        "titulo": "Carreras", "singular": "carrera",
        "columnas": [("nombre", "Nombre"), ("sigla", "Sigla")],
        "busqueda": ["nombre", "sigla"],
    },
    "materias": {
        "modelo": Materia, "grupo": "Estructura académica", "icono": "bi-book",
        "titulo": "Materias", "singular": "materia",
        "columnas": [("nombre", "Nombre"), ("sigla", "Sigla"), ("nivel", "Nivel"), ("carrera.sigla", "Carrera")],
        "busqueda": ["nombre", "sigla", "carrera__nombre"],
    },
    "turnos": {
        "modelo": Turno, "grupo": "Estructura académica", "icono": "bi-sun",
        "titulo": "Turnos", "singular": "turno",
        "columnas": [("nombre", "Nombre"), ("descripcion", "Descripción")],
        "busqueda": ["nombre", "descripcion"],
    },
    "cursos": {
        "modelo": Curso, "grupo": "Estructura académica", "icono": "bi-people",
        "titulo": "Cursos", "singular": "curso",
        "columnas": [("nombre", "Nombre"), ("nivel", "Nivel"), ("carrera.sigla", "Carrera"), ("turno", "Turno")],
        "busqueda": ["nombre", "carrera__nombre", "turno__nombre"],
    },
    "ciclos": {
        "modelo": CicloLectivo, "grupo": "Estructura académica", "icono": "bi-calendar-range",
        "titulo": "Ciclos lectivos", "singular": "ciclo lectivo",
        "columnas": [("anio", "Año"), ("descripcion", "Descripción"),
                     ("fecha_inicio", "Inicio"), ("fecha_fin", "Fin")],
        "busqueda": ["descripcion", "anio"],
    },
    # --- Cursado ---
    "dictados": {
        "modelo": DictadoMateria, "grupo": "Cursado", "icono": "bi-easel",
        "titulo": "Dictados de materia", "singular": "dictado",
        "columnas": [("materia.nombre", "Materia"), ("curso", "Curso"),
                     ("ciclo_lectivo.anio", "Ciclo"), ("docentes", "Docentes")],
        "busqueda": ["materia__nombre", "curso__nombre", "docentes__apellido"],
    },
    "modulos": {
        "modelo": Modulo, "grupo": "Cursado", "icono": "bi-clock",
        "titulo": "Módulos horarios", "singular": "módulo",
        "columnas": [("numero", "Número"), ("hora_inicio", "Desde"), ("hora_fin", "Hasta")],
        "busqueda": ["numero"],
    },
    "horarios": {
        "modelo": Horario, "grupo": "Cursado", "icono": "bi-calendar-week",
        "titulo": "Horarios", "singular": "horario",
        "columnas": [("dia", "Día"), ("dictado_materia", "Dictado"), ("modulos", "Módulos")],
        "busqueda": ["dia", "dictado_materia__materia__nombre"],
        "form": HorarioForm,
    },
    "inscripciones": {
        "modelo": Inscripcion, "grupo": "Cursado", "icono": "bi-journal-check",
        "titulo": "Inscripciones", "singular": "inscripción",
        "columnas": [("codigo_inscripcion", "Código"), ("alumno.nombre_completo", "Alumno"),
                     ("dictado_materia", "Dictado"), ("condicion_actual", "Condición"),
                     ("fecha_inscripcion", "Fecha")],
        "busqueda": ["codigo_inscripcion", "alumno__nombre_completo", "dictado_materia__materia__nombre"],
    },
    # --- Calificaciones ---
    "instancias-evaluacion": {
        "modelo": InstanciaEvaluacion, "grupo": "Calificaciones", "icono": "bi-table",
        "titulo": "Columnas de evaluación", "singular": "columna de evaluación",
        "columnas": [("dictado_materia", "Dictado"), ("titulo", "Evaluación"), ("tipo_evaluacion", "Tipo"),
                     ("fecha", "Fecha"), ("para_todos", "Para todos")],
        "busqueda": ["nombre", "tipo_evaluacion__nombre", "dictado_materia__materia__nombre"],
    },
    "evaluaciones": {
        "modelo": Evaluacion, "grupo": "Calificaciones", "icono": "bi-pencil-square",
        "titulo": "Evaluaciones", "singular": "evaluación",
        "columnas": [("inscripcion.alumno.nombre_completo", "Alumno"), ("instancia.titulo", "Evaluación"),
                     ("tipo_evaluacion", "Tipo"), ("valor", "Nota"), ("fecha_evaluacion", "Fecha"), ("docente", "Docente")],
        "busqueda": ["inscripcion__alumno__nombre_completo", "tipo_evaluacion__nombre"],
    },
    "cambios-condicion": {
        "modelo": CambioCondicion, "grupo": "Calificaciones", "icono": "bi-arrow-left-right",
        "titulo": "Cambios de condición", "singular": "cambio de condición",
        "columnas": [("inscripcion.alumno.nombre_completo", "Alumno"), ("condicion", "Condición"),
                     ("fecha_hora", "Fecha"), ("docente", "Docente")],
        "busqueda": ["inscripcion__alumno__nombre_completo", "condicion__nombre"],
    },
    "condiciones": {
        "modelo": Condicion, "grupo": "Calificaciones", "icono": "bi-flag",
        "titulo": "Condiciones", "singular": "condición",
        "columnas": [("nombre", "Nombre"), ("descripcion", "Descripción"), ("es_condicion_final", "Final")],
        "busqueda": ["nombre"],
    },
    "tipos-evaluacion": {
        "modelo": TipoEvaluacion, "grupo": "Calificaciones", "icono": "bi-ui-checks",
        "titulo": "Tipos de evaluación", "singular": "tipo de evaluación",
        "columnas": [("nombre", "Nombre"), ("descripcion", "Descripción")],
        "busqueda": ["nombre"],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _menu(request):
    """Arma el menú lateral agrupado, ocultando lo que el usuario no puede ver."""
    grupos = {}
    director = es_director(request.user)
    for clave, conf in ENTIDADES.items():
        if conf.get("solo_director") and not director:
            continue
        grupos.setdefault(conf["grupo"], []).append({"clave": clave, **conf})
    return grupos


def _obtener_entidad(request, clave):
    conf = ENTIDADES.get(clave)
    if conf is None:
        raise Http404("Sección inexistente")
    if conf.get("solo_director") and not es_director(request.user):
        return None
    return conf


def _valor(obj, ruta):
    """Resuelve 'carrera.sigla', métodos (get_cargo_display) y relaciones muchos-a-muchos."""
    valor = obj
    for parte in ruta.split("."):
        if valor is None:
            return None
        valor = getattr(valor, parte, None)
        if callable(valor) and not hasattr(valor, "all"):
            valor = valor()
    if hasattr(valor, "all"):  # ManyToMany
        return ", ".join(str(v) for v in valor.all()) or None
    return valor


def _form_class(conf):
    return conf.get("form") or modelform_factory(
        conf["modelo"], fields="__all__", formfield_callback=widgets_modernos
    )


def _contexto(request, **extra):
    return {"menu": _menu(request), **extra}


def _sin_permiso(request):
    messages.error(request, "Solo un director puede gestionar administradores.")
    return redirect("admin_dashboard")


# ---------------------------------------------------------------------------
# Vistas
# ---------------------------------------------------------------------------
@rol_requerido(ROL_ADMIN)
def admin_dashboard(request):
    tarjetas = []
    for clave in ["alumnos", "docentes", "carreras", "materias", "cursos", "turnos", "dictados", "inscripciones"]:
        conf = ENTIDADES[clave]
        tarjetas.append({
            "clave": clave, "titulo": conf["titulo"], "icono": conf["icono"],
            "cantidad": conf["modelo"].objects.count(),
        })
    ultimas = (Inscripcion.objects
               .select_related("alumno", "dictado_materia__materia")
               .order_by("-fecha_inscripcion", "-id")[:6])
    return render(request, "UTN/admin_panel/dashboard.html", _contexto(
        request, tarjetas=tarjetas, ultimas_inscripciones=ultimas, seccion_activa="dashboard",
    ))


@rol_requerido(ROL_ADMIN)
def admin_lista(request, entidad):
    conf = _obtener_entidad(request, entidad)
    if conf is None:
        return _sin_permiso(request)

    qs = conf["modelo"].objects.all().order_by("-id")
    q = request.GET.get("q", "").strip()
    if q:
        filtro = Q()
        for campo in conf["busqueda"]:
            filtro |= Q(**{f"{campo}__icontains": q})
        qs = qs.filter(filtro).distinct()

    pagina = Paginator(qs, 15).get_page(request.GET.get("page"))
    filas = [{"obj": obj, "valores": [_valor(obj, ruta) for ruta, _ in conf["columnas"]]} for obj in pagina]

    return render(request, "UTN/admin_panel/lista.html", _contexto(
        request, conf=conf, entidad=entidad, filas=filas, pagina=pagina, q=q,
        total=qs.count(), seccion_activa=entidad,
    ))


@rol_requerido(ROL_ADMIN)
def admin_crear(request, entidad):
    return _formulario(request, entidad, pk=None)


@rol_requerido(ROL_ADMIN)
def admin_editar(request, entidad, pk):
    return _formulario(request, entidad, pk=pk)


def _formulario(request, entidad, pk):
    conf = _obtener_entidad(request, entidad)
    if conf is None:
        return _sin_permiso(request)

    instancia = get_object_or_404(conf["modelo"], pk=pk) if pk else None
    FormClass = _form_class(conf)
    form = FormClass(request.POST or None, instance=instancia)
    aplicar_estilos(form)

    if request.method == "POST" and form.is_valid():
        obj = form.save()
        accion = "actualizado" if pk else "creado"
        messages.success(request, f"{conf['singular'].capitalize()} «{obj}» {accion} correctamente.")
        if "guardar_y_otro" in request.POST:
            return redirect("admin_crear", entidad=entidad)
        return redirect("admin_lista", entidad=entidad)

    return render(request, "UTN/admin_panel/form.html", _contexto(
        request, conf=conf, entidad=entidad, form=form, instancia=instancia, seccion_activa=entidad,
    ))


@rol_requerido(ROL_ADMIN)
def admin_eliminar(request, entidad, pk):
    conf = _obtener_entidad(request, entidad)
    if conf is None:
        return _sin_permiso(request)
    if request.method != "POST":
        return redirect("admin_lista", entidad=entidad)

    obj = get_object_or_404(conf["modelo"], pk=pk)
    if getattr(obj, "usuario_id", None) == request.user.id:
        messages.error(request, "No podés eliminar tu propio usuario.")
        return redirect("admin_lista", entidad=entidad)

    nombre = str(obj)
    try:
        usuario = getattr(obj, "usuario", None) if hasattr(obj, "usuario_id") else None
        obj.delete()
        if usuario is not None:
            usuario.delete()  # borra también la cuenta para iniciar sesión
        messages.success(request, f"«{nombre}» se eliminó correctamente.")
    except ProtectedError as e:
        usados = sorted({str(o._meta.verbose_name_plural) for o in e.protected_objects})
        messages.error(
            request,
            f"No se puede eliminar «{nombre}» porque está siendo usado en: {', '.join(usados)}. "
            "Primero eliminá o modificá esos registros.",
        )
    return redirect("admin_lista", entidad=entidad)
