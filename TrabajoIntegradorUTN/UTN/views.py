from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse 
from django.contrib import messages
from .models import Alumno, DictadoMateria, Inscripcion, CambioCondicion, Condicion, Carrera, Evaluacion, TipoEvaluacion
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.db import transaction, IntegrityError
from decimal import Decimal, InvalidOperation
from django.core.exceptions import PermissionDenied
from django.utils import timezone

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




def inscribir_materia(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    dictados = DictadoMateria.objects.filter(
        materia__carrera=alumno.carrera
    ).select_related('materia', 'curso', 'curso__turno', 'ciclo_lectivo').prefetch_related('horarios__modulos')


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

    if request.method != 'POST':
        return render(request, 'UTN/inscribir.html', {'alumno': alumno, 'dictados': dictados})


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
    
    
    
    
def landing(request):
    iconos_carrera = [
        "bi-building",
        "bi-lightning-charge",
        "bi-cpu",
        "bi-gear",
        "bi-tools",
        "bi-bezier2",
        "bi-boxes",
        "bi-code-slash",
    ]
    carreras = [
        {
            "nombre": carrera.nombre,
            "sigla": carrera.sigla,
            "icono": iconos_carrera[indice % len(iconos_carrera)],
        }
        for indice, carrera in enumerate(Carrera.objects.all().order_by("nombre"))
    ]
    if not carreras:
        carreras = [
            {"nombre": "Ingeniería Civil", "sigla": "IC", "icono": "bi-building"},
            {"nombre": "Ingeniería Eléctrica", "sigla": "IE", "icono": "bi-lightning-charge"},
            {"nombre": "Ingeniería Electrónica", "sigla": "IE", "icono": "bi-cpu"},
            {"nombre": "Ingeniería Industrial", "sigla": "II", "icono": "bi-gear"},
            {"nombre": "Ingeniería Mecánica", "sigla": "IM", "icono": "bi-tools"},
            {"nombre": "Ingeniería Metalúrgica", "sigla": "IM", "icono": "bi-bezier2"},
            {"nombre": "Ingeniería Química", "sigla": "IQ", "icono": "bi-boxes"},
            {"nombre": "Ingeniería en Sistemas de Información", "sigla": "ISI", "icono": "bi-code-slash"},
        ]

    fotos = [
        {"url": "static/UTN/media/img-utn-patio.webp", "alt": "Patio de la UTN Facultad Regional Córdoba"},
        {"url": "static/UTN/media/1-23.jpg", "alt": "Espacios universitarios"},
        {"url": "static/UTN/media/IMG_20130311_191734.jpg", "alt": "Actividad en las aulas"},
        {"url": "static/UTN/media/images (1).jpg", "alt": "Ciudad Universitaria de Córdoba"},
    ]
    noticias = [
        {"categoria": "Comunidad", "titulo": "5.ª Marcha Federal Universitaria",
         "resumen": "La comunidad tecnológica participó de la jornada por la educación, la soberanía y la democracia."},
        {"categoria": "Ingeniería Nuclear", "titulo": "Visita a la Central Nuclear Embalse",
         "resumen": "Una delegación de la UTN Córdoba recorrió una instalación clave del sistema energético argentino."},
        {"categoria": "Ingeniería en Sistemas", "titulo": "Presentación de proyectos finales",
         "resumen": "Estudiantes compartieron sus trabajos en una nueva jornada de proyectos de carrera."},
    ]
    eventos = [
        {"fecha": "26 OCT", "tipo": "Conferencia", "titulo": "Ingeniería en la vida real: de la UTN a Vaca Muerta",
         "detalle": "Hoy · 17:00 · Sala Agustín Tosco · Presencial"},
        {"fecha": "27 OCT", "tipo": "Charla", "titulo": "Campus France Argentina / DAAD",
         "detalle": "18:30 · Kultur Ensemble Córdoba · Presencial"},
        {"fecha": "28 OCT", "tipo": "Innovación", "titulo": "Llega Hack 2 Future",
         "detalle": "08:45 · SUM Lic. Alicia Delgado · Presencial"},
    ]
    formaciones = [
        {"tipo": "Curso", "titulo": "Flujo subterráneo con MODFLOW",
         "detalle": "Inicia el 26 de octubre · Modalidad online"},
        {"tipo": "Curso", "titulo": "Herramientas de Design Thinking",
         "detalle": "Inicia el 6 de noviembre · Modalidad presencial"},
        {"tipo": "Workshop", "titulo": "Desarrollo profesional de mandos medios",
         "detalle": "Inicia el 11 de noviembre · Modalidad presencial"},
    ]
    entrevistas = [
        {"persona": "Ing. Lucía Angeleri",
         "titulo": "Investigación, innovación y una experiencia internacional",
         "resumen": "Graduada de la UTN FRC, realizó investigación en nanotecnología y obtuvo una beca Marie Curie para doctorarse en Madrid."},
        {"persona": "Dr. Ing. Guillermo Gilberto",
         "titulo": "Un audiojuego para percibir el espacio",
         "resumen": "El investigador desarrolló una experiencia de realidad virtual como parte de su tesis doctoral en Ingeniería Electrónica."},
        {"persona": "Dr. Martín Pucheta",
         "titulo": "Ingeniería aplicada al automovilismo",
         "resumen": "Director de una especialización de posgrado pionera en Latinoamérica, dictada en nuestra Facultad."},
    ]
    context = {
        "carreras": carreras,
        "fotos": fotos,
        "noticias": noticias,
        "eventos": eventos,
        "formaciones": formaciones,
        "entrevistas": entrevistas,
    }
    return render(request, "UTN/landing.html", context)



class LoginDocenteView(LoginView):
    template_name = 'UTN/login.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Acceso docentes'
        ctx['subtitulo'] = 'Ingresá con tu usuario para calificar a tus alumnos.'
        return ctx

    def form_valid(self, form):
        # Credenciales correctas pero no es docente (ej: un alumno) -> no lo dejamos pasar
        if not hasattr(form.get_user(), 'docente'):
            form.add_error(None, "Este usuario no está registrado como docente.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('panel_docente')


def _a_int(valor):
    return int(valor) if valor and valor.isdigit() else None


@login_required(login_url='login_docente')
def panel_docente(request):
    docente = getattr(request.user, 'docente', None)
    if docente is None:
        raise PermissionDenied  # muestra tu página 403

    dictados = (docente.dictados
                .select_related('materia', 'curso', 'curso__turno', 'ciclo_lectivo')
                .order_by('-ciclo_lectivo__anio', 'materia__nombre'))
    tipos = TipoEvaluacion.objects.all()

    # Tanto en GET (?dictado=1&tipo=2) como en POST (campos ocultos)
    dictado_id = _a_int(request.POST.get('dictado_id') or request.GET.get('dictado'))
    tipo_id = _a_int(request.POST.get('tipo_id') or request.GET.get('tipo'))

    dictado = get_object_or_404(dictados, id=dictado_id) if dictado_id else None  # solo SUS cursos
    tipo = get_object_or_404(tipos, id=tipo_id) if tipo_id else tipos.first()

    filas = []
    if dictado and tipo:
        inscripciones = list(
            dictado.inscripciones.select_related('alumno').order_by('alumno__nombre_completo')
        )

        if request.method == 'POST':
            errores = 0
            with transaction.atomic():
                for insc in inscripciones:
                    raw = request.POST.get(f'nota_{insc.id}')
                    if raw is None:
                        continue  # alumno inscripto después de cargar la página
                    existente = Evaluacion.objects.filter(
                        inscripcion=insc, tipo_evaluacion=tipo
                    ).first()

                    if raw == '':  # Pendiente
                        if existente:
                            existente.delete()
                        continue

                    try:
                        valor = Decimal(raw)
                    except InvalidOperation:
                        errores += 1
                        continue
                    if not (1 <= valor <= 10):
                        errores += 1
                        continue

                    if existente:
                        existente.valor = valor
                        existente.docente = docente
                        existente.fecha_evaluacion = timezone.localdate()
                        existente.save()
                    else:
                        Evaluacion.objects.create(
                            inscripcion=insc, tipo_evaluacion=tipo, docente=docente,
                            valor=valor, fecha_evaluacion=timezone.localdate(),
                        )

            if errores:
                messages.warning(request, f"Se guardaron las notas, pero {errores} valor(es) no eran válidos.")
            else:
                messages.success(request, "Notas guardadas correctamente.")
            return redirect(f"{reverse('panel_docente')}?dictado={dictado.id}&tipo={tipo.id}")

        notas = {
            e.inscripcion_id: e.valor
            for e in Evaluacion.objects.filter(inscripcion__dictado_materia=dictado, tipo_evaluacion=tipo)
        }
        filas = [{'inscripcion': i, 'alumno': i.alumno, 'nota': notas.get(i.id)} for i in inscripciones]

    return render(request, 'UTN/panel_docente.html', {
        'docente': docente,
        'dictados': dictados,
        'tipos': tipos,
        'dictado': dictado,
        'tipo': tipo,
        'filas': filas,
        'escala': range(1, 11),
    })