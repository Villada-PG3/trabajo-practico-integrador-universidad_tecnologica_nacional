from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import HorarioForm, MateriaForm
from .models import (
    Administrador, Alumno, CambioCondicion, Carrera, CicloLectivo, Condicion, Curso, DictadoMateria, Docente,
    Evaluacion, Horario, InstanciaEvaluacion, Inscripcion, Materia, Modulo, TipoEvaluacion, Turno,
)


class BaseTestCase(TestCase):
    """Datos mínimos: dos carreras, un alumno de cada una, un docente y un administrador."""

    @classmethod
    def setUpTestData(cls):
        cls.sistemas = Carrera.objects.create(nombre="Sistemas", sigla="ISI")
        cls.civil = Carrera.objects.create(nombre="Civil", sigla="IC")
        turno = Turno.objects.create(nombre="Mañana")
        ciclo = CicloLectivo.objects.create(anio=2026, descripcion="2026", fecha_inicio=date(2026, 3, 1), fecha_fin=date(2099, 12, 1))
        cls.materia_sis = Materia.objects.create(carrera=cls.sistemas, nombre="Algoritmos", sigla="ALG", nivel=1)
        cls.materia_civ = Materia.objects.create(carrera=cls.civil, nombre="Estática", sigla="EST", nivel=1)
        curso_sis = Curso.objects.create(carrera=cls.sistemas, turno=turno, nombre="1K1", nivel=1)
        curso_civ = Curso.objects.create(carrera=cls.civil, turno=turno, nombre="1C1", nivel=1)
        cls.dictado_sis = DictadoMateria.objects.create(materia=cls.materia_sis, curso=curso_sis, ciclo_lectivo=ciclo)
        cls.dictado_civ = DictadoMateria.objects.create(materia=cls.materia_civ, curso=curso_civ, ciclo_lectivo=ciclo)

        def usuario(nombre, staff=False):
            return User.objects.create_user(nombre, password="Clave12345", is_staff=staff)

        cls.alumno = Alumno.objects.create(usuario=usuario("ana"), carrera=cls.sistemas, nombre_completo="Ana Sis", documento=1, email="a@a.com")
        cls.otro_alumno = Alumno.objects.create(usuario=usuario("beto"), carrera=cls.civil, nombre_completo="Beto Civ", documento=2, email="b@a.com")
        cls.docente = Docente.objects.create(usuario=usuario("profe"), legajo="L1", nombre="Pía", apellido="Profe")
        cls.dictado_sis.docentes.add(cls.docente)
        cls.director = Administrador.objects.create(usuario=usuario("dire", staff=True), nombre="Di", apellido="Rector", cargo=Administrador.DIRECTOR)
        cls.ejecutivo = Administrador.objects.create(usuario=usuario("ejec", staff=True), nombre="Ej", apellido="Ecutivo", cargo=Administrador.EJECUTIVO)
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

    def test_la_lista_no_ofrece_ciclos_terminados(self):
        viejo = CicloLectivo.objects.create(anio=2020, descripcion="2020", fecha_inicio=date(2020, 3, 1), fecha_fin=date(2020, 12, 1))
        DictadoMateria.objects.create(materia=self.materia_sis, curso=self.dictado_sis.curso, ciclo_lectivo=viejo)
        self.entrar("ana")
        respuesta = self.client.get(reverse("utn:inscribir_materia", args=[self.alumno.pk]))
        self.assertEqual(list(respuesta.context["dictados"]), [self.dictado_sis])

    def test_la_lista_marca_donde_ya_esta_inscripto(self):
        Inscripcion.objects.create(alumno=self.alumno, dictado_materia=self.dictado_sis)
        self.entrar("ana")
        dictado = self.client.get(reverse("utn:inscribir_materia", args=[self.alumno.pk])).context["dictados"][0]
        self.assertTrue(dictado.ya_inscripto)
        self.assertIsNone(dictado.choque)

    def test_no_se_inscribe_en_una_materia_ya_cumplida(self):
        viejo = CicloLectivo.objects.create(anio=2020, descripcion="2020", fecha_inicio=date(2020, 3, 1), fecha_fin=date(2020, 12, 1))
        anterior = DictadoMateria.objects.create(materia=self.materia_sis, curso=self.dictado_sis.curso, ciclo_lectivo=viejo)
        inscripcion = Inscripcion.objects.create(alumno=self.alumno, dictado_materia=anterior)
        self.regular.habilita_correlativas = True
        self.regular.save()
        CambioCondicion.objects.create(inscripcion=inscripcion, condicion=self.regular)
        self.entrar("ana")
        url = reverse("utn:inscribir_materia", args=[self.alumno.pk])
        self.assertTrue(self.client.get(url).context["dictados"][0].ya_cumplida)
        self.client.post(url, {"dictado_id": self.dictado_sis.pk})
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_no_se_inscribe_dos_veces(self):
        self.entrar("ana")
        url = reverse("utn:inscribir_materia", args=[self.alumno.pk])
        self.client.post(url, {"dictado_id": self.dictado_sis.pk})
        self.client.post(url, {"dictado_id": self.dictado_sis.pk})
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_el_panel_de_administracion_tambien_rechaza_otra_carrera(self):
        self.entrar("dire")
        respuesta = self.client.post(reverse("utn:inscripcion_nuevo"),
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
        url = reverse("utn:administrador_lista")
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
        self.client.post(reverse("utn:carrera_nuevo"), {"nombre": "Química", "sigla": "IQ"})
        respuesta = self.client.get(reverse("utn:carrera_lista"), {"q": "Quím"})
        self.assertContains(respuesta, "Química")

    def test_crear_alumno_crea_tambien_su_usuario(self):
        self.client.post(reverse("utn:alumno_nuevo"), {
            "nombre_completo": "Nuevo Alumno", "documento": 99, "email": "n@a.com", "carrera": self.sistemas.pk,
            "username": "nuevo", "password": "ClaveSegura2026"})
        self.assertTrue(User.objects.get(username="nuevo").check_password("ClaveSegura2026"))
        self.assertEqual(Alumno.objects.get(documento=99).usuario.username, "nuevo")

    def test_eliminar_alumno_elimina_su_usuario(self):
        self.client.post(reverse("utn:alumno_eliminar", args=[self.otro_alumno.pk]))
        self.assertFalse(User.objects.filter(username="beto").exists())

    def test_no_puede_eliminar_su_propio_usuario(self):
        propio = Administrador.objects.get(usuario__username="dire")
        self.client.post(reverse("utn:administrador_eliminar", args=[propio.pk]))
        self.assertTrue(Administrador.objects.filter(pk=propio.pk).exists())

    def test_el_menu_del_ejecutivo_no_muestra_administradores(self):
        self.assertContains(self.client.get(reverse("utn:admin_dashboard")), "Administradores")
        self.client.logout()
        self.entrar("ejec")
        self.assertNotContains(self.client.get(reverse("utn:admin_dashboard")), "Administradores")

    def test_las_otras_tablas_se_gestionan_desde_el_admin_de_django(self):
        self.assertEqual(self.client.get(reverse("admin:UTN_turno_changelist")).status_code, 200)
        self.client.logout()
        self.entrar("ana")
        self.assertNotEqual(self.client.get(reverse("admin:UTN_turno_changelist")).status_code, 200)


class MiCuentaTests(BaseTestCase):
    def test_cambiar_usuario_y_contrasena(self):
        self.entrar("ana")
        self.client.post(reverse("utn:mi_cuenta"), {"username": "ana2"})
        self.assertTrue(User.objects.filter(username="ana2").exists())
        self.client.post(reverse("utn:mi_cuenta_password"), {
            "old_password": "Clave12345", "new_password1": "OtraClave2026!", "new_password2": "OtraClave2026!"})
        self.assertTrue(User.objects.get(username="ana2").check_password("OtraClave2026!"))
        self.assertEqual(self.client.get(reverse("utn:mi_cuenta")).status_code, 200)  # la sesión sigue abierta


class CorrelativasTests(BaseTestCase):
    """Materia 2 de Sistemas exige tener Algoritmos (1) con una condición que habilite."""

    def setUp(self):
        self.regular.habilita_correlativas = True
        self.regular.save()
        self.materia2 = Materia.objects.create(carrera=self.sistemas, nombre="Programación II", sigla="PR2", nivel=2)
        self.materia2.correlativas.add(self.materia_sis)
        self.dictado2 = DictadoMateria.objects.create(
            materia=self.materia2, curso=self.dictado_sis.curso, ciclo_lectivo=self.dictado_sis.ciclo_lectivo)
        self.url = reverse("utn:inscribir_materia", args=[self.alumno.pk])

    def cursar_algoritmos(self, condicion):
        inscripcion = Inscripcion.objects.create(alumno=self.alumno, dictado_materia=self.dictado_sis)
        CambioCondicion.objects.create(inscripcion=inscripcion, condicion=condicion)

    def test_sin_la_correlativa_no_se_puede_inscribir(self):
        self.entrar("ana")
        self.client.post(self.url, {"dictado_id": self.dictado2.pk})
        self.assertFalse(Inscripcion.objects.filter(dictado_materia=self.dictado2).exists())

    def test_la_lista_muestra_lo_que_falta(self):
        self.entrar("ana")
        dictados = self.client.get(self.url).context["dictados"]
        faltantes = {d.materia.sigla: d.faltantes for d in dictados}
        self.assertEqual(faltantes["PR2"], [self.materia_sis])
        self.assertEqual(faltantes["ALG"], [])

    def test_con_la_correlativa_regular_se_inscribe(self):
        self.cursar_algoritmos(self.regular)
        self.entrar("ana")
        self.client.post(self.url, {"dictado_id": self.dictado2.pk})
        self.assertTrue(Inscripcion.objects.filter(dictado_materia=self.dictado2).exists())

    def test_una_condicion_que_no_habilita_no_alcanza(self):
        self.cursar_algoritmos(Condicion.objects.create(nombre="Libre"))
        self.entrar("ana")
        self.client.post(self.url, {"dictado_id": self.dictado2.pk})
        self.assertFalse(Inscripcion.objects.filter(dictado_materia=self.dictado2).exists())

    def test_el_panel_de_administracion_tambien_lo_valida(self):
        self.entrar("dire")
        self.client.post(reverse("utn:inscripcion_nuevo"),
                         {"alumno": self.alumno.pk, "dictado_materia": self.dictado2.pk})
        self.assertFalse(Inscripcion.objects.exists())

    def test_correlativa_de_otra_carrera_o_ciclo_se_rechaza(self):
        def formulario(correlativas, materia=None):
            datos = {"carrera": self.sistemas.pk, "nombre": "X", "sigla": "X", "nivel": 3, "correlativas": correlativas}
            return MateriaForm(datos, instance=materia)
        self.assertFalse(formulario([self.materia_civ.pk]).is_valid())            # otra carrera
        self.assertFalse(formulario([self.materia2.pk], self.materia_sis).is_valid())  # ciclo: ALG -> PR2 -> ALG
        self.assertFalse(formulario([self.materia_sis.pk], self.materia_sis).is_valid())  # ella misma
        self.assertTrue(formulario([self.materia_sis.pk]).is_valid())

    def test_el_mapa_marca_los_estados(self):
        self.entrar("ana")
        arbol = self.client.get(reverse("utn:correlativas", args=[self.alumno.pk])).context["arbol"]
        raiz = arbol[0]
        self.assertEqual((raiz["materia"], raiz["texto"]), (self.materia_sis, "Podés inscribirte"))
        self.assertEqual(raiz["hijos"][0]["texto"], "Bloqueada")
        self.assertEqual(raiz["hijos"][0]["faltantes"], [self.materia_sis])

    def test_el_mapa_con_la_correlativa_cumplida(self):
        self.cursar_algoritmos(self.regular)
        self.entrar("ana")
        raiz = self.client.get(reverse("utn:correlativas", args=[self.alumno.pk])).context["arbol"][0]
        self.assertEqual(raiz["texto"], "Cumplida")
        self.assertEqual(raiz["hijos"][0]["texto"], "Podés inscribirte")

    def test_el_panel_lateral_lista_lo_que_falta_en_orden(self):
        materia3 = Materia.objects.create(carrera=self.sistemas, nombre="Diseño", sigla="DIS", nivel=3)
        materia3.correlativas.add(self.materia2)
        self.entrar("ana")
        raiz = self.client.get(reverse("utn:correlativas", args=[self.alumno.pk])).context["arbol"][0]
        nodo = raiz["hijos"][0]["hijos"][0]  # Algoritmos -> Programación II -> Diseño
        self.assertEqual(nodo["pendientes"], "Algoritmos — Podés inscribirte ahora|Programación II — Primero necesitás sus correlativas")
        self.assertFalse(nodo["puede_inscribirse"])
        self.assertTrue(raiz["puede_inscribirse"])

    def test_el_boton_de_inscribirse_solo_esta_si_esta_habilitada(self):
        self.entrar("ana")
        pagina = self.client.get(reverse("utn:correlativas", args=[self.alumno.pk])).content.decode()
        inscribir = reverse("utn:inscribir_materia", args=[self.alumno.pk])
        self.assertEqual(pagina.count(f'data-inscribir="{inscribir}"'), 1)  # solo Algoritmos: Programación II está bloqueada

    def test_la_flecha_solo_aparece_si_se_puede_desplegar(self):
        self.entrar("ana")
        pagina = self.client.get(reverse("utn:correlativas", args=[self.alumno.pk])).content.decode()
        self.assertEqual(pagina.count('class="bi bi-chevron-right flecha"'), 1)  # Algoritmos tiene a Programación II debajo
        self.assertEqual(pagina.count('class="flecha-vacia"'), 1)                # Programación II no tiene nada debajo

    def test_no_se_ve_el_mapa_de_otro_alumno(self):
        self.entrar("beto")
        self.assertEqual(self.client.get(reverse("utn:correlativas", args=[self.alumno.pk])).status_code, 403)


class HorariosTests(BaseTestCase):
    """Dos materias en el mismo día y a la misma hora no se pueden cursar a la vez."""

    def setUp(self):
        turno = self.dictado_sis.curso.turno
        self.m1 = Modulo.objects.create(turno=turno, numero=1, hora_inicio=time(8, 0), hora_fin=time(8, 45))
        self.m2 = Modulo.objects.create(turno=turno, numero=2, hora_inicio=time(8, 45), hora_fin=time(9, 30))
        self.m3 = Modulo.objects.create(turno=turno, numero=3, hora_inicio=time(9, 40), hora_fin=time(10, 25))
        materia3 = Materia.objects.create(carrera=self.sistemas, nombre="Sistemas Operativos", sigla="SOP", nivel=1)
        self.dictado3 = DictadoMateria.objects.create(
            materia=materia3, curso=self.dictado_sis.curso, ciclo_lectivo=self.dictado_sis.ciclo_lectivo)
        self.url = reverse("utn:inscribir_materia", args=[self.alumno.pk])

    def horario(self, dictado, dia, *modulos):
        horario = Horario.objects.create(dictado_materia=dictado, dia=dia)
        horario.modulos.set(modulos)
        return horario

    def test_el_horario_muestra_dia_y_horas(self):
        self.assertEqual(self.horario(self.dictado_sis, "Lunes", self.m1, self.m2).texto, "Lunes 08:00 a 09:30")

    def test_horas_que_se_pisan_chocan_y_las_que_se_tocan_no(self):
        self.horario(self.dictado_sis, "Lunes", self.m1, self.m2)
        self.horario(self.dictado3, "Lunes", self.m2, self.m3)  # 08:45 a 10:25: se pisa
        self.assertIsNotNone(self.dictado_sis.choque_con(self.dictado3))
        Horario.objects.filter(dictado_materia=self.dictado3).delete()
        self.horario(self.dictado3, "Lunes", self.m3)  # 09:40 a 10:25: empieza después
        self.assertIsNone(self.dictado_sis.choque_con(self.dictado3))

    def test_no_se_inscribe_en_una_materia_a_la_misma_hora(self):
        self.horario(self.dictado_sis, "Lunes", self.m1, self.m2)
        self.horario(self.dictado3, "Lunes", self.m2, self.m3)
        self.entrar("ana")
        self.client.post(self.url, {"dictado_id": self.dictado_sis.pk})
        self.client.post(self.url, {"dictado_id": self.dictado3.pk})
        self.assertEqual(list(Inscripcion.objects.values_list("dictado_materia", flat=True)), [self.dictado_sis.pk])

    def test_la_lista_avisa_con_que_se_superpone(self):
        self.horario(self.dictado_sis, "Lunes", self.m1, self.m2)
        self.horario(self.dictado3, "Lunes", self.m2, self.m3)
        self.entrar("ana")
        self.client.post(self.url, {"dictado_id": self.dictado_sis.pk})
        dictados = {d.materia.sigla: d for d in self.client.get(self.url).context["dictados"]}
        self.assertIn("Algoritmos", dictados["SOP"].choque)

    def test_otro_dia_no_choca(self):
        self.horario(self.dictado_sis, "Lunes", self.m1, self.m2)
        self.horario(self.dictado3, "Martes", self.m1, self.m2)
        self.entrar("ana")
        self.client.post(self.url, {"dictado_id": self.dictado_sis.pk})
        self.client.post(self.url, {"dictado_id": self.dictado3.pk})
        self.assertEqual(Inscripcion.objects.count(), 2)

    def test_el_panel_de_administracion_tambien_lo_valida(self):
        self.horario(self.dictado_sis, "Lunes", self.m1)
        self.horario(self.dictado3, "Lunes", self.m1)
        Inscripcion.objects.create(alumno=self.alumno, dictado_materia=self.dictado_sis)
        self.entrar("dire")
        self.client.post(reverse("utn:inscripcion_nuevo"),
                         {"alumno": self.alumno.pk, "dictado_materia": self.dictado3.pk})
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_el_cronograma_del_panel_muestra_las_materias(self):
        self.horario(self.dictado_sis, "Lunes", self.m1, self.m2)
        Inscripcion.objects.create(alumno=self.alumno, dictado_materia=self.dictado_sis)
        self.entrar("ana")
        cronograma = self.client.get(reverse("utn:panel_alumno", args=[self.alumno.pk])).context["cronograma"]
        self.assertEqual(len(cronograma["filas"]), 2)  # una fila por módulo
        self.assertEqual(cronograma["dias"].index("Lunes"), 0)
        self.assertEqual(cronograma["filas"][0]["celdas"][0]["sigla"], "ALG")

    def test_el_formulario_de_horarios_valida_turno_y_superposicion(self):
        otro_turno = Turno.objects.create(nombre="Noche")
        modulo_noche = Modulo.objects.create(turno=otro_turno, numero=1, hora_inicio=time(18, 30), hora_fin=time(19, 15))
        self.horario(self.dictado_sis, "Lunes", self.m1, self.m2)

        def formulario(dictado, *modulos):
            return HorarioForm({"dictado_materia": dictado.pk, "dia": "Lunes", "modulos": [m.pk for m in modulos]})
        self.assertFalse(formulario(self.dictado3, modulo_noche).is_valid())   # módulo de otro turno
        self.assertFalse(formulario(self.dictado3, self.m2, self.m3).is_valid())  # se pisa con ALG en el mismo curso
        self.assertTrue(formulario(self.dictado3, self.m3).is_valid())
