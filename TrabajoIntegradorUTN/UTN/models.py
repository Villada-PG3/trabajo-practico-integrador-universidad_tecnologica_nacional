import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    documento = models.IntegerField(unique=True)
    email = models.EmailField(max_length=100)

    def __str__(self):
        return f"{self.nombre_completo} - DNI: {self.documento}"

    def inscripciones_en_curso(self):
        """Las que todavía no tienen condición final: lo que el alumno está cursando."""
        inscripciones = self.inscripciones.select_related(
            "dictado_materia__materia", "dictado_materia__curso", "dictado_materia__ciclo_lectivo"
        ).prefetch_related("historial_condiciones__condicion", "dictado_materia__horarios__modulos")
        en_curso = []
        for inscripcion in inscripciones:
            ultimo = inscripcion.ultimo_cambio
            if ultimo and not ultimo.condicion.es_condicion_final:
                en_curso.append(inscripcion)
        return en_curso

    def materias_cumplidas(self):
        """Ids de las materias donde el alumno quedó en una condición que habilita las siguientes."""
        inscripciones = self.inscripciones.select_related("dictado_materia").prefetch_related("historial_condiciones__condicion")
        cumplidas = set()
        for inscripcion in inscripciones:
            ultimo = inscripcion.ultimo_cambio
            if ultimo and ultimo.condicion.habilita_correlativas:
                cumplidas.add(inscripcion.dictado_materia.materia_id)
        return cumplidas


class Materia(models.Model):
    REGIMENES = [
        ("ANUAL", "Anual"),
        ("CUATRIMESTRAL", "Cuatrimestral"),
    ]
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name="materias")
    nombre = models.CharField(max_length=100)
    sigla = models.CharField(max_length=20)
    nivel = models.IntegerField()
    regimen = models.CharField(max_length=15, choices=REGIMENES, default="ANUAL")
    correlativas = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="habilita")

    def faltantes(self, cumplidas):
        """Las correlativas de esta materia que el alumno todavía no cumple."""
        faltantes = []
        for correlativa in self.correlativas.all():
            if correlativa.id not in cumplidas:
                faltantes.append(correlativa)
        return faltantes

    def todas_las_correlativas(self):
        """Ids de todo lo que hay que tener antes (directas e indirectas). Sirve para detectar ciclos."""
        por_revisar, vistas = list(self.correlativas.all()), set()
        while por_revisar:
            materia = por_revisar.pop()
            if materia.id not in vistas:
                vistas.add(materia.id)
                por_revisar.extend(materia.correlativas.all())
        return vistas

    def __str__(self):
        return f"{self.nombre} ({self.sigla}) - Nivel {self.nivel}"


