from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views, views_admin, views_docente

app_name = "utn"

urlpatterns = [
    path("", views.HomeView.as_view(), name="landing"),

    # Login único + redirección según el rol
    path("login/", views.LoginUnificadoView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("mi-panel/", views.redireccion_panel, name="redireccion_panel"),
    path("mi-cuenta/", views.CuentaUsuarioView.as_view(), name="mi_cuenta"),
    path("mi-cuenta/contrasena/", views.CuentaPasswordView.as_view(), name="mi_cuenta_password"),

    # Panel del alumno
    path("alumno/<int:pk>/", views.PanelAlumnoView.as_view(), name="panel_alumno"),
    path("alumno/<int:pk>/inscribir/", views.InscribirView.as_view(), name="inscribir_materia"),
    path("alumno/<int:pk>/correlativas/", views.CorrelativasView.as_view(), name="correlativas"),
    path("alumno/<int:pk>/reporte-regulares/", views.ReporteRegularesView.as_view(), name="reporte_regulares"),

    # Panel del docente
    path("docentes/panel/", views_docente.PanelDocenteView.as_view(), name="panel_docente"),

    # Panel de administración (directores y ejecutivos): 4 rutas por tabla
    path("administracion/", views_admin.DashboardView.as_view(), name="admin_dashboard"),

    path("administracion/alumnos/", views_admin.AlumnoLista.as_view(), name="alumno_lista"),
    path("administracion/alumnos/nuevo/", views_admin.AlumnoNuevo.as_view(), name="alumno_nuevo"),
    path("administracion/alumnos/<int:pk>/editar/", views_admin.AlumnoEditar.as_view(), name="alumno_editar"),
    path("administracion/alumnos/<int:pk>/eliminar/", views_admin.AlumnoEliminar.as_view(), name="alumno_eliminar"),

    path("administracion/docentes/", views_admin.DocenteLista.as_view(), name="docente_lista"),
    path("administracion/docentes/nuevo/", views_admin.DocenteNuevo.as_view(), name="docente_nuevo"),
    path("administracion/docentes/<int:pk>/editar/", views_admin.DocenteEditar.as_view(), name="docente_editar"),
    path("administracion/docentes/<int:pk>/eliminar/", views_admin.DocenteEliminar.as_view(), name="docente_eliminar"),

    path("administracion/administradores/", views_admin.AdministradorLista.as_view(), name="administrador_lista"),
    path("administracion/administradores/nuevo/", views_admin.AdministradorNuevo.as_view(), name="administrador_nuevo"),
    path("administracion/administradores/<int:pk>/editar/", views_admin.AdministradorEditar.as_view(), name="administrador_editar"),
    path("administracion/administradores/<int:pk>/eliminar/", views_admin.AdministradorEliminar.as_view(), name="administrador_eliminar"),

    path("administracion/carreras/", views_admin.CarreraLista.as_view(), name="carrera_lista"),
    path("administracion/carreras/nuevo/", views_admin.CarreraNuevo.as_view(), name="carrera_nuevo"),
    path("administracion/carreras/<int:pk>/editar/", views_admin.CarreraEditar.as_view(), name="carrera_editar"),
    path("administracion/carreras/<int:pk>/eliminar/", views_admin.CarreraEliminar.as_view(), name="carrera_eliminar"),

    path("administracion/materias/", views_admin.MateriaLista.as_view(), name="materia_lista"),
    path("administracion/materias/nuevo/", views_admin.MateriaNuevo.as_view(), name="materia_nuevo"),
    path("administracion/materias/<int:pk>/editar/", views_admin.MateriaEditar.as_view(), name="materia_editar"),
    path("administracion/materias/<int:pk>/eliminar/", views_admin.MateriaEliminar.as_view(), name="materia_eliminar"),

    path("administracion/cursos/", views_admin.CursoLista.as_view(), name="curso_lista"),
    path("administracion/cursos/nuevo/", views_admin.CursoNuevo.as_view(), name="curso_nuevo"),
    path("administracion/cursos/<int:pk>/editar/", views_admin.CursoEditar.as_view(), name="curso_editar"),
    path("administracion/cursos/<int:pk>/eliminar/", views_admin.CursoEliminar.as_view(), name="curso_eliminar"),

    path("administracion/dictados/", views_admin.DictadoLista.as_view(), name="dictado_lista"),
    path("administracion/dictados/nuevo/", views_admin.DictadoNuevo.as_view(), name="dictado_nuevo"),
    path("administracion/dictados/<int:pk>/editar/", views_admin.DictadoEditar.as_view(), name="dictado_editar"),
    path("administracion/dictados/<int:pk>/eliminar/", views_admin.DictadoEliminar.as_view(), name="dictado_eliminar"),

    path("administracion/horarios/", views_admin.HorarioLista.as_view(), name="horario_lista"),
    path("administracion/horarios/nuevo/", views_admin.HorarioNuevo.as_view(), name="horario_nuevo"),
    path("administracion/horarios/<int:pk>/editar/", views_admin.HorarioEditar.as_view(), name="horario_editar"),
    path("administracion/horarios/<int:pk>/eliminar/", views_admin.HorarioEliminar.as_view(), name="horario_eliminar"),

    path("administracion/inscripciones/", views_admin.InscripcionLista.as_view(), name="inscripcion_lista"),
    path("administracion/inscripciones/nuevo/", views_admin.InscripcionNuevo.as_view(), name="inscripcion_nuevo"),
    path("administracion/inscripciones/<int:pk>/editar/", views_admin.InscripcionEditar.as_view(), name="inscripcion_editar"),
    path("administracion/inscripciones/<int:pk>/eliminar/", views_admin.InscripcionEliminar.as_view(), name="inscripcion_eliminar"),
]
