"""
Regla nueva: un alumno solo puede estar inscripto en materias de su propia carrera.
Esta migración borra las inscripciones viejas que no cumplen la regla
(junto con su historial de condiciones y sus notas, que se borran en cascada).
"""
from django.db import migrations
from django.db.models import F


def borrar_inscripciones_cruzadas(apps, schema_editor):
    Inscripcion = apps.get_model('UTN', 'Inscripcion')
    Inscripcion.objects.exclude(dictado_materia__materia__carrera=F('alumno__carrera')).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('UTN', '0008_pasar_notas_existentes_a_columnas'),
    ]

    operations = [
        # No se puede deshacer: los datos borrados no vuelven.
        migrations.RunPython(borrar_inscripciones_cruzadas, migrations.RunPython.noop),
    ]
