"""
La nota (Evaluacion) guardaba el tipo y la fecha, datos que ya tiene su columna (InstanciaEvaluacion).
Se eliminan esos dos campos repetidos y toda nota pasa a pertenecer obligatoriamente a una columna.
Además se agrega el mensaje de error propio de la restricción "una inscripción por alumno y dictado".
"""
import django.db.models.deletion
from django.db import migrations, models


def columnas_para_notas_sueltas(apps, schema_editor):
    """Si quedó alguna nota sin columna, se le crea una (agrupando por curso + tipo + fecha)."""
    Evaluacion = apps.get_model('UTN', 'Evaluacion')
    InstanciaEvaluacion = apps.get_model('UTN', 'InstanciaEvaluacion')

    columnas = {}
    for ev in Evaluacion.objects.filter(instancia__isnull=True).select_related('inscripcion'):
        clave = (ev.inscripcion.dictado_materia_id, ev.tipo_evaluacion_id, ev.fecha_evaluacion)
        if clave not in columnas:
            columnas[clave] = InstanciaEvaluacion.objects.create(
                dictado_materia_id=clave[0], tipo_evaluacion_id=clave[1],
                fecha=clave[2], para_todos=True,
            )
        ev.instancia = columnas[clave]
        ev.save(update_fields=['instancia'])


class Migration(migrations.Migration):

    dependencies = [
        ('UTN', '0009_borrar_inscripciones_otras_carreras'),
    ]

    operations = [
        migrations.RunPython(columnas_para_notas_sueltas, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='evaluacion',
            name='instancia',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notas', to='UTN.instanciaevaluacion'),
        ),
        migrations.AlterField(
            model_name='evaluacion',
            name='docente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='UTN.docente'),
        ),
        migrations.RemoveField(model_name='evaluacion', name='tipo_evaluacion'),
        migrations.RemoveField(model_name='evaluacion', name='fecha_evaluacion'),
        migrations.AlterConstraint(
            model_name='inscripcion',
            name='inscripcion_unica_alumno_dictado',
            constraint=models.UniqueConstraint(
                fields=('alumno', 'dictado_materia'), name='inscripcion_unica_alumno_dictado',
                violation_error_message='Ya estás inscripto en esta materia.',
            ),
        ),
    ]
