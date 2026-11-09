import json

from django import forms
from django.contrib import admin, messages

from learning_core import contract

from .models import ChapterProgress, ContentPackage
from .services import bump_patch


class ContentPackageForm(forms.ModelForm):
    class Meta:
        model = ContentPackage
        fields = ["code", "kind", "version", "status", "title", "data", "change_note", "is_current"]

    def clean_data(self):
        data = self.cleaned_data["data"]
        if isinstance(data, str):
            data = json.loads(data)
        errors = contract.validate(data)
        if errors:
            raise forms.ValidationError(["Contrato editorial: " + e for e in errors[:15]])
        return data


@admin.register(ContentPackage)
class ContentPackageAdmin(admin.ModelAdmin):
    """Edición de contenidos.

    Guardar un cambio en el JSON de un paquete existente NO sobrescribe la versión:
    crea una versión nueva (sube el número de parche si no se cambió) y la deja
    vigente. Los intentos anteriores siguen apuntando a la versión con que se hicieron.
    """

    form = ContentPackageForm
    list_display = ("code", "version", "kind", "status", "title", "is_current", "created_at")
    list_filter = ("kind", "status", "is_current")
    search_fields = ("code", "title")
    readonly_fields = ("checksum", "created_at")

    def save_model(self, request, obj, form, change):
        if change and "data" in form.changed_data:
            previous = ContentPackage.objects.get(pk=obj.pk)
            new_version = obj.version if obj.version != previous.version else bump_patch(previous.version)
            data = dict(form.cleaned_data["data"])
            data["version"] = new_version
            data["status"] = obj.status
            ContentPackage.objects.filter(code=obj.code).update(is_current=False)
            obj.pk = None
            obj.version = new_version
            obj.data = data
            obj.is_current = True
            obj.title = data.get("title", obj.title)
            super().save_model(request, obj, form, False)
            messages.info(request, f"Se creó {obj.code} v{new_version}; la v{previous.version} se conserva para los intentos anteriores.")
            return
        if obj.is_current:
            ContentPackage.objects.filter(code=obj.code).exclude(pk=obj.pk).update(is_current=False)
        super().save_model(request, obj, form, change)


@admin.register(ChapterProgress)
class ChapterProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "chapter_code", "last_state", "provisional_on", "consolidated_on", "recovery_needed")
    list_filter = ("chapter_code", "last_state", "recovery_needed")
