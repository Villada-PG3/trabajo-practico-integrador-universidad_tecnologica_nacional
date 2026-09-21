from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse 
from django.contrib import messages
from .models import Alumno, DictadoMateria, Inscripcion, CambioCondicion, Condicion
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse

# --- 1. VISTA DE INICIO ---
def inicio(request):
    alumnos = Alumno.objects.all()
    
    return render(request, 'UTN/utn.html', {'alumnos': alumnos})

# --- 2. PANEL DEL ALUMNO ---
@login_required
def panel_alumno(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    inscripciones = Inscripcion.objects.filter(alumno=alumno).prefetch_related('evaluaciones', 'historial_condiciones')
    return render(request, 'UTN/panel_alumno.html', {
        'alumno': alumno,
        'inscripciones': inscripciones
    })

# --- 3. INSCRIBIR MATERIA ---
def inscribir_materia(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    dictados_disponibles = DictadoMateria.objects.filter(
        materia__carrera=alumno.carrera
    ).select_related('materia', 'curso', 'curso__turno', 'ciclo_lectivo').prefetch_related('horarios__modulos')

    if request.method == 'POST':
        dictado_id = request.POST.get('dictado_id')
        dictado = get_object_or_404(DictadoMateria, id=dictado_id)
        inscripcion = Inscripcion.objects.create(alumno=alumno, dictado_materia=dictado)
        condicion_inscripto, _ = Condicion.objects.get_or_create(nombre="Inscripto", defaults={'es_condicion_final': False})
        CambioCondicion.objects.create(inscripcion=inscripcion, condicion=condicion_inscripto)
        
        messages.success(request, f"¡Inscripción exitosa! Tu código es: {inscripcion.codigo_inscripcion}")
        return redirect('panel_alumno', alumno_id=alumno.id)

    return render(request, 'UTN/inscribir.html', {
        'alumno': alumno,
        'dictados': dictados_disponibles
    })

# --- 4. REPORTE DE REGULARES ---
def reporte_regulares(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    inscripciones = Inscripcion.objects.filter(alumno=alumno)
    
    regulares = []
    for insc in inscripciones:
        ultimo_cambio = insc.historial_condiciones.order_by('-fecha_hora').first()
        if ultimo_cambio and ultimo_cambio.condicion.nombre == "Regular":
            regulares.append({
                'materia': insc.dictado_materia.materia.nombre,
                'curso': insc.dictado_materia.curso.nombre,
                'condicion': ultimo_cambio.condicion.nombre,
                'fecha_regularizacion': ultimo_cambio.fecha_hora
            })
            
    return render(request, 'UTN/reporte_regulares.html', {
        'alumno': alumno,
        'regulares': regulares
    })
    

def notas(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    inscripciones = Inscripcion.objects.filter(alumno=alumno)
    
    return render(request, 'UTN/notas.html', {
        'alumno': alumno,
        'inscripciones': inscripciones
    })



    
class LoginAlumnoView(LoginView):
    template_name = 'UTN/login.html'

    def get_success_url(self):
        alumno = getattr(self.request.user, 'alumno', None)
        if alumno:
            return reverse('panel_alumno', args=[alumno.id])
        return '/admin/'

