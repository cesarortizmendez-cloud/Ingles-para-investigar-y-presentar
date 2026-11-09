import json
import os
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from curriculum.models import ContentPackage

STATIC = {"STORAGES": {"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}}


@override_settings(**STATIC)
class RememberSessionTests(TestCase):
    """«Mantener la sesión abierta»: 90 días si se marca; hasta cerrar el navegador si no."""

    @classmethod
    def setUpTestData(cls):
        get_user_model().objects.create_user("ana", password="clave-segura-321")

    def test_login_page_asks(self):
        r = self.client.get(reverse("login"))
        self.assertContains(r, "Mantener la sesión abierta en este equipo")
        self.assertContains(r, 'name="remember"')
        self.assertContains(r, "data-app-note")

    def test_remember_keeps_session(self):
        r = self.client.post(reverse("login"), {"username": "ana", "password": "clave-segura-321", "remember": "on"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(self.client.session.get_expire_at_browser_close())
        self.assertGreaterEqual(self.client.session.get_expiry_age(), 60 * 60 * 24 * 89)

    def test_without_remember_closes_with_browser(self):
        self.client.post(reverse("login"), {"username": "ana", "password": "clave-segura-321"})
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_signup_can_remember(self):
        r = self.client.post(reverse("signup"), {"username": "nuevo", "password1": "Otra-clave-larga-987",
                                                 "password2": "Otra-clave-larga-987", "remember": "on"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(self.client.session.get_expire_at_browser_close())


@override_settings(**STATIC)
class PwaTests(TestCase):
    def test_manifest_is_installable(self):
        data = json.loads(self.client.get(reverse("manifest")).content)
        self.assertEqual(data["display"], "standalone")
        self.assertEqual(data["id"], "/")
        self.assertTrue(any(i["purpose"] == "maskable" for i in data["icons"]))
        self.assertTrue(any(i["sizes"] == "512x512" for i in data["icons"]))
        self.assertEqual({s["form_factor"] for s in data["screenshots"]}, {"wide", "narrow"})
        self.assertEqual(len(data["shortcuts"]), 3)

    def test_install_sheet_has_every_platform(self):
        get_user_model().objects.create_user("ana", password="clave-segura-321")
        self.client.login(username="ana", password="clave-segura-321")
        html = self.client.get(reverse("catalog")).content.decode()
        for platform in ("ios", "ios-other", "android", "desktop", "mac-safari", "desktop-firefox"):
            self.assertIn(f'data-install-platform="{platform}"', html)
        self.assertIn("Agregar al Dock", html)
        self.assertIn("Agregar a inicio", html)

    def test_service_worker(self):
        r = self.client.get(reverse("service_worker"))
        self.assertEqual(r["Service-Worker-Allowed"], "/")
        self.assertIn(b"ingles-v", r.content)


class ProductionSetupTests(TestCase):
    def test_preparar_produccion_is_repeatable(self):
        env = {"DJANGO_SUPERUSER_USERNAME": "admin", "DJANGO_SUPERUSER_PASSWORD": "Clave-admin-123"}
        with mock.patch.dict(os.environ, env):
            out = StringIO()
            call_command("preparar_produccion", stdout=out)
            self.assertIn("Administrador «admin» creado", out.getvalue())
            out2 = StringIO()
            call_command("preparar_produccion", stdout=out2)
            self.assertIn("ya existe", out2.getvalue())
            self.assertIn("0 nuevos", out2.getvalue())
        admin = get_user_model().objects.get(username="admin")
        self.assertTrue(admin.is_superuser and admin.check_password("Clave-admin-123"))
        self.assertEqual(ContentPackage.objects.filter(kind="day", is_current=True).count(), 60)

    def test_without_admin_vars(self):
        with mock.patch.dict(os.environ, {"DJANGO_SUPERUSER_USERNAME": "", "DJANGO_SUPERUSER_PASSWORD": ""}):
            out = StringIO()
            call_command("preparar_produccion", stdout=out)
        self.assertIn("no se crea administrador", out.getvalue())
        self.assertFalse(get_user_model().objects.filter(is_superuser=True).exists())
