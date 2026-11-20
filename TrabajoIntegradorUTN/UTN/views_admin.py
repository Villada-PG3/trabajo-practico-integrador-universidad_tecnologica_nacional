"""
Panel de administración propio (directores y ejecutivos).

Cada tabla tiene sus 4 vistas (lista, nuevo, editar, eliminar), como en las clases de CRUD.
Para no repetir código, las 4 heredan de una vista base (AdminLista, AdminNuevo...) y de una
clase con los datos de la tabla (Alumnos, Docentes...): el modelo, el formulario, el título y el ícono.
Las tablas que no están acá (turnos, ciclos, módulos, calificaciones...) se gestionan desde /admin/.
"""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .forms import (AdministradorForm, AlumnoForm, CarreraForm, CursoForm, DictadoForm, DocenteForm,
                    HorarioForm, InscripcionForm, MateriaForm)
from .models import (Administrador, Alumno, Carrera, Curso, DictadoMateria, Docente, Horario,
                     Inscripcion, Materia, Turno)
from .roles import RolRequeridoMixin, ROL_ADMIN


# ---------------------------------------------------------------------------
# Vistas base: lo que comparten todas las tablas
# ---------------------------------------------------------------------------
class AdminMixin(RolRequeridoMixin):
    """Solo administradores."""
    roles = (ROL_ADMIN,)


class TablaMixin(AdminMixin):
    """Lo común de las vistas de una tabla. Cada tabla define `prefijo` ("alumno" -> rutas utn:alumno_lista, utn:alumno_nuevo...)."""

    def get_context_data(self, **kwargs):
        url_lista = f"utn:{self.prefijo}_lista"
        return super().get_context_data(
            titulo=self.titulo, singular=self.singular, icono=self.icono, seccion_activa=url_lista,
            url_lista=url_lista, url_nuevo=f"utn:{self.prefijo}_nuevo",
            url_editar=f"utn:{self.prefijo}_editar", url_eliminar=f"utn:{self.prefijo}_eliminar", **kwargs)

    def get_success_url(self):
        return reverse(f"utn:{self.prefijo}_lista")


class AdminLista(TablaMixin, ListView):
    template_name = "admin_lista.html"
    paginate_by = 15

    def get_queryset(self):
        queryset = self.model.objects.all().order_by("-id")
        self.q = self.request.GET.get("q", "").strip()
        if self.q:
            # Q permite unir condiciones con "|" (o): busca el texto en cualquiera de los campos de `busqueda`
            condicion = Q()
            for campo in self.busqueda:
                condicion |= Q(**{f"{campo}__icontains": self.q})
            queryset = queryset.filter(condicion).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(q=self.q, encabezados=self.encabezados, **kwargs)
        # Una fila por registro: el objeto y la lista de valores que muestra cada columna
        contexto["filas"] = [{"obj": obj, "valores": self.fila(obj)} for obj in contexto["page_obj"]]
        return contexto


class AdminFormMixin(TablaMixin):
    """Lo que comparten crear y editar: el template y el mensaje de éxito."""
    template_name = "admin_form.html"

    def get_form_class(self):
        return self.formulario

    def get_context_data(self, **kwargs):
        return super().get_context_data(instancia=self.object, **kwargs)

    def form_valid(self, form):
        respuesta = super().form_valid(form)  # guarda el objeto
        messages.success(self.request, f"{self.singular.capitalize()} «{self.object}» {self.accion} correctamente.")
        if "guardar_y_otro" in self.request.POST:
            return redirect(f"utn:{self.prefijo}_nuevo")
        return respuesta


class AdminNuevo(AdminFormMixin, CreateView):
    accion = "creado"


class AdminEditar(AdminFormMixin, UpdateView):
    accion = "actualizado"


class AdminEliminar(TablaMixin, DeleteView):
    template_name = "admin_confirmar_eliminar.html"

    def form_valid(self, form):
        nombre = str(self.object)
        if getattr(self.object, "usuario_id", None) == self.request.user.id:
            messages.error(self.request, "No podés eliminar tu propio usuario.")
            return redirect(self.get_success_url())
        usuario = getattr(self.object, "usuario", None)  # alumnos, docentes y administradores tienen cuenta de usuario
        self.object.delete()
        if usuario:
            usuario.delete()  # se borra también la cuenta para iniciar sesión
        messages.success(self.request, f"«{nombre}» se eliminó correctamente.")
        return redirect(self.get_success_url())


