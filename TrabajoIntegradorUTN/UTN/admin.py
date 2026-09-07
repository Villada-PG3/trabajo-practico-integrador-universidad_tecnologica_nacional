from django.contrib import admin
from .models import (
    Carrera, Alumno, Materia, Turno, Curso, CicloLectivo,
    DictadoMateria, Modulo, Horario, Docente, Condicion,
    TipoEvaluacion, Inscripcion, CambioCondicion, Evaluacion
)

admin.site.register([
    Carrera, Alumno, Materia, Turno, Curso, CicloLectivo,
    DictadoMateria, Modulo, Horario, Docente, Condicion,
    TipoEvaluacion, Inscripcion, CambioCondicion, Evaluacion
])