from django.contrib import admin
from .models import (
    Carrera, Alumno, Materia, Turno, Curso, CicloLectivo,
    DictadoMateria, Modulo, Horario, Docente, Administrador, Condicion,
    TipoEvaluacion, Inscripcion, CambioCondicion, Evaluacion, InstanciaEvaluacion
)

admin.site.register([
    Carrera, Alumno, Materia, Turno, Curso, CicloLectivo,
    DictadoMateria, Modulo, Horario, Docente, Administrador, Condicion,
    TipoEvaluacion, Inscripcion, CambioCondicion, Evaluacion, InstanciaEvaluacion
])