from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from .forms import LoginForm, CuentaUsuarioForm, CambiarPasswordForm
from .models import (
    Alumno, DictadoMateria, Inscripcion, CambioCondicion, Condicion,
    Carrera, Evaluacion, TipoEvaluacion, InstanciaEvaluacion,
)
from .roles import obtener_rol, rol_requerido, ROL_ADMIN, ROL_DOCENTE, ROL_ALUMNO


# ---------------------------------------------------------------------------
# Landing
# ---------------------------------------------------------------------------
ICONOS_CARRERA = [
    ("sistemas", "bi-cpu"),
    ("electr", "bi-motherboard"),
    ("eléctr", "bi-lightning-charge"),
    ("industrial", "bi-gear-wide-connected"),
    ("mecánica", "bi-tools"),
    ("mecanica", "bi-tools"),
    ("civil", "bi-building"),
    ("química", "bi-droplet-half"),
    ("quimica", "bi-droplet-half"),
    ("metal", "bi-fire"),
    ("aero", "bi-airplane"),
]


def _icono_carrera(nombre):
    nombre = nombre.lower()
    for palabra, icono in ICONOS_CARRERA:
        if palabra in nombre:
            return icono
    return "bi-mortarboard"


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


# ---------------------------------------------------------------------------
# Login único + redirección según el rol
# ---------------------------------------------------------------------------
class LoginUnificadoView(LoginView):
    template_name = 'UTN/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return reverse('redireccion_panel')


@login_required
def redireccion_panel(request):
    """Después del login, manda a cada usuario a su panel según su rol."""
    rol = obtener_rol(request.user)
    if rol == ROL_ADMIN:
        return redirect('admin_dashboard')
    if rol == ROL_DOCENTE:
        return redirect('panel_docente')
    if rol == ROL_ALUMNO:
        return redirect('panel_alumno', alumno_id=request.user.alumno.id)

    logout(request)
    messages.error(request, "Tu usuario no tiene un perfil asignado. Contactá a administración.")
    return redirect('login')


# ---------------------------------------------------------------------------
# Mi cuenta (alumnos, docentes y administradores)
# ---------------------------------------------------------------------------
@login_required
def mi_cuenta(request):
    form_usuario = CuentaUsuarioForm(instance=request.user, prefix='u')
    form_password = CambiarPasswordForm(request.user, prefix='p')

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'usuario':
            form_usuario = CuentaUsuarioForm(request.POST, instance=request.user, prefix='u')
            if form_usuario.is_valid():
                form_usuario.save()
                messages.success(request, f"Listo, tu nuevo usuario es «{request.user.username}».")
                return redirect('mi_cuenta')
        elif accion == 'password':
            form_password = CambiarPasswordForm(request.user, request.POST, prefix='p')
            if form_password.is_valid():
                usuario = form_password.save()
                update_session_auth_hash(request, usuario)  # para que no se cierre la sesión
                messages.success(request, "Tu contraseña se cambió correctamente.")
                return redirect('mi_cuenta')

    contexto = {
        'form_usuario': form_usuario,
        'form_password': form_password,
        'base_template': 'UTN/base.html',
    }
    if obtener_rol(request.user) == ROL_ADMIN:
        from .views_admin import _menu
        contexto.update(base_template='UTN/admin_panel/base_admin.html', menu=_menu(request))
    return render(request, 'UTN/mi_cuenta.html', contexto)


# ---------------------------------------------------------------------------
# Panel del alumno
# ---------------------------------------------------------------------------
def _alumno_autorizado(request, alumno_id):
    """El alumno solo puede ver lo suyo. El administrador puede ver a cualquiera."""
    alumno = get_object_or_404(Alumno, id=alumno_id)
    if obtener_rol(request.user) == ROL_ADMIN or alumno.usuario_id == request.user.id:
        return alumno
    raise PermissionDenied


@rol_requerido(ROL_ALUMNO, ROL_ADMIN)
def panel_alumno(request, alumno_id):
    alumno = _alumno_autorizado(request, alumno_id)
    inscripciones = Inscripcion.objects.filter(alumno=alumno).prefetch_related('evaluaciones', 'historial_condiciones')
    return render(request, 'UTN/panel_alumno.html', {
        'alumno': alumno,
        'inscripciones': inscripciones
    })


@rol_requerido(ROL_ALUMNO, ROL_ADMIN)
def inscribir_materia(request, alumno_id):
    alumno = _alumno_autorizado(request, alumno_id)
    dictados = DictadoMateria.objects.filter(
        materia__carrera=alumno.carrera
    ).select_related('materia', 'curso', 'curso__turno', 'ciclo_lectivo').prefetch_related('horarios__modulos')

    if request.method != 'POST':
        return render(request, 'UTN/inscribir.html', {'alumno': alumno, 'dictados': dictados})

    dictado = get_object_or_404(dictados, id=request.POST.get('dictado_id'))

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


