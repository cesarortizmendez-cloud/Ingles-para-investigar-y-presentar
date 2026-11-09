"""Pruebas de integración Django. Ejecutar con: python manage.py test

Recorren el corte vertical completo: importar contenido, perfil, diagnóstico,
catálogo, todas las lecciones de C01 y C11, actividades cerradas y abiertas,
grabación, rúbrica, repaso, confirmación diferida, portafolio, exportación y
eliminación de datos.
"""
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from activities.models import Attempt
from assessment.models import RubricScore
from curriculum.models import ChapterProgress, ContentPackage
from curriculum.services import ContentError, import_directory, publish_version
from review.models import ReviewItem
from voice.models import Recording

STATIC = {"STORAGES": {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                       "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}}


@override_settings(**STATIC)
class VerticalSliceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        import_directory()
        cls.user = get_user_model().objects.create_user("ana", password="clave-segura-123")

    def setUp(self):
        self.client.login(username="ana", password="clave-segura-123")
        self.c11 = ContentPackage.objects.get(code="C11", is_current=True)
        self.c01 = ContentPackage.objects.get(code="C01", is_current=True)

    def post_activity(self, pkg, activity_id, data, next_url="/"):
        url = reverse("activity_submit", args=[pkg.pk, activity_id])
        return self.client.post(url, {"next": next_url, **data})

    # ---------------------------------------------------------------- páginas
    def test_pages_render(self):
        for name in ("home", "catalog", "review", "portfolio", "privacy", "profile", "diagnostic", "diagnostic_result"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        for pkg in (self.c01, self.c11):
            self.assertEqual(self.client.get(reverse("chapter", args=[pkg.code])).status_code, 200)
            for lsn in pkg.data["lessons"]:
                r = self.client.get(reverse("lesson", args=[pkg.code, lsn["id"]]))
                self.assertEqual(r.status_code, 200, lsn["id"])
            r = self.client.get(reverse("lesson", args=["C11", "C11.6"]) + "?variantes=todas")
            self.assertContains(r, "C11.6.a1t")
        dx = ContentPackage.objects.get(code="DX01")
        for lsn in dx.data["lessons"]:
            self.assertEqual(self.client.get(reverse("lesson", args=["DX01", lsn["id"]])).status_code, 200)

    def test_unavailable_chapter_is_404_not_filler(self):
        self.assertEqual(self.client.get(reverse("chapter", args=["C02"])).status_code, 404)
        self.assertContains(self.client.get(reverse("catalog")), "En preparación")

    def test_specialty_variant(self):
        p = self.user.profile
        p.specialty = "comercial"
        p.save()
        r = self.client.get(reverse("lesson", args=["C11", "C11.6"]))
        self.assertContains(r, "C11.6.a1c")
        self.assertNotContains(r, "C11.6.a1t")

    # ---------------------------------------------------------------- actividades
    def test_closed_activity_graded_and_scheduled(self):
        r = self.post_activity(self.c11, "C11.2.a1", {"num_rel": "15", "num_pp": "0,5"})
        self.assertEqual(r.status_code, 302)
        att = Attempt.objects.get(activity_id="C11.2.a1")
        self.assertTrue(att.correct)
        self.assertEqual(att.package_id, self.c11.pk)
        item = ReviewItem.objects.get(user=self.user, key="C11.2.a1")
        self.assertEqual(item.due, timezone.localdate() + timedelta(days=1))
        # abrir el capítulo agenda el léxico prioritario
        self.assertEqual(ReviewItem.objects.filter(user=self.user, kind="lexis", chapter_code="C11").count(), 12)

    def test_incomplete_submission_is_not_saved(self):
        self.post_activity(self.c11, "C11.1.a3", {"option": "b"})  # falta justificación
        self.assertFalse(Attempt.objects.filter(activity_id="C11.1.a3").exists())

    def test_helps_are_recorded(self):
        self.post_activity(self.c11, "C11.4.a1", {"text": "was associated with", "helps_csv": "hint,glossary,bogus"})
        att = Attempt.objects.get(activity_id="C11.4.a1")
        self.assertEqual(att.helps, ["glossary", "hint"])
        item = ReviewItem.objects.get(user=self.user, key="C11.4.a1")
        self.assertEqual(item.stage, 0)

    def test_ordering_requires_permutation(self):
        self.post_activity(self.c01, "C01.2.a3", {"pos_w1": "1", "pos_w2": "1", "pos_w3": "3", "pos_w4": "4", "pos_w5": "5"})
        self.assertFalse(Attempt.objects.filter(activity_id="C01.2.a3").exists())
        self.post_activity(self.c01, "C01.2.a3", {"pos_w1": "1", "pos_w2": "2", "pos_w3": "3", "pos_w4": "4", "pos_w5": "5"})
        self.assertTrue(Attempt.objects.get(activity_id="C01.2.a3").correct)

    def test_open_redirect_blocked(self):
        r = self.post_activity(self.c11, "C11.2.a1", {"num_rel": "15", "num_pp": "0.5"}, next_url="https://evil.example/")
        self.assertTrue(r["Location"].startswith("/capitulo/C11/leccion/C11.2/"))

    # ---------------------------------------------------------------- voz, rúbrica y cierre
    def _record(self, activity_id, transcript=""):
        audio = SimpleUploadedFile("g.webm", b"\x1aE\xdf\xa3fakeaudio", content_type="audio/webm")
        r = self.client.post(reverse("recording_upload"), {
            "audio": audio, "activity_id": activity_id, "package_id": self.c11.pk,
            "duration_s": "75", "transcript": transcript})
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["id"]

    def test_full_chapter_cycle_to_consolidated(self):
        # comprobación: 5 ítems no vistos, todos correctos
        self.post_activity(self.c11, "C11.4.a3", {"option": "b"})
        self.post_activity(self.c11, "C11.4.a4", {"option": "b"})
        self.post_activity(self.c11, "C11.4.a5", {"gap_1": "while", "gap_2": "respectively", "gap_3": "suggest"})
        self.post_activity(self.c11, "C11.4.a6", {"num_rel": "25"})
        self.post_activity(self.c11, "C11.4.a7", {"text": "One limitation is"})
        # tarea integradora oral con grabación
        rec_id = self._record("C11.6.a1i", "Picking accuracy was 96.0% and 98.5%, a difference of 2.5 percentage points. "
                                           "This may suggest an association, but zones were not randomly assigned.")
        self.post_activity(self.c11, "C11.6.a1i", {"recording_id": str(rec_id), "transcript": "accuracy 96 and 98.5 percentage points may random"})
        final = Attempt.objects.get(activity_id="C11.6.a1i")
        self.assertEqual(final.status, "pendiente_rubrica")
        self.assertIsNone(final.score)
        self.assertEqual(Recording.objects.get(pk=rec_id).attempt_id, final.pk)
        self.assertEqual(self.client.get(reverse("recording_stream", args=[rec_id])).status_code, 200)

        url = reverse("rubric_form", args=[final.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url, {"c_task": 3, "c_organization": 3, "c_intelligibility": 3, "c_resources": 3, "c_fluency": 3})
        rs = RubricScore.objects.get(attempt=final)
        self.assertEqual(rs.total, 75)
        self.assertEqual(rs.rater_kind, "autoevaluacion")

        self.client.get(reverse("chapter", args=["C11"]))
        prog = ChapterProgress.objects.get(user=self.user, chapter_code="C11")
        self.assertEqual(prog.last_state, "aprobado_provisional")
        # aún no se abre la confirmación diferida
        self.assertEqual(self.client.get(reverse("deferred", args=["C11"])).status_code, 302)

        # simular el paso de 8 días
        prog.provisional_on = timezone.localdate() - timedelta(days=8)
        prog.save()
        self.assertEqual(self.client.get(reverse("deferred", args=["C11"])).status_code, 200)
        self.post_activity(self.c11, "C11.D.a1", {"num_rel": "25", "num_hours": "0.2"})
        self.post_activity(self.c11, "C11.D.a2", {"option": "b"})
        self.post_activity(self.c11, "C11.D.a3", {"text": "was associated with"})
        self.post_activity(self.c11, "C11.D.a4", {"gap_1": "respectively", "gap_2": "however", "gap_3": "random"})
        self.client.get(reverse("chapter", args=["C11"]))
        prog.refresh_from_db()
        # 3 + 2/3 de 4 ítems = 0,917 ≥ 0,75
        self.assertEqual(prog.last_state, "consolidado")

    def test_no_mic_is_pending_evidence(self):
        self.post_activity(self.c11, "C11.5.a1", {"no_mic": "1"})
        att = Attempt.objects.get(activity_id="C11.5.a1")
        self.assertEqual(att.status, "pendiente_evidencia")

    def test_upload_rejects_non_audio(self):
        bad = SimpleUploadedFile("x.txt", b"hola", content_type="text/plain")
        r = self.client.post(reverse("recording_upload"), {"audio": bad, "activity_id": "C11.5.a1"})
        self.assertEqual(r.status_code, 400)

    def test_other_user_cannot_listen(self):
        rec_id = self._record("C11.5.a1")
        get_user_model().objects.create_user("otro", password="clave-segura-456")
        self.client.logout()
        self.client.login(username="otro", password="clave-segura-456")
        self.assertEqual(self.client.get(reverse("recording_stream", args=[rec_id])).status_code, 403)

    # ---------------------------------------------------------------- repaso
    def test_review_session_and_lexis(self):
        self.post_activity(self.c11, "C11.2.a1", {"num_rel": "15", "num_pp": "0.5"})
        ReviewItem.objects.filter(user=self.user).update(due=timezone.localdate())
        r = self.client.get(reverse("review"))
        self.assertEqual(r.status_code, 200)
        lx = ReviewItem.objects.get(user=self.user, key="lexis:C11-LX01")
        self.client.post(reverse("review_lexis", args=[lx.pk]), {"text": "was associated with"})
        lx.refresh_from_db()
        self.assertEqual(lx.stage, 1)
        self.assertEqual(lx.due, timezone.localdate() + timedelta(days=3))

    # ---------------------------------------------------------------- diagnóstico
    def test_diagnostic_result(self):
        dx = ContentPackage.objects.get(code="DX01")
        for aid, data in [("DX01.1.a1", {"option": "b"}), ("DX01.1.a3", {"option": "b"}),
                          ("DX01.1.a4", {"option": "b"}), ("DX01.1.a5", {"option": "b"})]:
            self.client.post(reverse("activity_submit", args=[dx.pk, aid]), data)
        self.client.post(reverse("diagnostic_compute"))
        r = self.client.get(reverse("diagnostic_result"))
        self.assertContains(r, "B1+ o superior")
        self.assertContains(r, "insuficiente")
        self.assertTrue(Attempt.objects.filter(source="diagnostico").exists())

    # ---------------------------------------------------------------- control del usuario
    def test_export_and_delete(self):
        self._record("C11.5.a1")
        r = self.client.get(reverse("portfolio_export"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("recordings", r.json())
        self.client.post(reverse("delete_recordings"), {"confirm": "ELIMINAR"})
        self.assertFalse(Recording.objects.filter(user=self.user).exists())
        self.client.post(reverse("delete_account"), {"confirm": "ELIMINAR MI CUENTA"})
        self.assertFalse(get_user_model().objects.filter(username="ana").exists())


class ContentVersioningTests(TestCase):
    def test_editing_requires_new_version_and_keeps_old(self):
        import_directory()
        pkg = ContentPackage.objects.get(code="C11", is_current=True)
        user = get_user_model().objects.create_user("u", password="x-clave-123456")
        Attempt.objects.create(user=user, package=pkg, chapter_code="C11", activity_id="C11.2.a1",
                               activity_type="numeric", status="corregido", score=1.0)
        data = dict(pkg.data)
        data["title"] = "Título cambiado"
        with self.assertRaises(ContentError):
            publish_version(data)  # misma versión, otro contenido
        data["version"] = "1.0.1"
        new, created = publish_version(data)
        self.assertTrue(created)
        self.assertTrue(new.is_current)
        pkg.refresh_from_db()
        self.assertFalse(pkg.is_current)
        self.assertEqual(Attempt.objects.get(activity_id="C11.2.a1").package_id, pkg.pk)

    def test_invalid_content_is_rejected(self):
        import_directory()
        data = dict(ContentPackage.objects.get(code="C11", is_current=True).data)
        data["objectives"] = []
        data["version"] = "9.9.9"
        with self.assertRaises(ContentError):
            publish_version(data)


@override_settings(**STATIC)
class Plan40Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        import_directory()
        cls.user = get_user_model().objects.create_user("eva", password="clave-segura-789")

    def setUp(self):
        self.client.login(username="eva", password="clave-segura-789")

    def test_calendar_start_and_day_pages(self):
        self.assertEqual(ContentPackage.objects.filter(kind="day", is_current=True, code__startswith="D").count(), 40)
        self.assertEqual(ContentPackage.objects.filter(kind="day", is_current=True, code__startswith="B").count(), 20)
        r = self.client.get(reverse("plan_calendar"))
        self.assertContains(r, "Comenzar el plan")
        r = self.client.post(reverse("plan_start"), {"start": timezone.localdate().isoformat()})
        self.assertRedirects(r, reverse("plan_day", args=[1]))
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.plan_start, timezone.localdate())
        for n in (1, 7, 15, 40):
            self.assertEqual(self.client.get(reverse("plan_day", args=[n])).status_code, 200, n)
        self.assertEqual(self.client.get(reverse("plan_day", args=[41])).status_code, 404)

    def test_all_day_lessons_render(self):
        for n in (1, 15, 21, 40):
            pkg = ContentPackage.objects.get(code=f"D{n:02d}", is_current=True)
            for lsn in pkg.data["lessons"]:
                r = self.client.get(reverse("lesson", args=[pkg.code, lsn["id"]]))
                self.assertEqual(r.status_code, 200, lsn["id"])
        r = self.client.get(reverse("lesson", args=["D15", "D15.2"]))
        self.assertContains(r, "is measured")

    def test_answer_vocab_and_progress(self):
        pkg = ContentPackage.objects.get(code="D01", is_current=True)
        act = next(a for a in pkg.data["lessons"][0]["activities"] if a["type"] == "short_text")
        self.client.get(reverse("lesson", args=["D01", "D01.1"]))
        self.assertEqual(ReviewItem.objects.filter(user=self.user, kind="lexis", chapter_code="D01").count(), 12)
        self.client.post(reverse("activity_submit", args=[pkg.pk, act["id"]]), {"text": act["accept"][0]})
        att = Attempt.objects.get(activity_id=act["id"])
        self.assertTrue(att.correct)
        r = self.client.get(reverse("plan_day", args=[1]))
        self.assertContains(r, "1 de ")
        self.assertEqual(self.client.get(reverse("review")).status_code, 200)
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)


@override_settings(**STATIC)
class PlanPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        import_directory()
        cls.user = get_user_model().objects.create_user("leo", password="clave-segura-321")

    def test_plan_pages_without_avatar(self):
        self.client.login(username="leo", password="clave-segura-321")
        for url in (reverse("home"), reverse("plan_calendar"), reverse("plan_day", args=[3])):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            self.assertNotContains(r, "data-avatar")
            self.assertNotContains(r, "avatar.js")
        r = self.client.get(reverse("plan_calendar"))
        self.assertContains(r, 'class="ring"')
        self.assertEqual(r.content.decode().count("<path "), 40)
        r = self.client.get(reverse("plan_day", args=[3]))
        self.assertContains(r, 'class="day-strip"')
        self.assertContains(r, "Metas de hoy")
        self.assertContains(r, "Tu día, paso a paso")

    def test_sections_are_coordinated_with_plan(self):
        """Inicio, ruta, repaso, diagnóstico, portafolio y perfil apuntan al plan y no tienen enlaces rotos."""
        from accounts.models import get_profile
        profile = get_profile(self.user)
        profile.plan_start = timezone.localdate() - timedelta(days=4)
        profile.save()
        self.client.login(username="leo", password="clave-segura-321")
        d1 = ContentPackage.objects.get(code="D01", is_current=True)
        lsn = d1.data["lessons"][4]  # bloque de habla
        self.client.get(reverse("lesson", args=["D01", lsn["id"]]))  # registra el día como abierto
        act = next(a for a in lsn["activities"] if a["type"] in ("oral", "open_text"))
        Attempt.objects.create(user=self.user, package=d1, chapter_code="D01", lesson_id=lsn["id"],
                               activity_id=act["id"], activity_type=act["type"], status="pendiente_rubrica",
                               response={"text": "I am a researcher."})
        pages = {"home": reverse("home"), "plan": reverse("plan_calendar"), "ruta": reverse("catalog"),
                 "repaso": reverse("review"), "diag": reverse("diagnostic"), "diag_res": reverse("diagnostic_result"),
                 "portafolio": reverse("portfolio"), "perfil": reverse("profile")}
        bodies = {}
        for name, url in pages.items():
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, name)
            bodies[name] = r.content.decode()
            for link in set(re.findall(r'href="(/(?:capitulo|plan|repaso|evaluacion|portafolio|ruta|diagnostico)[^"#]*)', bodies[name])):
                self.assertLess(self.client.get(link).status_code, 400, f"{name} → {link}")
        day5 = reverse("plan_day", args=[5])
        self.assertNotIn("/capitulo/D01/\"", bodies["home"])
        self.assertIn(day5, bodies["home"])
        self.assertIn("Plan intensivo de 40 días", bodies["ruta"])
        self.assertIn("Plan base de 20 días", bodies["ruta"])
        self.assertIn("estás aquí", bodies["ruta"])
        self.assertIn(day5, bodies["repaso"])
        self.assertIn("plan de 40 días", bodies["diag"])
        self.assertIn("Día 1 · ", bodies["portafolio"])
        self.assertIn("Inicio del plan intensivo de 40 días", bodies["perfil"])
        self.assertNotIn("360 minutos semanales", bodies["perfil"])


@override_settings(**STATIC)
class Base20Tests(TestCase):
    """Plan base de 20 días: calendario propio, días B01…B20 y avance separado del plan de 40."""

    @classmethod
    def setUpTestData(cls):
        import_directory()
        cls.user = get_user_model().objects.create_user("bea", password="clave-segura-321")

    def setUp(self):
        self.client.login(username="bea", password="clave-segura-321")

    def test_start_calendar_and_day(self):
        r = self.client.get(reverse("program_calendar", args=["base20"]))
        self.assertContains(r, "Plan base de 20 días")
        self.assertContains(r, "Elige tu día 1")
        r = self.client.post(reverse("program_start", args=["base20"]), {"start": timezone.localdate().isoformat()})
        self.assertRedirects(r, reverse("program_day", args=["base20", 1]))
        from accounts.models import get_profile
        profile = get_profile(self.user)
        self.assertEqual(profile.base_start, timezone.localdate())
        self.assertIsNone(profile.plan_start)  # el plan de 40 no se inicia solo
        r = self.client.get(reverse("program_calendar", args=["base20"]))
        self.assertEqual(r.content.decode().count("<path "), 20)
        self.assertContains(r, "Unidad 4")
        r = self.client.get(reverse("program_day", args=["base20", 3]))
        self.assertContains(r, "Países, nacionalidades e idiomas")
        self.assertContains(r, "/20")
        self.assertContains(r, reverse("program_day", args=["base20", 4]))
        lsn = ContentPackage.objects.get(code="B03", is_current=True).data["lessons"][0]["id"]
        r = self.client.get(reverse("lesson", args=["B03", lsn]))
        self.assertContains(r, "Plan base de 20 días")
        self.assertContains(r, reverse("program_day", args=["base20", 3]))
        self.assertEqual(self.client.get(reverse("program_day", args=["base20", 21])).status_code, 404)
        self.assertEqual(self.client.get(reverse("program_calendar", args=["nada"])).status_code, 404)

    def test_progress_is_separate_per_program(self):
        from plan.services import progress_for
        from curriculum.services import current_packages
        pkg = ContentPackage.objects.get(code="B01", is_current=True)
        for lsn in pkg.data["lessons"]:
            for a in lsn["activities"]:
                Attempt.objects.create(user=self.user, package=pkg, chapter_code="B01", lesson_id=lsn["id"],
                                       activity_id=a["id"], activity_type=a["type"], status="calificado", score=1.0,
                                       response={"text": "x"})
        packages = current_packages()
        self.assertTrue(progress_for(self.user, packages, "base20")[1]["done"])
        self.assertFalse(progress_for(self.user, packages, "plan40").get(1, {}).get("done"))
        r = self.client.get(reverse("portfolio"))
        self.assertContains(r, "Base 20 · Día 1 · Hola")
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Plan base de 20 días")
        self.assertContains(r, "1</strong>/20 días completados")

    def test_home_shows_base_ring_when_only_base_started(self):
        from accounts.models import get_profile
        profile = get_profile(self.user)
        profile.base_start = timezone.localdate()
        profile.save()
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Tu camino al plan de 40 días")
        self.assertEqual(r.content.decode().count("<path "), 20)
        self.assertContains(r, reverse("program_day", args=["base20", 1]))
