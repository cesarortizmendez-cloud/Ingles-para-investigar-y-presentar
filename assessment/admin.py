from django.contrib import admin

from .models import DiagnosticResult, RubricScore


@admin.register(RubricScore)
class RubricScoreAdmin(admin.ModelAdmin):
    list_display = ("attempt", "rubric_code", "rater_kind", "total", "passed", "created_at")
    list_filter = ("rubric_code", "rater_kind", "passed")


@admin.register(DiagnosticResult)
class DiagnosticResultAdmin(admin.ModelAdmin):
    list_display = ("user", "package_version", "created_at")