@rol_requerido(ROL_ALUMNO, ROL_ADMIN)
def reporte_regulares(request, alumno_id):
    alumno = _alumno_autorizado(request, alumno_id)
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


@rol_requerido(ROL_ALUMNO, ROL_ADMIN)
def notas(request, alumno_id):
    alumno = _alumno_autorizado(request, alumno_id)
    inscripciones = Inscripcion.objects.filter(alumno=alumno).select_related('dictado_materia__materia', 'dictado_materia__curso').prefetch_related('evaluaciones__instancia', 'evaluaciones__tipo_evaluacion')

    return render(request, 'UTN/notas.html', {
        'alumno': alumno,
        'inscripciones': inscripciones
    })


# ---------------------------------------------------------------------------
# Panel del docente
# ---------------------------------------------------------------------------
def _a_int(valor):
    return int(valor) if valor and valor.isdigit() else None


def _condiciones_actuales(inscripciones):
    """Devuelve {inscripcion_id: condicion_id} con la última condición de cada inscripción."""
    actuales = {}
    cambios = (CambioCondicion.objects
               .filter(inscripcion__in=inscripciones)
               .order_by('inscripcion_id', 'fecha_hora', 'id'))
    for cambio in cambios:
        actuales[cambio.inscripcion_id] = cambio.condicion_id  # el último pisa a los anteriores
    return actuales


def _parsear_nota(raw):
    """Acepta '8', '8.5' o '8,5'. Devuelve Decimal o None si no es válida (1 a 10)."""
    try:
        valor = Decimal(raw.replace(',', '.'))
    except InvalidOperation:
        return None
    return valor if Decimal('1') <= valor <= Decimal('10') else None


def _nota_texto(valor):
    """Decimal('7.50') -> '7,5' ; Decimal('8.00') -> '8' (como se escribe a mano)."""
    texto = f"{valor:f}"
    if '.' in texto:
        texto = texto.rstrip('0').rstrip('.')
    return texto.replace('.', ',')


def _parsear_fecha(raw):
    try:
        return date.fromisoformat(raw)
    except (TypeError, ValueError):
        return timezone.localdate()


