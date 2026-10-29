"""
Las notas que ya existían no tenían "columna" (InstanciaEvaluacion).
Esta migración las agrupa por curso + tipo de evaluación + fecha y les crea su columna,
así aparecen en la planilla del docente.
"""
from django.db import migrations


def crear_columnas(apps, schema_editor):
    Evaluacion = apps.get_model('UTN', 'Evaluacion')
    InstanciaEvaluacion = apps.get_model('UTN', 'InstanciaEvaluacion')

    columnas = {}
    for ev in Evaluacion.objects.filter(instancia__isnull=True).select_related('inscripcion'):
        clave = (ev.inscripcion.dictado_materia_id, ev.tipo_evaluacion_id, ev.fecha_evaluacion)
        if clave not in columnas:
            columnas[clave] = InstanciaEvaluacion.objects.create(
                dictado_materia_id=clave[0],
                tipo_evaluacion_id=clave[1],
                fecha=clave[2],
                para_todos=True,
            )
        ev.instancia = columnas[clave]
        ev.save(update_fields=['instancia'])


def deshacer(apps, schema_editor):
    Evaluacion = apps.get_model('UTN', 'Evaluacion')
    InstanciaEvaluacion = apps.get_model('UTN', 'InstanciaEvaluacion')
    Evaluacion.objects.update(instancia=None)
    InstanciaEvaluacion.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('UTN', '0007_instancias_evaluacion'),
    ]

    operations = [
        migrations.RunPython(crear_columnas, deshacer),
    ]
