from django.contrib import admin

from .models import Recording


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_id", "duration_s", "size_bytes", "consent_share", "created_at")
    list_filter = ("consent_share", "transcript_source")
    exclude = ("audio",)  # el audio solo se escucha con autorización (vista voz/<id>/audio/)
    readonly_fields = ("user", "attempt", "package", "activity_id", "mime", "size_bytes", "duration_s",
                       "transcript", "transcript_source", "asr_errors_flagged", "created_at")
