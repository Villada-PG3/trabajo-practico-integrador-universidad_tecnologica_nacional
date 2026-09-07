from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse # Importante para la página de inicio
from django.contrib import messages
from .models import Alumno, DictadoMateria, Inscripcion, CambioCondicion, Condicion

# --- 1. VISTA DE INICIO ---
def inicio(request):
    # Buscamos todos los alumnos para crear un menú rápido de pruebas
    alumnos = Alumno.objects.all()
    
    # Armamos un HTML básico directamente desde Python
    html = "<h1>Bienvenido al Sistema UTN</h1>"
    html += "<h3>Selecciona un alumno para probar el sistema:</h3><ul>"
    
    if alumnos.exists():
        for alumno in alumnos:
            html += f"<li><a href='/alumno/{alumno.id}/'>{alumno.nombre} {alumno.apellido} (ID: {alumno.id})</a></li>"
    else:
        html += "<li>No hay alumnos cargados en la base de datos todavía. Ve al panel de <a href='/admin/'>/admin/</a> para agregar uno.</li>"
        
    html += "</ul>"
    
    return HttpResponse(html)

# --- 2. PANEL DEL ALUMNO ---
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
    
    # Oferta académica disponible para la carrera del alumno
    dictados_disponibles = DictadoMateria.objects.filter(
        materia__carrera=alumno.carrera
    ).select_related('materia', 'curso', 'curso__turno', 'ciclo_lectivo').prefetch_related('horarios__modulos')

    if request.method == 'POST':
        dictado_id = request.POST.get('dictado_id')
        dictado = get_object_or_404(DictadoMateria, id=dictado_id)
        
        # 1. Crear la inscripción
        inscripcion = Inscripcion.objects.create(alumno=alumno, dictado_materia=dictado)
        
        # 2. Registrar condición inicial "Inscripto"
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