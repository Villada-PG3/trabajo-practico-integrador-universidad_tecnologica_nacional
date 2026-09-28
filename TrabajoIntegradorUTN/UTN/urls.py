from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.inicio, name='utn'),

    path('alumno/<int:alumno_id>/', views.panel_alumno, name='panel_alumno'),
    path('alumno/<int:alumno_id>/inscribir/', views.inscribir_materia, name='inscribir_materia'),
    path('alumno/<int:alumno_id>/reporte-regulares/', views.reporte_regulares, name='reporte_regulares'),

    path('alumno/<int:alumno_id>/notas/', views.notas, name='notas'),

    path('login/', views.LoginAlumnoView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

]