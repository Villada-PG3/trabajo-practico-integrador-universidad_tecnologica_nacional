from django.contrib import admin
from .models import (
    Carrera, Alumno, Materia, Turno, Curso, CicloLectivo,
    DictadoMateria, Modulo, Horario, Docente, Administrador, Condicion,
    TipoEvaluacion, Inscripcion, CambioCondicion, Evaluacion, InstanciaEvaluacion
)

from .forms import MateriaForm


class MateriaAdmin(admin.ModelAdmin):
    form = MateriaForm  # valida las correlativas también desde /admin/


admin.site.register(Materia, MateriaAdmin)
admin.site.register([
    Carrera, Alumno, Turno, Curso, CicloLectivo,
    DictadoMateria, Modulo, Horario, Docente, Administrador, Condicion,
    TipoEvaluacion, Inscripcion, CambioCondicion, Evaluacion, InstanciaEvaluacion
])