from django.contrib import admin

from .models import ReviewItem


@admin.register(ReviewItem)
class ReviewItemAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "kind", "stage", "due", "blocking", "last_correct")
    list_filter = ("kind", "chapter_code", "blocking")
    search_fields = ("user__username", "key")
