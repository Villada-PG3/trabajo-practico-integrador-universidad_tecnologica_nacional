import datetime

import django.db.models.deletion
from django.db import migrations, models


def asignar_turno(apps, schema_editor):
    """Los módulos que ya existían se asignan al turno que les corresponde según la hora."""
    Modulo = apps.get_model("UTN", "Modulo")
    Turno = apps.get_model("UTN", "Turno")
    for modulo in Modulo.objects.all():
        if modulo.hora_inicio < datetime.time(13, 30):
            nombre = "Mañana"
        elif modulo.hora_inicio < datetime.time(19, 0):
            nombre = "Tarde"
        else:
            nombre = "Noche"
        modulo.turno = Turno.objects.get_or_create(nombre=nombre)[0]
        modulo.save()


class Migration(migrations.Migration):

    dependencies = [
        ("UTN", "0012_cargar_correlativas_sistemas"),
    ]

    operations = [
        migrations.AddField(
            model_name="modulo",
            name="turno",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="modulos", to="UTN.turno"),
        ),
        migrations.RunPython(asignar_turno, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="modulo",
            name="turno",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                    related_name="modulos", to="UTN.turno"),
        ),
    ]
