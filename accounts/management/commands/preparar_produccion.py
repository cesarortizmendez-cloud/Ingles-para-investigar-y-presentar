"""Deja lista la base de datos de producción (Neon): tablas, contenido y administrador.

Uso (lo ejecuta Vercel en cada despliegue mediante vercel_build.py; también sirve a mano):

    python manage.py preparar_produccion

Es seguro repetirlo: las migraciones ya aplicadas se saltan, el contenido sin cambios no se duplica y el
administrador solo se crea si no existe.

Administrador (opcional), con variables de entorno:
    DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_PASSWORD y DJANGO_SUPERUSER_EMAIL (opcional).
    Si el usuario ya existe no se toca, salvo que DJANGO_SUPERUSER_RESET=1 (cambia su contraseña).
"""
import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Migra la base, importa content/ y crea el administrador desde variables de entorno."

    def handle(self, *args, **options):
        engine = connection.vendor
        self.stdout.write(f"Base de datos: {engine} ({connection.settings_dict.get('HOST') or connection.settings_dict.get('NAME')})")

        self.stdout.write(self.style.MIGRATE_HEADING("1/3 Migraciones"))
        call_command("migrate", interactive=False, verbosity=1)

        self.stdout.write(self.style.MIGRATE_HEADING("2/3 Contenido (capítulos, diagnóstico, Base 20 y Plan 40)"))
        call_command("import_content", verbosity=0, stdout=_Quiet(self.stdout))

        self.stdout.write(self.style.MIGRATE_HEADING("3/3 Administrador"))
        self._ensure_admin()
        self.stdout.write(self.style.SUCCESS("Producción lista."))

    def _ensure_admin(self):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not username or not password:
            self.stdout.write("Sin DJANGO_SUPERUSER_USERNAME/PASSWORD: no se crea administrador (puedes agregarlas después).")
            return
        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if user is None:
            User.objects.create_superuser(username=username, email=os.environ.get("DJANGO_SUPERUSER_EMAIL", ""),
                                          password=password)
            self.stdout.write(self.style.SUCCESS(f"Administrador «{username}» creado."))
        elif os.environ.get("DJANGO_SUPERUSER_RESET") == "1":
            user.set_password(password)
            user.is_staff = user.is_superuser = True
            user.save()
            self.stdout.write(self.style.WARNING(f"Contraseña de «{username}» actualizada (DJANGO_SUPERUSER_RESET=1)."))
        else:
            self.stdout.write(f"Administrador «{username}» ya existe: sin cambios.")


class _Quiet:
    """Resume la salida de import_content (una línea por paquete sería demasiado en los registros de Vercel)."""

    def __init__(self, out):
        self.out, self.new, self.same = out, 0, 0

    def write(self, msg="", *a, **k):
        if ": nuevo" in msg:
            self.new += 1
        elif "sin cambios" in msg:
            self.same += 1
        elif "paquetes procesados" in msg:
            self.out.write(f"{msg.strip()} ({self.new} nuevos, {self.same} sin cambios)")

    def flush(self):
        pass
