from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from . import views, views_admin, views_docente

app_name = "utn"

urlpatterns = [
    path("", views.landing, name="landing"),

    # Login único + redirección según el rol
    path("login/", views.LoginUnificadoView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("mi-panel/", views.redireccion_panel, name="redireccion_panel"),
    path("mi-cuenta/", views.CuentaUsuarioView.as_view(), name="mi_cuenta"),
    path("mi-cuenta/contrasena/", views.CuentaPasswordView.as_view(), name="mi_cuenta_password"),

    # Direcciones viejas: ahora redirigen al login único
    path("utn/", RedirectView.as_view(pattern_name="utn:login", query_string=True)),
    path("docentes/login/", RedirectView.as_view(pattern_name="utn:login", query_string=True)),

    # Panel del alumno
    path("alumno/<int:pk>/", views.PanelAlumnoView.as_view(), name="panel_alumno"),
    path("alumno/<int:pk>/inscribir/", views.InscribirView.as_view(), name="inscribir_materia"),
    path("alumno/<int:pk>/reporte-regulares/", views.ReporteRegularesView.as_view(), name="reporte_regulares"),

    # Panel del docente
    path("docentes/panel/", views_docente.PanelDocenteView.as_view(), name="panel_docente"),

    # Panel de administración (directores y ejecutivos)
    path("administracion/", views_admin.DashboardView.as_view(), name="admin_dashboard"),
    path("administracion/<slug:entidad>/", views_admin.EntidadListView.as_view(), name="admin_lista"),
    path("administracion/<slug:entidad>/nuevo/", views_admin.EntidadCreateView.as_view(), name="admin_crear"),
    path("administracion/<slug:entidad>/<int:pk>/editar/", views_admin.EntidadUpdateView.as_view(), name="admin_editar"),
    path("administracion/<slug:entidad>/<int:pk>/eliminar/", views_admin.EntidadDeleteView.as_view(), name="admin_eliminar"),
]
