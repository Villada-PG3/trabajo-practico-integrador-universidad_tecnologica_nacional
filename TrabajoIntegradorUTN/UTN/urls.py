from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

from . import views, views_admin

urlpatterns = [
    # Landing
    path("", views.landing, name="landing"),

    # Login único + redirección según el rol
    path('login/', views.LoginUnificadoView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('mi-panel/', views.redireccion_panel, name='redireccion_panel'),
    path('mi-cuenta/', views.mi_cuenta, name='mi_cuenta'),

    # Direcciones viejas: ahora redirigen al login único
    path('utn/', RedirectView.as_view(pattern_name='login', query_string=True), name='utn'),
    path('docentes/login/', RedirectView.as_view(pattern_name='login', query_string=True), name='login_docente'),

    # Panel del alumno
    path('alumno/<int:alumno_id>/', views.panel_alumno, name='panel_alumno'),
    path('alumno/<int:alumno_id>/inscribir/', views.inscribir_materia, name='inscribir_materia'),
    path('alumno/<int:alumno_id>/reporte-regulares/', views.reporte_regulares, name='reporte_regulares'),
    path('alumno/<int:alumno_id>/notas/', views.notas, name='notas'),

    # Panel del docente
    path('docentes/panel/', views.panel_docente, name='panel_docente'),

    # Panel de administración (directores y ejecutivos)
    path('administracion/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('administracion/<slug:entidad>/', views_admin.admin_lista, name='admin_lista'),
    path('administracion/<slug:entidad>/nuevo/', views_admin.admin_crear, name='admin_crear'),
    path('administracion/<slug:entidad>/<int:pk>/editar/', views_admin.admin_editar, name='admin_editar'),
    path('administracion/<slug:entidad>/<int:pk>/eliminar/', views_admin.admin_eliminar, name='admin_eliminar'),
]
