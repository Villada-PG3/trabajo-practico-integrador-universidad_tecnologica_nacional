import uuid
from django.db import models
from django.utils import timezone

class Carrera(models.Model):
    nombre = models.CharField(max_length=100)
    sigla = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.nombre} ({self.sigla})"


class Alumno(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name="alumnos")
    nombre_completo = models.CharField(max_length=100)
    documento = models.IntegerField(unique=True)
    email = models.EmailField(max_length=100)

    def __str__(self):
        return f"{self.nombre_completo} - DNI: {self.documento}"


class Materia(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name="materias")
    nombre = models.CharField(max_length=100)
    sigla = models.CharField(max_length=20)
    nivel = models.IntegerField()

    def __str__(self):
        return f"{self.nombre} ({self.sigla}) - Nivel {self.nivel}"


class Turno(models.Model):
    nombre = models.CharField(max_length=50) # Mañana, Tarde, Noche
    descripcion = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombre


class Curso(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name="cursos")
    turno = models.ForeignKey(Turno, on_delete=models.PROTECT, related_name="cursos")
    nombre = models.CharField(max_length=50) # Ej: 2K7, 2K9
    nivel = models.IntegerField()

    def __str__(self):
        return f"{self.nombre} ({self.turno.nombre})"


class CicloLectivo(models.Model):
    anio = models.IntegerField()
    descripcion = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    def __str__(self):
        return f"{self.descripcion} ({self.anio})"


class DictadoMateria(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name="dictados")
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="dictados")
    ciclo_lectivo = models.ForeignKey(CicloLectivo, on_delete=models.PROTECT, related_name="dictados")

    def __str__(self):
        return f"{self.materia.sigla} - {self.curso.nombre} ({self.ciclo_lectivo.anio})"


class Modulo(models.Model):
    numero = models.IntegerField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    def __str__(self):
        return f"Módulo {self.numero} ({self.hora_inicio.strftime('%H:%M')} a {self.hora_fin.strftime('%H:%M')})"


class Horario(models.Model):
    dictado_materia = models.ForeignKey(DictadoMateria, on_delete=models.CASCADE, related_name="horarios")
    dia = models.CharField(max_length=20) # Lunes, Martes, etc.
    modulos = models.ManyToManyField(Modulo, related_name="horarios")

    def __str__(self):
        return f"{self.dia} - {self.dictado_materia}"


class Docente(models.Model):
    legajo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.apellido}, {self.nombre} (Legajo: {self.legajo})"


class Condicion(models.Model):
    nombre = models.CharField(max_length=50) # Inscripto, Regular, Libre, Aprobación directa, Promoción Práctica
    descripcion = models.CharField(max_length=150, blank=True, null=True)
    es_condicion_final = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre


class TipoEvaluacion(models.Model):
    nombre = models.CharField(max_length=50) # Parcial Teórico, Práctico, TP
    descripcion = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return self.nombre


class Inscripcion(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="inscripciones")
    dictado_materia = models.ForeignKey(DictadoMateria, on_delete=models.CASCADE, related_name="inscripciones")
    codigo_inscripcion = models.CharField(max_length=30, unique=True, editable=False)
    fecha_inscripcion = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.codigo_inscripcion:
            self.codigo_inscripcion = f"INS-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def obtener_condicion_actual(self):
        ultimo_cambio = self.historial_condiciones.order_by('-fecha_hora').first()
        return ultimo_cambio.condicion.nombre if ultimo_cambio else "Sin Condición"

    def es_regular(self):
        return self.obtener_condicion_actual() == "Regular"

    def __str__(self):
        return f"{self.alumno.nombre_completo} - {self.dictado_materia} [{self.codigo_inscripcion}]"


class CambioCondicion(models.Model):
    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE, related_name="historial_condiciones")
    condicion = models.ForeignKey(Condicion, on_delete=models.PROTECT)
    docente = models.ForeignKey(Docente, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_hora = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.inscripcion.alumno.nombre_completo} -> {self.condicion.nombre}"


class Evaluacion(models.Model):
    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE, related_name="evaluaciones")
    tipo_evaluacion = models.ForeignKey(TipoEvaluacion, on_delete=models.PROTECT)
    docente = models.ForeignKey(Docente, on_delete=models.SET_NULL, null=True)
    valor = models.DecimalField(max_digits=4, decimal_places=2)
    fecha_evaluacion = models.DateField()

    def __str__(self):
        return f"{self.tipo_evaluacion.nombre}: {self.valor} ({self.inscripcion.alumno.nombre_completo})"