class Turno(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombre


class Curso(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name="cursos")
    turno = models.ForeignKey(Turno, on_delete=models.PROTECT, related_name="cursos")
    nombre = models.CharField(max_length=50)
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
    docentes = models.ManyToManyField("Docente", related_name="dictados", blank=True)

    def choque_con(self, otro):
        """El primer par de horarios (propio, ajeno) que se pisan con otro dictado, o None."""
        for propio in self.horarios.all():
            for ajeno in otro.horarios.all():
                if propio.se_superpone_con(ajeno):
                    return propio, ajeno
        return None

    def __str__(self):
        return f"{self.materia.sigla} - {self.curso.nombre} ({self.ciclo_lectivo.anio})"


class Modulo(models.Model):
    """Una franja de clase de un turno: el módulo 3 de la mañana no es el módulo 3 de la noche."""
    turno = models.ForeignKey(Turno, on_delete=models.PROTECT, related_name="modulos")
    numero = models.IntegerField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    def __str__(self):
        return f"{self.turno.nombre} · Módulo {self.numero} ({self.hora_inicio:%H:%M} a {self.hora_fin:%H:%M})"


def franja_de(modulos):
    """(desde, hasta) de un bloque de módulos: del comienzo del primero al final del último."""
    modulos = list(modulos)
    if not modulos:
        return None
    return min(m.hora_inicio for m in modulos), max(m.hora_fin for m in modulos)


class Horario(models.Model):
    dictado_materia = models.ForeignKey(DictadoMateria, on_delete=models.CASCADE, related_name="horarios")
    dia = models.CharField(max_length=20)
    modulos = models.ManyToManyField(Modulo, related_name="horarios")

    @property
    def franja(self):
        return franja_de(self.modulos.all())  # .all() aprovecha el prefetch_related

    @property
    def texto(self):
        """Ej: "Miércoles · Módulos 4-5-6 (14:00 a 16:15)"."""
        modulos = sorted(self.modulos.all(), key=lambda m: m.numero)
        if not modulos:
            return self.dia
        nums = "-".join(str(m.numero) for m in modulos)
        desde, hasta = franja_de(modulos)
        return f"{self.dia} · Módulos {nums} ({desde:%H:%M} a {hasta:%H:%M})"

    def se_superpone_con(self, otro):
        """Mismo día y las horas se pisan (que uno termine justo cuando empieza el otro no cuenta)."""
        if self.dia != otro.dia:
            return False
        a, b = self.franja, otro.franja
        if a is None or b is None:
            return False
        return a[0] < b[1] and b[0] < a[1]

    def __str__(self):
        return f"{self.dia} - {self.dictado_materia}"


class Docente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    legajo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.apellido}, {self.nombre} (Legajo: {self.legajo})"


class Administrador(models.Model):
    DIRECTOR = "DIRECTOR"
    EJECUTIVO = "EJECUTIVO"
    CARGOS = [
        (DIRECTOR, "Director"),
        (EJECUTIVO, "Ejecutivo"),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="administrador")
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    cargo = models.CharField(max_length=20, choices=CARGOS, default=EJECUTIVO)

    class Meta:
        verbose_name_plural = "Administradores"

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.get_cargo_display()})"


class Condicion(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=150, blank=True, null=True)
    es_condicion_final = models.BooleanField(default=False)
    habilita_correlativas = models.BooleanField(
        default=False, help_text="Si el alumno queda así en una materia, puede cursar las que la tienen como correlativa")

    def __str__(self):
        return self.nombre


