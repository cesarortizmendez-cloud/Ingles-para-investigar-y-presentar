"""Paso de construcción en Vercel (pyproject.toml → [tool.vercel.scripts] build).

Vercel lo ejecuta después de instalar las dependencias y antes de publicar. Prepara la base de datos Neon
(migraciones, contenido y administrador). Vercel ejecuta collectstatic por su cuenta.

Para las migraciones usa la conexión directa de Neon (DATABASE_URL_UNPOOLED) si existe: es la recomendada
para cambios de esquema; la app en ejecución usa DATABASE_URL (con pooler).
"""
import os
import sys


def main() -> int:
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not url:
        print("ERROR: falta DATABASE_URL. En Vercel: Storage → Connect Database → Neon (o agrega la variable a mano).")
        return 1
    if not os.environ.get("DJANGO_SECRET_KEY"):
        print("ERROR: falta DJANGO_SECRET_KEY. En Vercel: Settings → Environment Variables.")
        return 1
    direct = os.environ.get("DATABASE_URL_UNPOOLED") or os.environ.get("POSTGRES_URL_NON_POOLING")
    if direct:
        os.environ["DATABASE_URL"] = direct
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django
    from django.core.management import call_command

    django.setup()
    call_command("preparar_produccion")
    return 0


if __name__ == "__main__":
    sys.exit(main())
