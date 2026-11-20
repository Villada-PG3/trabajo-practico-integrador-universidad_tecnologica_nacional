from .roles import obtener_rol, es_director, ROL_ADMIN

# Menú lateral del panel de administración: {grupo: [(nombre de la ruta, título, ícono)]}
MENU = {
    "Personas": [
        ("utn:alumno_lista", "Alumnos", "bi-person-badge"),
        ("utn:docente_lista", "Docentes", "bi-person-workspace"),
        ("utn:administrador_lista", "Administradores", "bi-shield-lock"),
    ],
    "Estructura académica": [
        ("utn:carrera_lista", "Carreras", "bi-mortarboard"),
        ("utn:materia_lista", "Materias", "bi-book"),
        ("utn:curso_lista", "Cursos", "bi-people"),
    ],
    "Cursado": [
        ("utn:dictado_lista", "Dictados de materia", "bi-easel"),
        ("utn:horario_lista", "Horarios", "bi-calendar-week"),
        ("utn:inscripcion_lista", "Inscripciones", "bi-journal-check"),
    ],
}


def panel(request):
    """
    Datos disponibles en TODOS los templates:
      rol, es_director          -> para mostrar u ocultar cosas según quién es el usuario
      base_template, menu       -> el administrador usa el diseño con menú lateral
    """
    rol = obtener_rol(request.user)
    contexto = {"rol": rol, "es_director": es_director(request.user), "base_template": "base.html"}
    if rol == ROL_ADMIN:
        contexto["base_template"] = "admin_base.html"
        contexto["menu"] = {}
        for grupo, items in MENU.items():
            # Los administradores solo los gestiona un director
            contexto["menu"][grupo] = [i for i in items if contexto["es_director"] or i[0] != "utn:administrador_lista"]
    return contexto
