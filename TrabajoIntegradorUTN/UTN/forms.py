from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import Alumno, Docente, Administrador, Horario, InstanciaEvaluacion
from .roles import obtener_rol


class EstiloBootstrapMixin:
    """Le pone a cada campo la clase de Bootstrap que corresponde y usa inputs nativos de fecha/hora."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(campo, forms.DateTimeField):
                campo.widget = widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
            elif isinstance(campo, forms.DateField):
                campo.widget = widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
            elif isinstance(campo, forms.TimeField):
                campo.widget = widget = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
            elif isinstance(campo, forms.ModelMultipleChoiceField):
                campo.widget = widget = forms.CheckboxSelectMultiple()
            if isinstance(widget, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
                continue
            if isinstance(widget, forms.CheckboxInput):
                clase = "form-check-input"
            elif isinstance(widget, forms.Select):
                clase = "form-select"
            else:
                clase = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {clase}".strip()


class ModeloForm(EstiloBootstrapMixin, forms.ModelForm):
    """Base de los formularios del panel de administración (también sirve con modelform_factory)."""


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
        usuario = perfil.usuario if perfil.usuario_id else User()
        usuario.username = self.cleaned_data["username"]
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
    class Meta:
        model = Administrador
        fields = ["nombre", "apellido", "cargo"]


class HorarioForm(ModeloForm):
    dia = forms.ChoiceField(choices=[(d, d) for d in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]])

    class Meta:
        model = Horario
        fields = ["dictado_materia", "dia", "modulos"]


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
