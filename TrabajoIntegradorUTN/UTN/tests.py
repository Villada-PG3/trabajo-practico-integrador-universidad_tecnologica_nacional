from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    Administrador, Alumno, Carrera, CicloLectivo, Condicion, Curso, DictadoMateria, Docente,
    Evaluacion, InstanciaEvaluacion, Inscripcion, Materia, TipoEvaluacion, Turno,
)


class BaseTestCase(TestCase):
    """Datos mínimos: dos carreras, un alumno de cada una, un docente y un administrador."""

    @classmethod
    def setUpTestData(cls):
        cls.sistemas = Carrera.objects.create(nombre="Sistemas", sigla="ISI")
        cls.civil = Carrera.objects.create(nombre="Civil", sigla="IC")
        turno = Turno.objects.create(nombre="Mañana")
        ciclo = CicloLectivo.objects.create(anio=2026, descripcion="2026", fecha_inicio=date(2026, 3, 1), fecha_fin=date(2026, 12, 1))
        cls.materia_sis = Materia.objects.create(carrera=cls.sistemas, nombre="Algoritmos", sigla="ALG", nivel=1)
        cls.materia_civ = Materia.objects.create(carrera=cls.civil, nombre="Estática", sigla="EST", nivel=1)
        curso_sis = Curso.objects.create(carrera=cls.sistemas, turno=turno, nombre="1K1", nivel=1)
        curso_civ = Curso.objects.create(carrera=cls.civil, turno=turno, nombre="1C1", nivel=1)
        cls.dictado_sis = DictadoMateria.objects.create(materia=cls.materia_sis, curso=curso_sis, ciclo_lectivo=ciclo)
        cls.dictado_civ = DictadoMateria.objects.create(materia=cls.materia_civ, curso=curso_civ, ciclo_lectivo=ciclo)

        def usuario(nombre):
            return User.objects.create_user(nombre, password="Clave12345")

        cls.alumno = Alumno.objects.create(usuario=usuario("ana"), carrera=cls.sistemas, nombre_completo="Ana Sis", documento=1, email="a@a.com")
        cls.otro_alumno = Alumno.objects.create(usuario=usuario("beto"), carrera=cls.civil, nombre_completo="Beto Civ", documento=2, email="b@a.com")
        cls.docente = Docente.objects.create(usuario=usuario("profe"), legajo="L1", nombre="Pía", apellido="Profe")
        cls.dictado_sis.docentes.add(cls.docente)
        cls.director = Administrador.objects.create(usuario=usuario("dire"), nombre="Di", apellido="Rector", cargo=Administrador.DIRECTOR)
        cls.ejecutivo = Administrador.objects.create(usuario=usuario("ejec"), nombre="Ej", apellido="Ecutivo", cargo=Administrador.EJECUTIVO)
        cls.sin_rol = usuario("fantasma")
        cls.tipo = TipoEvaluacion.objects.create(nombre="Parcial")
        cls.regular = Condicion.objects.create(nombre="Regular")

    def entrar(self, nombre):
        self.client.login(username=nombre, password="Clave12345")


class InscripcionTests(BaseTestCase):
    def test_alumno_se_inscribe_en_su_carrera(self):
        self.entrar("ana")
        self.client.post(reverse("utn:inscribir_materia", args=[self.alumno.pk]), {"dictado_id": self.dictado_sis.pk})
        inscripcion = Inscripcion.objects.get(alumno=self.alumno)
        self.assertEqual(inscripcion.condicion_actual, "Inscripto")

    def test_alumno_no_se_inscribe_en_otra_carrera(self):
        self.entrar("ana")
        respuesta = self.client.post(reverse("utn:inscribir_materia", args=[self.alumno.pk]), {"dictado_id": self.dictado_civ.pk})
        self.assertEqual(respuesta.status_code, 404)  # esa materia ni siquiera está en su lista
        self.assertFalse(Inscripcion.objects.exists())

    def test_la_lista_solo_muestra_materias_de_su_carrera(self):
        self.entrar("ana")
        respuesta = self.client.get(reverse("utn:inscribir_materia", args=[self.alumno.pk]))
        self.assertEqual(list(respuesta.context["dictados"]), [self.dictado_sis])

    def test_no_se_inscribe_dos_veces(self):
        self.entrar("ana")
        url = reverse("utn:inscribir_materia", args=[self.alumno.pk])
        self.client.post(url, {"dictado_id": self.dictado_sis.pk})
        self.client.post(url, {"dictado_id": self.dictado_sis.pk})
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_el_panel_de_administracion_tambien_rechaza_otra_carrera(self):
        self.entrar("dire")
        respuesta = self.client.post(reverse("utn:admin_crear", args=["inscripciones"]),
                                     {"alumno": self.alumno.pk, "dictado_materia": self.dictado_civ.pk})
        self.assertEqual(respuesta.status_code, 200)  # vuelve al formulario con el error
        self.assertFalse(Inscripcion.objects.exists())
        self.assertContains(respuesta, "no pertenece a la carrera del alumno")


