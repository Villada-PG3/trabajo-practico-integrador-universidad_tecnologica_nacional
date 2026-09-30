from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse 
from django.contrib import messages
from .models import Alumno, DictadoMateria, Inscripcion, CambioCondicion, Condicion
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.db import transaction, IntegrityError

def inicio(request):
    return render(request, 'UTN/utn.html', {'alumnos': Alumno.objects.all()})

@login_required
def panel_alumno(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    inscripciones = Inscripcion.objects.filter(alumno=alumno).prefetch_related('evaluaciones', 'historial_condiciones')
    return render(request, 'UTN/panel_alumno.html', {
        'alumno': alumno,
        'inscripciones': inscripciones
    })

<<<<<<< HEAD
# --- 3. INSCRIBIR MATERIA ---


=======
>>>>>>> origin/develop
def inscribir_materia(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    dictados = DictadoMateria.objects.filter(
        materia__carrera=alumno.carrera
    ).select_related('materia', 'curso', 'curso__turno', 'ciclo_lectivo').prefetch_related('horarios__modulos')

<<<<<<< HEAD
    if request.method == 'POST':
        dictado_id = request.POST.get('dictado_id')
        dictado = get_object_or_404(dictados_disponibles, id=dictado_id)

        if Inscripcion.objects.filter(alumno=alumno, dictado_materia=dictado).exists():
            messages.warning(request, "Ya estás inscripto en esta materia.")
            return redirect('inscribir_materia', alumno_id=alumno.id)

        try:
            with transaction.atomic():
                inscripcion = Inscripcion.objects.create(alumno=alumno, dictado_materia=dictado)
                condicion_inscripto, _ = Condicion.objects.get_or_create(
                    nombre="Inscripto", defaults={'es_condicion_final': False}
                )
                CambioCondicion.objects.create(inscripcion=inscripcion, condicion=condicion_inscripto)
        except IntegrityError:
            messages.warning(request, "Ya estás inscripto en esta materia.")
            return redirect('inscribir_materia', alumno_id=alumno.id)

        messages.success(request, f"¡Inscripción exitosa! Tu código es: {inscripcion.codigo_inscripcion}")
        return redirect('panel_alumno', alumno_id=alumno.id)
=======
    if request.method != 'POST':
        return render(request, 'UTN/inscribir.html', {'alumno': alumno, 'dictados': dictados})
>>>>>>> origin/develop

    dictado = get_object_or_404(DictadoMateria, id=request.POST.get('dictado_id'))
    inscripcion = Inscripcion.objects.create(alumno=alumno, dictado_materia=dictado)
    condicion, _ = Condicion.objects.get_or_create(nombre="Inscripto", defaults={'es_condicion_final': False})
    CambioCondicion.objects.create(inscripcion=inscripcion, condicion=condicion)
    
    messages.success(request, f"¡Inscripción exitosa! Tu código es: {inscripcion.codigo_inscripcion}")
    return redirect('panel_alumno', alumno_id=alumno.id)

def reporte_regulares(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    inscripciones = Inscripcion.objects.filter(alumno=alumno).prefetch_related(
        'historial_condiciones__condicion',
        'dictado_materia__materia',
        'dictado_materia__curso'
    )
    
    regulares = []
    for insc in inscripciones:
        historial = list(insc.historial_condiciones.all())
        if not historial:
            continue
            
        ultimo_cambio = sorted(historial, key=lambda c: c.fecha_hora, reverse=True)[0]
        if ultimo_cambio.condicion.nombre == "Regular":
            regulares.append({
                'materia': insc.dictado_materia.materia.nombre,
                'curso': insc.dictado_materia.curso.nombre,
                'condicion': "Regular",
                'fecha_regularizacion': ultimo_cambio.fecha_hora
            })
            
    return render(request, 'UTN/reporte_regulares.html', {'alumno': alumno, 'regulares': regulares})

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

