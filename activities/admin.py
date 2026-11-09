from django.contrib import admin

from .models import Attempt


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_id", "attempt_number", "source", "status", "score", "created_at")
    list_filter = ("chapter_code", "source", "status", "activity_type", "role")
    search_fields = ("user__username", "activity_id")
    readonly_fields = [f.name for f in Attempt._meta.fields]