class TipoEvaluacion(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return self.nombre


def _generar_codigo():
    return f"INS-{uuid.uuid4().hex[:8].upper()}"


class Inscripcion(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="inscripciones")
    dictado_materia = models.ForeignKey(DictadoMateria, on_delete=models.CASCADE, related_name="inscripciones")
    codigo_inscripcion = models.CharField(max_length=30, unique=True, default=_generar_codigo, editable=False)
    fecha_inscripcion = models.DateField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["alumno", "dictado_materia"],
                name="inscripcion_unica_alumno_dictado",
                violation_error_message="Ya estás inscripto en esta materia.",
            )
        ]

    def clean(self):
        """Reglas para inscribirse: materia de su carrera, no cumplida ni en curso, con correlativas y sin choque de horarios."""
        if not (self.alumno_id and self.dictado_materia_id):
            return
        alumno, dictado = self.alumno, self.dictado_materia
        materia = dictado.materia
        cumplidas = alumno.materias_cumplidas()
        en_curso = alumno.inscripciones_en_curso()

        # 1. Tiene que ser de su carrera
        if materia.carrera_id != alumno.carrera_id:
            raise ValidationError("Esa materia no pertenece a la carrera del alumno.")
        # 2. No puede volver a cursar una materia que ya cumplió
        if materia.id in cumplidas:
            raise ValidationError(f"Ya cumpliste {materia.nombre}: no podés volver a inscribirte.")
        # 3. Ni cursarla dos veces a la vez (por ejemplo, en otra comisión)
        for otra in en_curso:
            if otra.dictado_materia.materia_id == materia.id and otra.pk != self.pk:
                raise ValidationError(f"Ya estás cursando {materia.nombre}.")
        # 4. Tiene que tener cumplidas las correlativas
        faltantes = materia.faltantes(cumplidas)
        if faltantes:
            raise ValidationError("Te faltan las correlativas: " + ", ".join(m.nombre for m in faltantes) + ".")
        # 5. No puede tener otra materia en el mismo horario (del mismo ciclo lectivo)
        for otra in en_curso:
            if otra.dictado_materia.ciclo_lectivo_id != dictado.ciclo_lectivo_id or otra.pk == self.pk:
                continue
            choque = dictado.choque_con(otra.dictado_materia)
            if choque:
                raise ValidationError(f"Se superpone con {otra.dictado_materia.materia.nombre} ({choque[1].texto}).")

    def save(self, *args, **kwargs):
        es_nueva = self._state.adding
        super().save(*args, **kwargs)
        if es_nueva:  # toda inscripción nueva arranca con la condición "Inscripto"
            condicion, _ = Condicion.objects.get_or_create(
                nombre="Inscripto", defaults={"es_condicion_final": False}
            )
            CambioCondicion.objects.create(inscripcion=self, condicion=condicion)

    @property
    def ultimo_cambio(self):
        # Se recorre .all() (y no .order_by) para aprovechar el prefetch_related: así no hace una consulta por inscripción
        ultimo = None
        for cambio in self.historial_condiciones.all():
            if ultimo is None or (cambio.fecha_hora, cambio.id) > (ultimo.fecha_hora, ultimo.id):
                ultimo = cambio
        return ultimo

    @property
    def condicion_actual(self):
        return self.ultimo_cambio.condicion.nombre if self.ultimo_cambio else "Sin Condición"

    def __str__(self):
        return f"{self.alumno.nombre_completo} - {self.dictado_materia} [{self.codigo_inscripcion}]"


class CambioCondicion(models.Model):
    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE, related_name="historial_condiciones")
    condicion = models.ForeignKey(Condicion, on_delete=models.PROTECT)
    docente = models.ForeignKey(Docente, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_hora = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.inscripcion.alumno.nombre_completo} -> {self.condicion.nombre}"


class InstanciaEvaluacion(models.Model):
    """Una "columna" de la planilla del docente: un parcial, un TP, un recuperatorio, etc."""
    dictado_materia = models.ForeignKey(DictadoMateria, on_delete=models.CASCADE, related_name="instancias_evaluacion")
    tipo_evaluacion = models.ForeignKey(TipoEvaluacion, on_delete=models.PROTECT, related_name="instancias")
    nombre = models.CharField(max_length=80, blank=True, help_text="Opcional. Ej: Parcial 1, Recuperatorio")
    fecha = models.DateField(default=timezone.localdate)
    para_todos = models.BooleanField(default=True, help_text="Si está tildado, aplica a todos los inscriptos del curso")
    inscripciones = models.ManyToManyField(Inscripcion, related_name="instancias_evaluacion", blank=True,
                                           help_text="Solo se usa si no es para todos")
    creada_por = models.ForeignKey(Docente, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["fecha", "id"]
        verbose_name = "instancia de evaluación"
        verbose_name_plural = "instancias de evaluación"

    @property
    def titulo(self):
        return self.nombre or self.tipo_evaluacion.nombre

    def __str__(self):
        return f"{self.titulo} - {self.dictado_materia} ({self.fecha:%d/%m/%Y})"


class Evaluacion(models.Model):
    """La nota de un alumno (inscripción) en una columna de la planilla."""
    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE, related_name="evaluaciones")
    instancia = models.ForeignKey(InstanciaEvaluacion, on_delete=models.CASCADE, related_name="notas")
    docente = models.ForeignKey(Docente, on_delete=models.SET_NULL, null=True, blank=True)
    valor = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return f"{self.instancia.titulo}: {self.valor} ({self.inscripcion.alumno.nombre_completo})"