@rol_requerido(ROL_DOCENTE)
def panel_docente(request):
    docente = request.user.docente

    dictados = (docente.dictados
                .select_related('materia', 'curso', 'curso__turno', 'ciclo_lectivo')
                .order_by('-ciclo_lectivo__anio', 'materia__nombre'))
    tipos = TipoEvaluacion.objects.all()
    condiciones = Condicion.objects.all().order_by('id')

    # Solo se elige el curso. Si no se eligió ninguno, se abre el primero.
    dictado_id = _a_int(request.POST.get('dictado_id') or request.GET.get('dictado'))
    dictado = get_object_or_404(dictados, id=dictado_id) if dictado_id else dictados.first()  # solo SUS cursos

    contexto = {
        'docente': docente,
        'dictados': dictados,
        'tipos': tipos,
        'condiciones': condiciones,
        'dictado': dictado,
        'hoy': timezone.localdate(),
    }
    if dictado is None:
        return render(request, 'UTN/panel_docente.html', contexto)

    inscripciones = list(dictado.inscripciones.select_related('alumno').order_by('alumno__nombre_completo'))
    ids_inscripciones = {i.id for i in inscripciones}
    columnas = list(dictado.instancias_evaluacion
                    .select_related('tipo_evaluacion')
                    .prefetch_related('inscripciones'))
    for col in columnas:
        col.ids_alumnos = {i.id for i in col.inscripciones.all()}
    condicion_actual = _condiciones_actuales(inscripciones)
    notas = {
        (e.instancia_id, e.inscripcion_id): e
        for e in Evaluacion.objects.filter(instancia__in=columnas)
    }

    def aplica(col, insc_id):
        return col.para_todos or insc_id in col.ids_alumnos

    if request.method == 'POST':
        accion = request.POST.get('accion', 'guardar')
        errores = cambios_notas = cambios_condicion = 0
        condiciones_validas = {c.id: c for c in condiciones}

        with transaction.atomic():
            # 1) Siempre se guarda la planilla (así no se pierde lo que se tipeó)
            for col in columnas:
                for insc in inscripciones:
                    if not aplica(col, insc.id):
                        continue
                    raw = request.POST.get(f'nota_{col.id}_{insc.id}')
                    if raw is None:  # alumno inscripto después de cargar la página
                        continue
                    raw = raw.strip()
                    existente = notas.get((col.id, insc.id))
                    if raw == '':
                        if existente:
                            existente.delete()
                            cambios_notas += 1
                        continue
                    valor = _parsear_nota(raw)
                    if valor is None:
                        errores += 1
                    elif existente is None:
                        Evaluacion.objects.create(
                            inscripcion=insc, instancia=col, tipo_evaluacion=col.tipo_evaluacion,
                            docente=docente, valor=valor, fecha_evaluacion=col.fecha,
                        )
                        cambios_notas += 1
                    elif existente.valor != valor:
                        existente.valor = valor
                        existente.docente = docente
                        existente.save(update_fields=['valor', 'docente'])
                        cambios_notas += 1


            for insc in inscripciones:
                nueva = _a_int(request.POST.get(f'condicion_{insc.id}'))
                if nueva and nueva in condiciones_validas and nueva != condicion_actual.get(insc.id):
                    CambioCondicion.objects.create(
                        inscripcion=insc, condicion=condiciones_validas[nueva], docente=docente,
                    )
                    cambios_condicion += 1

            # 2) Acciones sobre columnas
            if accion == 'guardar_columna':
                tipo = tipos.filter(id=_a_int(request.POST.get('col_tipo'))).first()
                alcance = request.POST.get('col_alcance', 'todos')
                elegidos = {_a_int(x) for x in request.POST.getlist('col_alumnos')} & ids_inscripciones
                col_id = _a_int(request.POST.get('col_id'))
                columna = next((c for c in columnas if c.id == col_id), None) if col_id else None

                if tipo is None:
                    messages.error(request, "Elegí el tipo de evaluación de la columna.")
                elif alcance == 'algunos' and not elegidos:
                    messages.error(request, "Elegí al menos un alumno para la evaluación.")
                else:
                    es_nueva = columna is None
                    if es_nueva:
                        columna = InstanciaEvaluacion(dictado_materia=dictado, creada_por=docente)
                    columna.tipo_evaluacion = tipo
                    columna.nombre = request.POST.get('col_nombre', '').strip()[:80]
                    columna.fecha = _parsear_fecha(request.POST.get('col_fecha'))
                    columna.para_todos = alcance != 'algunos'
                    columna.save()
                    columna.inscripciones.set([] if columna.para_todos else elegidos)
                    if not es_nueva:
                        # las notas existentes acompañan el nuevo tipo/fecha
                        columna.notas.update(tipo_evaluacion=tipo, fecha_evaluacion=columna.fecha)
                        if not columna.para_todos:  # se sacaron alumnos: se borran sus notas
                            columna.notas.exclude(inscripcion_id__in=elegidos).delete()
                    if es_nueva:
                        messages.success(request, f"Columna «{columna.titulo}» agregada. Ya podés cargar las notas.")
                    else:
                        messages.success(request, f"Columna «{columna.titulo}» actualizada.")

            elif accion == 'eliminar_columna':
                col_id = _a_int(request.POST.get('col_id'))
                columna = next((c for c in columnas if c.id == col_id), None)
                if columna:
                    titulo = columna.titulo
                    columna.delete()  # borra también sus notas
                    messages.success(request, f"Se eliminó la columna «{titulo}» y sus notas.")

        resumen = []
        if cambios_notas:
            resumen.append(f"{cambios_notas} nota(s) guardada(s)")
        if cambios_condicion:
            resumen.append(f"{cambios_condicion} condición(es) actualizada(s)")
        if errores:
            messages.warning(request, f"{errores} nota(s) no se guardaron: tienen que ser números entre 1 y 10.")
        if resumen:
            messages.success(request, "Planilla guardada: " + " y ".join(resumen) + ".")
        elif accion == 'guardar' and not errores:
            messages.info(request, "No había cambios para guardar.")
        return redirect(f"{reverse('panel_docente')}?dictado={dictado.id}")

    filas = []
    for insc in inscripciones:
        celdas, valores = [], []
        for col in columnas:
            ev = notas.get((col.id, insc.id))
            celdas.append({
                'columna': col,
                'aplica': aplica(col, insc.id),
                'nota': _nota_texto(ev.valor) if ev else '',
            })
            if ev:
                valores.append(ev.valor)
        filas.append({
            'inscripcion': insc,
            'alumno': insc.alumno,
            'celdas': celdas,
            'promedio': (sum(valores) / len(valores)) if valores else None,
            'condicion_id': condicion_actual.get(insc.id),
        })

    contexto.update(columnas=columnas, filas=filas, inscripciones=inscripciones)
    return render(request, 'UTN/panel_docente.html', contexto)
