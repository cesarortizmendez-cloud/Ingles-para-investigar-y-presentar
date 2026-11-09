from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "specialty", "reference_voice", "no_mic_mode")
    list_filter = ("specialty", "reference_voice")
    search_fields = ("user__username", "display_name", "institution")
