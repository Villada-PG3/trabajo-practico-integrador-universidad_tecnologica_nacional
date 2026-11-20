from django.db import migrations

# materia -> materias que hay que tener antes (por sigla). Corregir desde el panel de administración si hace falta.
CORRELATIVAS = {
    "ASI": ["AED"],
    "GMP": ["ASI"],
    "DSI": ["ASI"],
    "RDI": ["DSI"],
}


def cargar(apps, schema_editor):
    Materia = apps.get_model("UTN", "Materia")
    for sigla, previas in CORRELATIVAS.items():
        for materia in Materia.objects.filter(sigla=sigla, carrera__sigla="ISI"):
            materia.correlativas.add(*Materia.objects.filter(sigla__in=previas, carrera=materia.carrera))


class Migration(migrations.Migration):

    dependencies = [
        ("UTN", "0011_correlatividades"),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
