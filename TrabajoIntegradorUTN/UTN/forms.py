from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import (Administrador, Alumno, Carrera, Curso, DictadoMateria, Docente, Horario, Inscripcion,
                     InstanciaEvaluacion, Materia, franja_de)
from .roles import obtener_rol


class EstiloBootstrapMixin:
    """Le pone a cada campo la clase de Bootstrap que corresponde."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.CheckboxSelectMultiple):
                continue  # las casillas múltiples se dibujan en el template
            if isinstance(campo.widget, forms.CheckboxInput):
                campo.widget.attrs["class"] = "form-check-input"
            elif isinstance(campo.widget, forms.Select):
                campo.widget.attrs["class"] = "form-select"
            else:
                campo.widget.attrs["class"] = "form-control"


class ModeloForm(EstiloBootstrapMixin, forms.ModelForm):
    """Base de los formularios del panel de administración."""


class MateriaForm(ModeloForm):
    """Materia con sus correlativas: deben ser de la misma carrera y no pueden formar un ciclo."""

    class Meta:
        model = Materia
        fields = "__all__"
        widgets = {"correlativas": forms.CheckboxSelectMultiple()}

    def clean(self):
        datos = super().clean()
        carrera = datos.get("carrera")
        for correlativa in datos.get("correlativas", []):
            if carrera and correlativa.carrera_id != carrera.id:
                self.add_error("correlativas", f"«{correlativa.nombre}» es de otra carrera.")
            elif self.instance.pk and (correlativa.pk == self.instance.pk
                                       or self.instance.pk in correlativa.todas_las_correlativas()):
                self.add_error("correlativas", f"«{correlativa.nombre}» no puede ser correlativa (sería un ciclo).")
        return datos


class CarreraForm(ModeloForm):
    class Meta:
        model = Carrera
        fields = "__all__"


class CursoForm(ModeloForm):
    class Meta:
        model = Curso
        fields = "__all__"


class DictadoForm(ModeloForm):
    class Meta:
        model = DictadoMateria
        fields = "__all__"
        widgets = {"docentes": forms.CheckboxSelectMultiple()}


class InscripcionForm(ModeloForm):
    class Meta:
        model = Inscripcion
        fields = ["alumno", "dictado_materia"]  # el código y la fecha los pone el sistema


# ---------------------------------------------------------------------------
# Login único
# ---------------------------------------------------------------------------
class LoginForm(EstiloBootstrapMixin, AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Usuario o contraseña incorrectos.",
        "sin_rol": "Tu usuario no tiene un perfil asignado (alumno, docente o administrador). Contactá a administración.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"placeholder": "Tu usuario", "autofocus": True})
        self.fields["password"].widget.attrs.update({"placeholder": "Tu contraseña"})

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if obtener_rol(user) is None:
            raise forms.ValidationError(self.error_messages["sin_rol"], code="sin_rol")


# ---------------------------------------------------------------------------
# Personas: además del perfil, crean/editan la cuenta de usuario (usuario + contraseña)
# ---------------------------------------------------------------------------
class ConUsuarioForm(ModeloForm):
    es_staff = False  # los administradores pueden entrar también al /admin/ de Django
    username = forms.CharField(label="Usuario para iniciar sesión", max_length=150)
    password = forms.CharField(label="Contraseña", required=False, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.usuario_id:
            self.fields["username"].initial = self.instance.usuario.username
            self.fields["password"].help_text = "Dejala vacía para mantener la contraseña actual."
        else:
            self.fields["password"].required = True
            self.fields["password"].help_text = "Mínimo 8 caracteres, no solo números."

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        repetidos = User.objects.filter(username__iexact=username).exclude(pk=self.instance.usuario_id)
        if repetidos.exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        if password:
            validate_password(password)
        return password

    def save(self, commit=True):
        perfil = super().save(commit=False)
        usuario = perfil.usuario or User()
        usuario.username = self.cleaned_data["username"]
        usuario.is_staff = self.es_staff
        if self.cleaned_data["password"]:
            usuario.set_password(self.cleaned_data["password"])
        usuario.save()
        perfil.usuario = usuario
        perfil.save()
        self.save_m2m()
        return perfil


class AlumnoForm(ConUsuarioForm):
    class Meta:
        model = Alumno
        fields = ["nombre_completo", "documento", "email", "carrera"]


class DocenteForm(ConUsuarioForm):
    class Meta:
        model = Docente
        fields = ["legajo", "nombre", "apellido"]


class AdministradorForm(ConUsuarioForm):
    es_staff = True

    class Meta:
        model = Administrador
        fields = ["nombre", "apellido", "cargo"]


class HorarioForm(ModeloForm):
    dia = forms.ChoiceField(choices=[(d, d) for d in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]])

    class Meta:
        model = Horario
        fields = ["dictado_materia", "dia", "modulos"]
        widgets = {"modulos": forms.CheckboxSelectMultiple()}

    def clean(self):
        datos = super().clean()
        dictado, dia, modulos = datos.get("dictado_materia"), datos.get("dia"), datos.get("modulos")
        if not (dictado and dia and modulos):
            return datos
        turno = dictado.curso.turno
        if any(m.turno_id != turno.id for m in modulos):
            self.add_error("modulos", f"Los módulos tienen que ser del turno del curso ({turno.nombre}).")
            return datos
        # Dos materias del mismo curso no pueden dictarse a la misma hora.
        desde, hasta = franja_de(modulos)
        mismos = Horario.objects.filter(dia=dia, dictado_materia__curso=dictado.curso,
                                        dictado_materia__ciclo_lectivo=dictado.ciclo_lectivo)
        for otro in mismos.exclude(pk=self.instance.pk).prefetch_related("modulos"):
            if desde < otro.franja[1] and otro.franja[0] < hasta:
                self.add_error("modulos", f"Se superpone con {otro.dictado_materia.materia.nombre} ({otro.texto}).")
                break
        return datos


# ---------------------------------------------------------------------------
# "Mi cuenta": cada usuario cambia su nombre de usuario y su contraseña
# ---------------------------------------------------------------------------
class CuentaUsuarioForm(ModeloForm):
    class Meta:
        model = User
        fields = ["username"]
        labels = {"username": "Nuevo nombre de usuario"}


class CambiarPasswordForm(EstiloBootstrapMixin, PasswordChangeForm):
    pass


# ---------------------------------------------------------------------------
# Planilla del docente: agregar/editar una columna (una evaluación)
# ---------------------------------------------------------------------------
class ColumnaForm(ModeloForm):
    alcance = forms.ChoiceField(choices=[("todos", "A todos"), ("algunos", "A algunos")], initial="todos")

    class Meta:
        model = InstanciaEvaluacion
        fields = ["tipo_evaluacion", "nombre", "fecha", "inscripciones"]

    def __init__(self, *args, dictado, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["inscripciones"].queryset = dictado.inscripciones.all()  # solo alumnos de ese curso
        self.fields["inscripciones"].required = False

    def clean(self):
        datos = super().clean()
        if datos.get("alcance") == "algunos":
            if not datos.get("inscripciones"):
                self.add_error("inscripciones", "Elegí al menos un alumno para la evaluación.")
        else:  # "a todos": no hace falta guardar la lista de alumnos
            datos["inscripciones"] = self.fields["inscripciones"].queryset.none()
        return datos

    def save(self, commit=True):
        self.instance.para_todos = self.cleaned_data["alcance"] == "todos"
        return super().save(commit)