class RolesTests(BaseTestCase):
    def test_login_redirige_al_panel_de_cada_rol(self):
        esperado = {
            "ana": reverse("utn:panel_alumno", args=[self.alumno.pk]),
            "profe": reverse("utn:panel_docente"),
            "dire": reverse("utn:admin_dashboard"),
            "ejec": reverse("utn:admin_dashboard"),
        }
        for usuario, destino in esperado.items():
            self.client.logout()
            respuesta = self.client.post(reverse("utn:login"), {"username": usuario, "password": "Clave12345"}, follow=True)
            self.assertEqual(respuesta.redirect_chain[-1][0], destino, usuario)

    def test_usuario_sin_perfil_no_puede_entrar(self):
        respuesta = self.client.post(reverse("utn:login"), {"username": "fantasma", "password": "Clave12345"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_alumno_no_ve_el_panel_de_otro(self):
        self.entrar("ana")
        self.assertEqual(self.client.get(reverse("utn:panel_alumno", args=[self.otro_alumno.pk])).status_code, 403)

    def test_administrador_ve_el_panel_de_cualquier_alumno(self):
        self.entrar("ejec")
        self.assertEqual(self.client.get(reverse("utn:panel_alumno", args=[self.alumno.pk])).status_code, 200)

    def test_alumno_no_entra_al_panel_de_administracion(self):
        self.entrar("ana")
        respuesta = self.client.get(reverse("utn:admin_dashboard"))
        self.assertRedirects(respuesta, reverse("utn:redireccion_panel"), fetch_redirect_response=False)

    def test_sin_login_va_al_login(self):
        respuesta = self.client.get(reverse("utn:panel_docente"))
        self.assertRedirects(respuesta, f"{reverse('utn:login')}?next={reverse('utn:panel_docente')}")

    def test_solo_el_director_gestiona_administradores(self):
        url = reverse("utn:admin_lista", args=["administradores"])
        self.entrar("ejec")
        self.assertRedirects(self.client.get(url), reverse("utn:redireccion_panel"), fetch_redirect_response=False)
        self.client.logout()
        self.entrar("dire")
        self.assertEqual(self.client.get(url).status_code, 200)


class PanelDocenteTests(BaseTestCase):
    def setUp(self):
        self.inscripcion = Inscripcion.objects.create(alumno=self.alumno, dictado_materia=self.dictado_sis)
        self.entrar("profe")
        self.url = reverse("utn:panel_docente")

    def test_crear_columna_cargar_nota_y_cambiar_condicion(self):
        self.client.post(self.url, {"dictado_id": self.dictado_sis.pk, "accion": "guardar_columna",
                                    "tipo_evaluacion": self.tipo.pk, "fecha": "2026-05-10", "alcance": "todos"})
        columna = InstanciaEvaluacion.objects.get()
        self.assertTrue(columna.para_todos)

        self.client.post(self.url, {"dictado_id": self.dictado_sis.pk, "accion": "guardar",
                                    f"nota_{columna.pk}_{self.inscripcion.pk}": "7,5",
                                    f"condicion_{self.inscripcion.pk}": self.regular.pk})
        self.assertEqual(Evaluacion.objects.get().valor, Decimal("7.50"))
        self.assertEqual(Inscripcion.objects.get().condicion_actual, "Regular")

    def test_nota_fuera_de_rango_no_se_guarda(self):
        columna = InstanciaEvaluacion.objects.create(dictado_materia=self.dictado_sis, tipo_evaluacion=self.tipo)
        self.client.post(self.url, {"dictado_id": self.dictado_sis.pk, f"nota_{columna.pk}_{self.inscripcion.pk}": "11"})
        self.assertFalse(Evaluacion.objects.exists())

    def test_columna_para_algunos_exige_elegir_alumnos(self):
        self.client.post(self.url, {"dictado_id": self.dictado_sis.pk, "accion": "guardar_columna",
                                    "tipo_evaluacion": self.tipo.pk, "fecha": "2026-05-10", "alcance": "algunos"})
        self.assertFalse(InstanciaEvaluacion.objects.exists())

    def test_eliminar_columna_borra_sus_notas(self):
        columna = InstanciaEvaluacion.objects.create(dictado_materia=self.dictado_sis, tipo_evaluacion=self.tipo)
        Evaluacion.objects.create(inscripcion=self.inscripcion, instancia=columna, valor=8)
        self.client.post(self.url, {"dictado_id": self.dictado_sis.pk, "accion": "eliminar_columna", "col_id": columna.pk})
        self.assertFalse(InstanciaEvaluacion.objects.exists())
        self.assertFalse(Evaluacion.objects.exists())

    def test_no_puede_abrir_el_curso_de_otro_docente(self):
        respuesta = self.client.get(self.url, {"dictado": self.dictado_civ.pk})
        self.assertEqual(respuesta.status_code, 404)


class PanelAdministracionTests(BaseTestCase):
    def setUp(self):
        self.entrar("dire")

    def test_crear_y_listar_una_carrera(self):
        self.client.post(reverse("utn:admin_crear", args=["carreras"]), {"nombre": "Química", "sigla": "IQ"})
        respuesta = self.client.get(reverse("utn:admin_lista", args=["carreras"]), {"q": "Quím"})
        self.assertContains(respuesta, "Química")

    def test_crear_alumno_crea_tambien_su_usuario(self):
        self.client.post(reverse("utn:admin_crear", args=["alumnos"]), {
            "nombre_completo": "Nuevo Alumno", "documento": 99, "email": "n@a.com", "carrera": self.sistemas.pk,
            "username": "nuevo", "password": "ClaveSegura2026"})
        self.assertTrue(User.objects.get(username="nuevo").check_password("ClaveSegura2026"))
        self.assertEqual(Alumno.objects.get(documento=99).usuario.username, "nuevo")

    def test_eliminar_alumno_elimina_su_usuario(self):
        self.client.post(reverse("utn:admin_eliminar", args=["alumnos", self.otro_alumno.pk]))
        self.assertFalse(User.objects.filter(username="beto").exists())

    def test_no_se_elimina_lo_que_esta_en_uso(self):
        turno = Turno.objects.get()  # lo usan los cursos (on_delete=PROTECT)
        self.client.post(reverse("utn:admin_eliminar", args=["turnos", turno.pk]))
        self.assertTrue(Turno.objects.filter(pk=turno.pk).exists())

    def test_seccion_inexistente_da_404(self):
        self.assertEqual(self.client.get(reverse("utn:admin_lista", args=["nada"])).status_code, 404)


class MiCuentaTests(BaseTestCase):
    def test_cambiar_usuario_y_contrasena(self):
        self.entrar("ana")
        self.client.post(reverse("utn:mi_cuenta"), {"username": "ana2"})
        self.assertTrue(User.objects.filter(username="ana2").exists())
        self.client.post(reverse("utn:mi_cuenta_password"), {
            "old_password": "Clave12345", "new_password1": "OtraClave2026!", "new_password2": "OtraClave2026!"})
        self.assertTrue(User.objects.get(username="ana2").check_password("OtraClave2026!"))
        self.assertEqual(self.client.get(reverse("utn:mi_cuenta")).status_code, 200)  # la sesión sigue abierta
