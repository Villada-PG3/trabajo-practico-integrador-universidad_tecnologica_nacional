from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import models

from .models import Alumno, Docente, Administrador, Horario
from .roles import obtener_rol


# ---------------------------------------------------------------------------
# Utilidades de estilo
# ---------------------------------------------------------------------------
def aplicar_estilos(form):
    """Agrega las clases de Bootstrap a todos los campos de un formulario."""
    for campo in form.fields.values():
        widget = campo.widget
        if isinstance(widget, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
            continue
        if isinstance(widget, forms.CheckboxInput):
            clase = "form-check-input"
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            clase = "form-select"
        else:
            clase = "form-control"
        widget.attrs["class"] = (widget.attrs.get("class", "") + " " + clase).strip()
    return form


def widgets_modernos(campo_modelo, **kwargs):
    """Callback para modelform_factory: usa inputs nativos de fecha/hora y checkboxes."""
    if isinstance(campo_modelo, models.ManyToManyField):
        kwargs["widget"] = forms.CheckboxSelectMultiple
    elif isinstance(campo_modelo, models.DateTimeField):
        kwargs["widget"] = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
    elif isinstance(campo_modelo, models.DateField):
        kwargs["widget"] = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    elif isinstance(campo_modelo, models.TimeField):
        kwargs["widget"] = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
    return campo_modelo.formfield(**kwargs)


# ---------------------------------------------------------------------------
# Login único
# ---------------------------------------------------------------------------
class LoginForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Usuario o contraseña incorrectos.",
        "sin_rol": "Tu usuario no tiene un perfil asignado (alumno, docente o administrador). Contactá a administración.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"placeholder": "Tu usuario", "autofocus": True})
        self.fields["password"].widget.attrs.update({"placeholder": "Tu contraseña"})
        aplicar_estilos(self)

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if obtener_rol(user) is None:
            raise forms.ValidationError(self.error_messages["sin_rol"], code="sin_rol")


# ---------------------------------------------------------------------------
# Formularios que además crean/editan la cuenta de usuario
# ---------------------------------------------------------------------------
class ConUsuarioForm(forms.ModelForm):
    username = forms.CharField(label="Usuario para iniciar sesión", max_length=150)
    password = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput(render_value=False),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuario = self.instance.usuario if self.instance.usuario_id else None
        if usuario:
            self.fields["username"].initial = usuario.username
            self.fields["password"].help_text = "Dejala vacía para mantener la contraseña actual."
        else:
            self.fields["password"].required = True
            self.fields["password"].help_text = "Mínimo 8 caracteres, no solo números."

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        repetidos = User.objects.filter(username__iexact=username)
        if self.instance.usuario_id:
            repetidos = repetidos.exclude(pk=self.instance.usuario_id)
        if repetidos.exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password)
        return password

    def save(self, commit=True):
        obj = super().save(commit=False)
        usuario = obj.usuario if obj.usuario_id else User()
        usuario.username = self.cleaned_data["username"]
        if self.cleaned_data.get("password"):
            usuario.set_password(self.cleaned_data["password"])
        usuario.save()
        obj.usuario = usuario
        obj.save()
        self.save_m2m()
        return obj


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


# ---------------------------------------------------------------------------
# Otros formularios del panel de administración
# ---------------------------------------------------------------------------
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]


class HorarioForm(forms.ModelForm):
    dia = forms.ChoiceField(choices=[(d, d) for d in DIAS], label="Día")

    class Meta:
        model = Horario
        fields = ["dictado_materia", "dia", "modulos"]
        widgets = {"modulos": forms.CheckboxSelectMultiple}


# ---------------------------------------------------------------------------
# "Mi cuenta": cada usuario cambia su nombre de usuario y su contraseña
# ---------------------------------------------------------------------------
class CuentaUsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username"]
        labels = {"username": "Nuevo nombre de usuario"}
        help_texts = {"username": "Hasta 150 caracteres. Letras, números y @ . + - _"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_estilos(self)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ese nombre de usuario ya está en uso.")
        return username


class CambiarPasswordForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].help_text = ""
        aplicar_estilos(self)
