from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from curriculum.services import ContentError, import_directory, load_course, load_plan


class Command(BaseCommand):
    help = "Valida e importa los paquetes de content/ como versiones vigentes (no altera versiones previas)."

    def add_arguments(self, parser):
        parser.add_argument("--path", help="Carpeta de contenido (por defecto settings.CONTENT_DIR)")

    def handle(self, *args, **options):
        load_course.cache_clear()
        load_plan.cache_clear()
        try:
            results = import_directory(Path(options["path"]) if options.get("path") else None)
        except ContentError as exc:
            raise CommandError(f"Contenido inválido:\n{exc}") from exc
        for code, version, created in results:
            label = "nuevo" if created else "sin cambios"
            self.stdout.write(f"{code} v{version}: {label}")
        self.stdout.write(self.style.SUCCESS(f"{len(results)} paquetes procesados."))
