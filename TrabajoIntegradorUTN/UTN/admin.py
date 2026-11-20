from django.contrib import admin

from .forms import HorarioForm, MateriaForm
from .models import (
    Carrera, Alumno, Materia, Turno, Curso, CicloLectivo,
    DictadoMateria, Modulo, Horario, Docente, Administrador, Condicion,
    TipoEvaluacion, Inscripcion, CambioCondicion, Evaluacion, InstanciaEvaluacion
)
from .roles import obtener_rol, es_director, ROL_ADMIN


def es_administrador(self, request, obj=None):
    return obtener_rol(request.user) == ROL_ADMIN


def solo_director(self, request, obj=None):
    return es_director(request.user)


class AdminDeLaFacultad(admin.ModelAdmin):
    """Director y ejecutivo pueden gestionar estas tablas desde /admin/ (las que no están en su panel)."""
    has_module_permission = has_view_permission = has_add_permission = es_administrador
    has_change_permission = has_delete_permission = es_administrador


class MateriaAdmin(AdminDeLaFacultad):
    form = MateriaForm  # valida las correlativas también desde /admin/


class HorarioAdmin(AdminDeLaFacultad):
    form = HorarioForm  # valida el turno y la superposición también desde /admin/


class AdministradorAdmin(AdminDeLaFacultad):
    """Los administradores solo los gestiona un director."""
    has_module_permission = has_view_permission = has_add_permission = solo_director
    has_change_permission = has_delete_permission = solo_director


admin.site.register(Materia, MateriaAdmin)
admin.site.register(Horario, HorarioAdmin)
admin.site.register(Administrador, AdministradorAdmin)
admin.site.register([
    Carrera, Alumno, Turno, Curso, CicloLectivo, DictadoMateria, Modulo, Docente, Condicion,
    TipoEvaluacion, Inscripcion, CambioCondicion, Evaluacion, InstanciaEvaluacion
], AdminDeLaFacultad)
