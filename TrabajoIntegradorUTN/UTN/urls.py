from django.urls import path
from . import views

urlpatterns = [
    path('alumno/<int:alumno_id>/', views.panel_alumno, name='panel_alumno'),
    path('alumno/<int:alumno_id>/inscribir/', views.inscribir_materia, name='inscribir_materia'),
    path('alumno/<int:alumno_id>/reporte-regulares/', views.reporte_materias_regulares, name='reporte_regulares'),
]