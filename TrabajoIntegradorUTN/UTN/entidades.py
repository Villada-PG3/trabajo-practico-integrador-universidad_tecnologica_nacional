"""
Registro de las entidades que se administran desde el panel de administración.

Cada entrada describe un modelo: qué columnas mostrar, por qué campos buscar y, si hace falta,
qué formulario usar. Las mismas 4 vistas genéricas (views_admin.py) sirven para todas.
En `columnas`, la ruta acepta puntos: "carrera.sigla".
"""
from .forms import AlumnoForm, DocenteForm, AdministradorForm, HorarioForm
from .models import (
    Carrera, Alumno, Materia, Turno, Curso, CicloLectivo, DictadoMateria,
    Modulo, Horario, Docente, Administrador, Condicion, TipoEvaluacion,
    Inscripcion, CambioCondicion, Evaluacion, InstanciaEvaluacion,
)
from .roles import es_director

PERSONAS, ESTRUCTURA, CURSADO, CALIFICACIONES = "Personas", "Estructura académica", "Cursado", "Calificaciones"

ENTIDADES = {
    # --- Personas ---
    "alumnos": {
        "modelo": Alumno, "grupo": PERSONAS, "icono": "bi-person-badge", "titulo": "Alumnos", "singular": "alumno",
        "columnas": [("nombre_completo", "Nombre"), ("documento", "DNI"), ("email", "Email"),
                     ("carrera.sigla", "Carrera"), ("usuario.username", "Usuario")],
        "busqueda": ["nombre_completo", "documento", "email", "usuario__username"],
        "form": AlumnoForm,
    },
    "docentes": {
        "modelo": Docente, "grupo": PERSONAS, "icono": "bi-person-workspace", "titulo": "Docentes", "singular": "docente",
        "columnas": [("legajo", "Legajo"), ("apellido", "Apellido"), ("nombre", "Nombre"), ("usuario.username", "Usuario")],
        "busqueda": ["legajo", "nombre", "apellido", "usuario__username"],
        "form": DocenteForm,
    },
    "administradores": {
        "modelo": Administrador, "grupo": PERSONAS, "icono": "bi-shield-lock", "titulo": "Administradores",
        "singular": "administrador",
        "columnas": [("apellido", "Apellido"), ("nombre", "Nombre"),
                     ("get_cargo_display", "Cargo"), ("usuario.username", "Usuario")],
        "busqueda": ["nombre", "apellido", "usuario__username"],
        "form": AdministradorForm,
        "solo_director": True,
    },
    # --- Estructura académica ---
    "carreras": {
        "modelo": Carrera, "grupo": ESTRUCTURA, "icono": "bi-mortarboard", "titulo": "Carreras", "singular": "carrera",
        "columnas": [("nombre", "Nombre"), ("sigla", "Sigla")],
        "busqueda": ["nombre", "sigla"],
    },
    "materias": {
        "modelo": Materia, "grupo": ESTRUCTURA, "icono": "bi-book", "titulo": "Materias", "singular": "materia",
        "columnas": [("nombre", "Nombre"), ("sigla", "Sigla"), ("nivel", "Nivel"), ("carrera.sigla", "Carrera")],
        "busqueda": ["nombre", "sigla", "carrera__nombre"],
    },
    "turnos": {
        "modelo": Turno, "grupo": ESTRUCTURA, "icono": "bi-sun", "titulo": "Turnos", "singular": "turno",
        "columnas": [("nombre", "Nombre"), ("descripcion", "Descripción")],
        "busqueda": ["nombre", "descripcion"],
    },
    "cursos": {
        "modelo": Curso, "grupo": ESTRUCTURA, "icono": "bi-people", "titulo": "Cursos", "singular": "curso",
        "columnas": [("nombre", "Nombre"), ("nivel", "Nivel"), ("carrera.sigla", "Carrera"), ("turno", "Turno")],
        "busqueda": ["nombre", "carrera__nombre", "turno__nombre"],
    },
    "ciclos": {
        "modelo": CicloLectivo, "grupo": ESTRUCTURA, "icono": "bi-calendar-range", "titulo": "Ciclos lectivos",
        "singular": "ciclo lectivo",
        "columnas": [("anio", "Año"), ("descripcion", "Descripción"), ("fecha_inicio", "Inicio"), ("fecha_fin", "Fin")],
        "busqueda": ["descripcion", "anio"],
    },
    # --- Cursado ---
    "dictados": {
        "modelo": DictadoMateria, "grupo": CURSADO, "icono": "bi-easel", "titulo": "Dictados de materia",
        "singular": "dictado",
        "columnas": [("materia.nombre", "Materia"), ("curso", "Curso"),
                     ("ciclo_lectivo.anio", "Ciclo"), ("docentes", "Docentes")],
        "busqueda": ["materia__nombre", "curso__nombre", "docentes__apellido"],
    },
    "modulos": {
        "modelo": Modulo, "grupo": CURSADO, "icono": "bi-clock", "titulo": "Módulos horarios", "singular": "módulo",
        "columnas": [("numero", "Número"), ("hora_inicio", "Desde"), ("hora_fin", "Hasta")],
        "busqueda": ["numero"],
    },
    "horarios": {
        "modelo": Horario, "grupo": CURSADO, "icono": "bi-calendar-week", "titulo": "Horarios", "singular": "horario",
        "columnas": [("dia", "Día"), ("dictado_materia", "Dictado"), ("modulos", "Módulos")],
        "busqueda": ["dia", "dictado_materia__materia__nombre"],
        "form": HorarioForm,
    },
    "inscripciones": {
        "modelo": Inscripcion, "grupo": CURSADO, "icono": "bi-journal-check", "titulo": "Inscripciones",
        "singular": "inscripción",
        "columnas": [("codigo_inscripcion", "Código"), ("alumno.nombre_completo", "Alumno"),
                     ("dictado_materia", "Dictado"), ("condicion_actual", "Condición"), ("fecha_inscripcion", "Fecha")],
        "busqueda": ["codigo_inscripcion", "alumno__nombre_completo", "dictado_materia__materia__nombre"],
    },
    # --- Calificaciones ---
    "instancias-evaluacion": {
        "modelo": InstanciaEvaluacion, "grupo": CALIFICACIONES, "icono": "bi-table", "titulo": "Columnas de evaluación",
        "singular": "columna de evaluación",
        "columnas": [("dictado_materia", "Dictado"), ("titulo", "Evaluación"), ("tipo_evaluacion", "Tipo"),
                     ("fecha", "Fecha"), ("para_todos", "Para todos")],
        "busqueda": ["nombre", "tipo_evaluacion__nombre", "dictado_materia__materia__nombre"],
    },
    "evaluaciones": {
        "modelo": Evaluacion, "grupo": CALIFICACIONES, "icono": "bi-pencil-square", "titulo": "Evaluaciones",
        "singular": "evaluación",
        "columnas": [("inscripcion.alumno.nombre_completo", "Alumno"), ("instancia.titulo", "Evaluación"),
                     ("valor", "Nota"), ("instancia.fecha", "Fecha"), ("docente", "Docente")],
        "busqueda": ["inscripcion__alumno__nombre_completo", "instancia__nombre", "instancia__tipo_evaluacion__nombre"],
    },
    "cambios-condicion": {
        "modelo": CambioCondicion, "grupo": CALIFICACIONES, "icono": "bi-arrow-left-right",
        "titulo": "Cambios de condición", "singular": "cambio de condición",
        "columnas": [("inscripcion.alumno.nombre_completo", "Alumno"), ("condicion", "Condición"),
                     ("fecha_hora", "Fecha"), ("docente", "Docente")],
        "busqueda": ["inscripcion__alumno__nombre_completo", "condicion__nombre"],
    },
    "condiciones": {
        "modelo": Condicion, "grupo": CALIFICACIONES, "icono": "bi-flag", "titulo": "Condiciones", "singular": "condición",
        "columnas": [("nombre", "Nombre"), ("descripcion", "Descripción"), ("es_condicion_final", "Final")],
        "busqueda": ["nombre"],
    },
    "tipos-evaluacion": {
        "modelo": TipoEvaluacion, "grupo": CALIFICACIONES, "icono": "bi-ui-checks", "titulo": "Tipos de evaluación",
        "singular": "tipo de evaluación",
        "columnas": [("nombre", "Nombre"), ("descripcion", "Descripción")],
        "busqueda": ["nombre"],
    },
}


def menu_para(user):
    """Menú lateral agrupado: {grupo: [entidades]}, sin lo que el usuario no puede ver."""
    grupos = {}
    for clave, conf in ENTIDADES.items():
        if conf.get("solo_director") and not es_director(user):
            continue
        grupos.setdefault(conf["grupo"], []).append({"clave": clave, **conf})
    return grupos