class DashboardView(AdminMixin, TemplateView):
    template_name = "admin_dashboard.html"

    def get_context_data(self, **kwargs):
        tarjetas = [
            {"url": "utn:alumno_lista", "titulo": "Alumnos", "icono": "bi-person-badge", "cantidad": Alumno.objects.count()},
            {"url": "utn:docente_lista", "titulo": "Docentes", "icono": "bi-person-workspace", "cantidad": Docente.objects.count()},
            {"url": "utn:carrera_lista", "titulo": "Carreras", "icono": "bi-mortarboard", "cantidad": Carrera.objects.count()},
            {"url": "utn:materia_lista", "titulo": "Materias", "icono": "bi-book", "cantidad": Materia.objects.count()},
            {"url": "utn:curso_lista", "titulo": "Cursos", "icono": "bi-people", "cantidad": Curso.objects.count()},
            {"url": "admin:UTN_turno_changelist", "titulo": "Turnos", "icono": "bi-sun", "cantidad": Turno.objects.count()},
            {"url": "utn:dictado_lista", "titulo": "Dictados de materia", "icono": "bi-easel", "cantidad": DictadoMateria.objects.count()},
            {"url": "utn:inscripcion_lista", "titulo": "Inscripciones", "icono": "bi-journal-check", "cantidad": Inscripcion.objects.count()},
        ]
        ultimas = Inscripcion.objects.select_related("alumno", "dictado_materia__materia").order_by("-fecha_inscripcion", "-id")[:6]
        return super().get_context_data(tarjetas=tarjetas, ultimas_inscripciones=ultimas,
                                        seccion_activa="dashboard", **kwargs)


def nombres(relacion):
    """Los objetos de una relación muchos-a-muchos, separados por coma ('Ana, Luis')."""
    return ", ".join(str(objeto) for objeto in relacion.all())


# ---------------------------------------------------------------------------
# Alumnos
# ---------------------------------------------------------------------------
class Alumnos:
    model, formulario = Alumno, AlumnoForm
    prefijo, titulo, singular, icono = "alumno", "Alumnos", "alumno", "bi-person-badge"


class AlumnoLista(Alumnos, AdminLista):
    encabezados = ["Nombre", "DNI", "Email", "Carrera", "Usuario"]
    busqueda = ["nombre_completo", "documento", "email", "usuario__username"]

    def fila(self, alumno):
        return [alumno.nombre_completo, alumno.documento, alumno.email, alumno.carrera.sigla,
                alumno.usuario.username if alumno.usuario else None]


class AlumnoNuevo(Alumnos, AdminNuevo):
    pass


class AlumnoEditar(Alumnos, AdminEditar):
    pass


class AlumnoEliminar(Alumnos, AdminEliminar):
    pass


# ---------------------------------------------------------------------------
# Docentes
# ---------------------------------------------------------------------------
class Docentes:
    model, formulario = Docente, DocenteForm
    prefijo, titulo, singular, icono = "docente", "Docentes", "docente", "bi-person-workspace"


class DocenteLista(Docentes, AdminLista):
    encabezados = ["Legajo", "Apellido", "Nombre", "Usuario"]
    busqueda = ["legajo", "nombre", "apellido", "usuario__username"]

    def fila(self, docente):
        return [docente.legajo, docente.apellido, docente.nombre, docente.usuario.username if docente.usuario else None]


class DocenteNuevo(Docentes, AdminNuevo):
    pass


class DocenteEditar(Docentes, AdminEditar):
    pass


class DocenteEliminar(Docentes, AdminEliminar):
    pass


# ---------------------------------------------------------------------------
# Administradores (solo los gestiona un director)
# ---------------------------------------------------------------------------
class Administradores:
    model, formulario = Administrador, AdministradorForm
    prefijo, titulo, singular, icono = "administrador", "Administradores", "administrador", "bi-shield-lock"
    solo_director = True
    mensaje_denegado = "Solo un director puede gestionar administradores."


class AdministradorLista(Administradores, AdminLista):
    encabezados = ["Apellido", "Nombre", "Cargo", "Usuario"]
    busqueda = ["nombre", "apellido", "usuario__username"]

    def fila(self, administrador):
        return [administrador.apellido, administrador.nombre, administrador.get_cargo_display(),
                administrador.usuario.username]


class AdministradorNuevo(Administradores, AdminNuevo):
    pass


class AdministradorEditar(Administradores, AdminEditar):
    pass


class AdministradorEliminar(Administradores, AdminEliminar):
    pass


# ---------------------------------------------------------------------------
# Carreras
# ---------------------------------------------------------------------------
class Carreras:
    model, formulario = Carrera, CarreraForm
    prefijo, titulo, singular, icono = "carrera", "Carreras", "carrera", "bi-mortarboard"


