"""Panel del docente: una planilla (alumnos en filas, evaluaciones en columnas) por cada curso."""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic import TemplateView

from .forms import ColumnaForm
from .models import CambioCondicion, Condicion, Evaluacion, InstanciaEvaluacion, TipoEvaluacion
from .roles import RolRequeridoMixin, ROL_DOCENTE


def a_int(valor):
    return int(valor) if valor and valor.isdigit() else None


def parsear_nota(texto):
    """Acepta '8', '8.5' u '8,5'. Devuelve un Decimal entre 1 y 10, o None si no es válida."""
    try:
        valor = Decimal(texto.replace(",", "."))
    except InvalidOperation:
        return None
    return valor if Decimal(1) <= valor <= Decimal(10) else None


def nota_a_texto(valor):
    """Decimal('7.50') -> '7,5' y Decimal('8.00') -> '8' (como se escribe a mano)."""
    texto = f"{valor:f}"
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(".", ",")


class PanelDocenteView(RolRequeridoMixin, TemplateView):
    roles = (ROL_DOCENTE,)
    template_name = "panel_docente.html"

    # --- Datos de la planilla (cada uno se calcula una sola vez por request) ---
    @cached_property
    def docente(self):
        return self.request.user.docente

    @cached_property
    def dictados(self):
        return (self.docente.dictados
                .select_related("materia", "curso__turno", "ciclo_lectivo")
                .order_by("-ciclo_lectivo__anio", "materia__nombre"))  # solo SUS cursos

    @cached_property
    def dictado(self):
        """El curso elegido. Si no se eligió ninguno, el primero."""
        dictado_id = a_int(self.request.POST.get("dictado_id") or self.request.GET.get("dictado"))
        return get_object_or_404(self.dictados, pk=dictado_id) if dictado_id else self.dictados.first()

    @cached_property
    def inscripciones(self):
        return list(self.dictado.inscripciones
                    .select_related("alumno")
                    .prefetch_related("historial_condiciones")
                    .order_by("alumno__nombre_completo"))

    @cached_property
    def columnas(self):
        columnas = list(self.dictado.instancias_evaluacion.select_related("tipo_evaluacion").prefetch_related("inscripciones"))
        for columna in columnas:
            columna.ids_alumnos = {i.id for i in columna.inscripciones.all()}
        return columnas

    @cached_property
    def notas(self):
        """{(id de columna, id de inscripción): Evaluacion}"""
        return {(e.instancia_id, e.inscripcion_id): e for e in Evaluacion.objects.filter(instancia__in=self.columnas)}

    @staticmethod
    def aplica(columna, inscripcion):
        return columna.para_todos or inscripcion.id in columna.ids_alumnos

    # --- GET: armar la planilla ---
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(
            docente=self.docente, dictados=self.dictados, dictado=self.dictado, hoy=timezone.localdate(),
            tipos=TipoEvaluacion.objects.all(), condiciones=Condicion.objects.order_by("id"), **kwargs,
        )
        if self.dictado is None:
            return contexto

        filas = []
        for insc in self.inscripciones:
            celdas = []
            for col in self.columnas:
                nota = self.notas.get((col.id, insc.id))
                celdas.append({"columna": col, "aplica": self.aplica(col, insc),
                               "nota": nota_a_texto(nota.valor) if nota else ""})
            valores = [self.notas[(c.id, insc.id)].valor for c in self.columnas if (c.id, insc.id) in self.notas]
            filas.append({
                "inscripcion": insc, "alumno": insc.alumno, "celdas": celdas,
                "promedio": sum(valores) / len(valores) if valores else None,
                "condicion_id": insc.ultimo_cambio.condicion_id if insc.ultimo_cambio else None,
            })
        contexto.update(columnas=self.columnas, filas=filas, inscripciones=self.inscripciones)
        return contexto

    # --- POST: guardar la planilla y, si corresponde, agregar/editar/eliminar una columna ---
    def post(self, request, *args, **kwargs):
        if self.dictado is None:
            return redirect("utn:panel_docente")
        accion = request.POST.get("accion", "guardar")

        with transaction.atomic():
            notas_guardadas, errores = self.guardar_notas()  # siempre: así no se pierde lo que se tipeó
            condiciones_cambiadas = self.guardar_condiciones()
            if accion == "guardar_columna":
                self.guardar_columna()
            elif accion == "eliminar_columna":
                self.eliminar_columna()

        resumen = []
        if notas_guardadas:
            resumen.append(f"{notas_guardadas} nota(s) guardada(s)")
        if condiciones_cambiadas:
            resumen.append(f"{condiciones_cambiadas} condición(es) actualizada(s)")
        if errores:
            messages.warning(request, f"{errores} nota(s) no se guardaron: tienen que ser números entre 1 y 10.")
        if resumen:
            messages.success(request, "Planilla guardada: " + " y ".join(resumen) + ".")
        elif accion == "guardar" and not errores:
            messages.info(request, "No había cambios para guardar.")
        return redirect(f"{reverse('utn:panel_docente')}?dictado={self.dictado.id}")

    def guardar_notas(self):
        """Compara cada celda con lo que hay en la base y solo escribe lo que cambió."""
        guardadas = errores = 0
        for col in self.columnas:
            for insc in self.inscripciones:
                texto = self.request.POST.get(f"nota_{col.id}_{insc.id}")
                if texto is None or not self.aplica(col, insc):
                    continue
                texto = texto.strip()
                actual = self.notas.get((col.id, insc.id))
                if not texto:
                    if actual:
                        actual.delete()
                        guardadas += 1
                    continue
                valor = parsear_nota(texto)
                if valor is None:
                    errores += 1
                elif actual is None:
                    Evaluacion.objects.create(inscripcion=insc, instancia=col, docente=self.docente, valor=valor)
                    guardadas += 1
                elif actual.valor != valor:
                    actual.valor, actual.docente = valor, self.docente
                    actual.save()
                    guardadas += 1
        return guardadas, errores

    def guardar_condiciones(self):
        """Si el docente eligió otra condición, se agrega un cambio al historial (no se pisa el anterior)."""
        validas = {c.id: c for c in Condicion.objects.all()}
        cambiadas = 0
        for insc in self.inscripciones:
            nueva = a_int(self.request.POST.get(f"condicion_{insc.id}"))
            actual = insc.ultimo_cambio.condicion_id if insc.ultimo_cambio else None
            if nueva in validas and nueva != actual:
                CambioCondicion.objects.create(inscripcion=insc, condicion=validas[nueva], docente=self.docente)
                cambiadas += 1
        return cambiadas

    def columna_elegida(self):
        columna_id = a_int(self.request.POST.get("col_id"))
        return next((c for c in self.columnas if c.id == columna_id), None)

    def guardar_columna(self):
        columna = self.columna_elegida()  # None = columna nueva
        if columna is None:
            columna = InstanciaEvaluacion(dictado_materia=self.dictado, creada_por=self.docente)
        form = ColumnaForm(self.request.POST, instance=columna, dictado=self.dictado)
        if not form.is_valid():
            errores = " ".join(e for lista in form.errors.values() for e in lista)
            messages.error(self.request, f"No se pudo guardar la evaluación: {errores}")
            return
        es_nueva = columna.pk is None
        columna = form.save()
        if not columna.para_todos:  # si se sacaron alumnos de la columna, se borran sus notas
            columna.notas.exclude(inscripcion__in=columna.inscripciones.all()).delete()
        messages.success(self.request, f"Columna «{columna.titulo}» " + ("agregada. Ya podés cargar las notas." if es_nueva else "actualizada."))

    def eliminar_columna(self):
        columna = self.columna_elegida()
        if columna:
            columna.delete()  # borra también sus notas (on_delete=CASCADE)
            messages.success(self.request, f"Se eliminó la columna «{columna.titulo}» y sus notas.")
