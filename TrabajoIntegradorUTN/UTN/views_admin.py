"""
Panel de administración propio (directores y ejecutivos).

Son 5 vistas genéricas (dashboard, listar, crear, editar, eliminar). Sirven para TODAS las
entidades: cada una se describe en entidades.py y la URL dice cuál se está administrando.
"""
from django.contrib import messages
from django.db.models import ProtectedError, Q
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .entidades import ENTIDADES
from .forms import ModeloForm
from .models import Inscripcion
from .roles import RolRequeridoMixin, es_director, ROL_ADMIN


def valor_de(obj, ruta):
    """Resuelve 'carrera.sigla', métodos (get_cargo_display) y relaciones muchos-a-muchos."""
    valor = obj
    for parte in ruta.split("."):
        if valor is None:
            return None
        valor = getattr(valor, parte, None)
        if callable(valor) and not hasattr(valor, "all"):
            valor = valor()
    if hasattr(valor, "all"):  # ManyToMany
        return ", ".join(str(v) for v in valor.all()) or None
    return valor


class AdminMixin(RolRequeridoMixin):
    """Solo administradores. En las vistas de una entidad, además, la busca en entidades.py."""
    roles = (ROL_ADMIN,)

    def test_func(self):
        if not super().test_func():
            return False
        clave = self.kwargs.get("entidad")
        if clave is None:  # el dashboard no tiene entidad
            return True
        if clave not in ENTIDADES:
            raise Http404("Sección inexistente")
        if self.conf.get("solo_director") and not es_director(self.request.user):
            self.mensaje_denegado = "Solo un director puede gestionar administradores."
            return False
        return True

    @cached_property
    def conf(self):
        return ENTIDADES[self.kwargs["entidad"]]

    def get_context_data(self, **kwargs):
        entidad = self.kwargs.get("entidad")
        return super().get_context_data(conf=self.conf if entidad else None, entidad=entidad,
                                        seccion_activa=entidad or "dashboard", **kwargs)

    def get_queryset(self):
        return self.conf["modelo"].objects.all()

    def get_success_url(self):
        return reverse("utn:admin_lista", kwargs={"entidad": self.kwargs["entidad"]})


class DashboardView(AdminMixin, TemplateView):
    template_name = "admin_dashboard.html"

    def get_context_data(self, **kwargs):
        tarjetas = [
            {"clave": clave, "titulo": ENTIDADES[clave]["titulo"], "icono": ENTIDADES[clave]["icono"],
             "cantidad": ENTIDADES[clave]["modelo"].objects.count()}
            for clave in ["alumnos", "docentes", "carreras", "materias", "cursos", "turnos", "dictados", "inscripciones"]
        ]
        ultimas = Inscripcion.objects.select_related("alumno", "dictado_materia__materia").order_by("-fecha_inscripcion", "-id")[:6]
        return super().get_context_data(tarjetas=tarjetas, ultimas_inscripciones=ultimas, **kwargs)


class EntidadListView(AdminMixin, ListView):
    template_name = "admin_lista.html"
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().order_by("-id")
        self.q = self.request.GET.get("q", "").strip()
        if self.q:
            filtro = Q()
            for campo in self.conf["busqueda"]:
                filtro |= Q(**{f"{campo}__icontains": self.q})
            qs = qs.filter(filtro).distinct()
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(q=self.q, **kwargs)
        columnas = self.conf["columnas"]
        contexto["filas"] = [{"obj": obj, "valores": [valor_de(obj, ruta) for ruta, _ in columnas]}
                             for obj in contexto["page_obj"]]
        return contexto


class FormularioEntidadMixin(AdminMixin):
    """Lo que comparten crear y editar: el formulario y el mensaje de éxito."""
    template_name = "admin_form.html"

    def get_form_class(self):
        # Si la entidad tiene un formulario propio (alumnos, docentes...) se usa; si no, Django lo arma solo.
        return self.conf.get("form") or modelform_factory(self.conf["modelo"], form=ModeloForm, fields="__all__")

    def get_context_data(self, **kwargs):
        return super().get_context_data(instancia=self.object, **kwargs)

    def form_valid(self, form):
        respuesta = super().form_valid(form)  # guarda el objeto
        accion = "actualizado" if isinstance(self, UpdateView) else "creado"
        messages.success(self.request, f"{self.conf['singular'].capitalize()} «{self.object}» {accion} correctamente.")
        if "guardar_y_otro" in self.request.POST:
            return redirect("utn:admin_crear", entidad=self.kwargs["entidad"])
        return respuesta


class EntidadCreateView(FormularioEntidadMixin, CreateView):
    pass


class EntidadUpdateView(FormularioEntidadMixin, UpdateView):
    pass


class EntidadDeleteView(AdminMixin, DeleteView):
    template_name = "admin_confirmar_eliminar.html"

    def form_valid(self, form):
        obj, nombre = self.object, str(self.object)
        if getattr(obj, "usuario_id", None) == self.request.user.id:
            messages.error(self.request, "No podés eliminar tu propio usuario.")
            return redirect(self.get_success_url())
        try:
            usuario = getattr(obj, "usuario", None) if hasattr(obj, "usuario_id") else None
            obj.delete()
            if usuario is not None:
                usuario.delete()  # borra también la cuenta para iniciar sesión
            messages.success(self.request, f"«{nombre}» se eliminó correctamente.")
        except ProtectedError as error:  # on_delete=PROTECT: algo lo está usando
            usados = sorted({str(o._meta.verbose_name_plural) for o in error.protected_objects})
            messages.error(self.request, f"No se puede eliminar «{nombre}» porque está siendo usado en: "
                                         f"{', '.join(usados)}. Primero eliminá o modificá esos registros.")
        return redirect(self.get_success_url())