class CarreraLista(Carreras, AdminLista):
    encabezados = ["Nombre", "Sigla"]
    busqueda = ["nombre", "sigla"]

    def fila(self, carrera):
        return [carrera.nombre, carrera.sigla]


class CarreraNuevo(Carreras, AdminNuevo):
    pass


class CarreraEditar(Carreras, AdminEditar):
    pass


class CarreraEliminar(Carreras, AdminEliminar):
    pass


# ---------------------------------------------------------------------------
# Materias
# ---------------------------------------------------------------------------
class Materias:
    model, formulario = Materia, MateriaForm
    prefijo, titulo, singular, icono = "materia", "Materias", "materia", "bi-book"


class MateriaLista(Materias, AdminLista):
    encabezados = ["Nombre", "Sigla", "Nivel", "Carrera", "Correlativas"]
    busqueda = ["nombre", "sigla", "carrera__nombre"]

    def fila(self, materia):
        return [materia.nombre, materia.sigla, materia.nivel, materia.carrera.sigla, nombres(materia.correlativas)]


class MateriaNuevo(Materias, AdminNuevo):
    pass


class MateriaEditar(Materias, AdminEditar):
    pass


class MateriaEliminar(Materias, AdminEliminar):
    pass


# ---------------------------------------------------------------------------
# Cursos
# ---------------------------------------------------------------------------
class Cursos:
    model, formulario = Curso, CursoForm
    prefijo, titulo, singular, icono = "curso", "Cursos", "curso", "bi-people"


class CursoLista(Cursos, AdminLista):
    encabezados = ["Nombre", "Nivel", "Carrera", "Turno"]
    busqueda = ["nombre", "carrera__nombre", "turno__nombre"]

    def fila(self, curso):
        return [curso.nombre, curso.nivel, curso.carrera.sigla, curso.turno]


class CursoNuevo(Cursos, AdminNuevo):
    pass


class CursoEditar(Cursos, AdminEditar):
    pass


class CursoEliminar(Cursos, AdminEliminar):
    pass


# ---------------------------------------------------------------------------
# Dictados de materia
# ---------------------------------------------------------------------------
class Dictados:
    model, formulario = DictadoMateria, DictadoForm
    prefijo, titulo, singular, icono = "dictado", "Dictados de materia", "dictado", "bi-easel"


class DictadoLista(Dictados, AdminLista):
    encabezados = ["Materia", "Curso", "Ciclo", "Docentes"]
    busqueda = ["materia__nombre", "curso__nombre", "docentes__apellido"]

    def fila(self, dictado):
        return [dictado.materia.nombre, dictado.curso, dictado.ciclo_lectivo.anio, nombres(dictado.docentes)]


class DictadoNuevo(Dictados, AdminNuevo):
    pass


class DictadoEditar(Dictados, AdminEditar):
    pass


class DictadoEliminar(Dictados, AdminEliminar):
    pass


# ---------------------------------------------------------------------------
# Horarios
# ---------------------------------------------------------------------------
class Horarios:
    model, formulario = Horario, HorarioForm
    prefijo, titulo, singular, icono = "horario", "Horarios", "horario", "bi-calendar-week"


class HorarioLista(Horarios, AdminLista):
    encabezados = ["Día", "Dictado", "Módulos"]
    busqueda = ["dia", "dictado_materia__materia__nombre"]

    def fila(self, horario):
        return [horario.dia, horario.dictado_materia, nombres(horario.modulos)]


class HorarioNuevo(Horarios, AdminNuevo):
    pass


class HorarioEditar(Horarios, AdminEditar):
    pass


class HorarioEliminar(Horarios, AdminEliminar):
    pass


# ---------------------------------------------------------------------------
# Inscripciones
# ---------------------------------------------------------------------------
class Inscripciones:
    model, formulario = Inscripcion, InscripcionForm
    prefijo, titulo, singular, icono = "inscripcion", "Inscripciones", "inscripción", "bi-journal-check"


class InscripcionLista(Inscripciones, AdminLista):
    encabezados = ["Código", "Alumno", "Dictado", "Condición", "Fecha"]
    busqueda = ["codigo_inscripcion", "alumno__nombre_completo", "dictado_materia__materia__nombre"]

    def fila(self, inscripcion):
        return [inscripcion.codigo_inscripcion, inscripcion.alumno.nombre_completo, inscripcion.dictado_materia,
                inscripcion.condicion_actual, inscripcion.fecha_inscripcion]


class InscripcionNuevo(Inscripciones, AdminNuevo):
    pass


class InscripcionEditar(Inscripciones, AdminEditar):
    pass


class InscripcionEliminar(Inscripciones, AdminEliminar):
    pass
