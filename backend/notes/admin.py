from django.contrib import admin

from .models import Attachment, Note, NoteTag, ProviderProfile, Tag


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "tag_status", "local_only", "updated_at")
    list_filter = ("tag_status", "local_only")
    search_fields = ("title", "body_md")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "usage_count")
    search_fields = ("slug", "name")


@admin.register(NoteTag)
class NoteTagAdmin(admin.ModelAdmin):
    list_display = ("note", "tag", "source", "confidence")


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ("label", "base_url", "model", "is_default", "is_local", "enabled")


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("note", "mime", "byte_size", "created_at")
