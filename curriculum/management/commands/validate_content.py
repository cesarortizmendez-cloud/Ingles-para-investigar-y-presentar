import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from learning_core import contract


class Command(BaseCommand):
    help = "Valida los paquetes de content/ contra el contrato editorial sin tocar la base de datos."

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="*", help="Archivos JSON (por defecto, todos los de content/)")

    def handle(self, *args, **options):
        root = Path(settings.CONTENT_DIR)
        files = [Path(f) for f in options["files"]] or sorted(
            list(root.glob("chapters/*.json")) + list(root.glob("diagnostic/*.json")) + list(root.glob("days/*.json")))
        failed = 0
        for path in files:
            errors = contract.validate(json.loads(path.read_text(encoding="utf-8")))
            if errors:
                failed += 1
                self.stdout.write(self.style.ERROR(f"✗ {path.name}"))
                for e in errors:
                    self.stdout.write(f"   - {e}")
            else:
                self.stdout.write(self.style.SUCCESS(f"✓ {path.name}"))
        if failed:
            raise CommandError(f"{failed} archivo(s) con errores.")
