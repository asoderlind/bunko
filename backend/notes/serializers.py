from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from .models import Note, NoteTag, ProviderProfile, Tag


class TagSerializer(serializers.ModelSerializer):
    note_count = serializers.IntegerField(source="usage_count", read_only=True)

    class Meta:
        model = Tag
        fields = ["id", "slug", "name", "description", "color", "note_count"]


class TagWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "slug", "name", "description", "color"]
        read_only_fields = ["id"]

    def validate_slug(self, value):
        # Slug is the identity of a tag and is referenced by stored model output,
        # so it must stay a valid slug.
        if not value or value != value.lower():
            raise serializers.ValidationError("slug must be lowercase")
        return value


class NoteTagSerializer(serializers.ModelSerializer):
    tag_id = serializers.UUIDField(source="tag.id", read_only=True)
    slug = serializers.CharField(source="tag.slug", read_only=True)
    name = serializers.CharField(source="tag.name", read_only=True)
    color = serializers.CharField(source="tag.color", read_only=True)

    class Meta:
        model = NoteTag
        fields = ["id", "tag_id", "slug", "name", "color", "source", "confidence"]


class NoteSerializer(serializers.ModelSerializer):
    tags = NoteTagSerializer(source="note_tags", many=True, read_only=True)
    tag_status = serializers.CharField(read_only=True)
    tag_error = serializers.CharField(read_only=True)
    title = serializers.CharField(required=False, allow_blank=True)
    title_source = serializers.CharField(read_only=True)

    class Meta:
        model = Note
        fields = [
            "id",
            "body_md",
            "title",
            "title_source",
            "tags",
            "tag_status",
            "tag_error",
            "local_only",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_body_md(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Note body cannot be empty.")
        return value

    def create(self, validated_data):
        note = Note.objects.create(**validated_data)
        note.tag_status = Note.TagStatus.PENDING
        note.save(update_fields=["tag_status"])
        return note

    def update(self, instance, validated_data):
        body_changed = "body_md" in validated_data and (
            validated_data["body_md"] != instance.body_md
        )
        for key, value in validated_data.items():
            setattr(instance, key, value)

        update_fields = list(validated_data.keys())

        # An explicit title is the user's; remember that so the tagging worker
        # never overwrites it, and so a later body edit doesn't discard it.
        if "title" in validated_data:
            if validated_data["title"].strip():
                instance.title_source = Note.TitleSource.USER
            else:
                # Cleared on purpose: fall back to derived, allow regeneration.
                instance.title_source = Note.TitleSource.DERIVED
                instance.title = instance.derive_title()
                update_fields += ["title", "title_source"]
            update_fields.append("title_source")
        elif body_changed and instance.title_source != Note.TitleSource.USER:
            # Body changed and the title isn't the user's: show the derived one
            # immediately, and let the worker replace it with a generated one.
            instance.title = instance.derive_title()
            instance.title_source = Note.TitleSource.DERIVED
            update_fields += ["title", "title_source"]
        if body_changed:
            # Requeue tagging and bump the revision so any in-flight worker
            # result is discarded rather than written over the new body.
            instance.tag_status = Note.TagStatus.PENDING
            instance.tag_error = ""
            instance.content_revision = F("content_revision") + 1
            update_fields += ["tag_status", "tag_error", "content_revision"]
        if update_fields:
            instance.save(update_fields=update_fields or None)
        instance.refresh_from_db()
        return instance


class ProviderProfileSerializer(serializers.ModelSerializer):
    """api_key_env is a NAME, never a secret. Nothing here exposes a key."""

    class Meta:
        model = ProviderProfile
        fields = [
            "id",
            "label",
            "base_url",
            "model",
            "api_key_env",
            "is_default",
            "is_local",
            "enabled",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {"is_default": {"validators": []}}

    def get_unique_together_validators(self):
        # DRF generates a UniqueTogetherValidator from the conditional
        # `uniq_default_provider` constraint, which rejects a new default before
        # our code can demote the old one. Setting Meta.validators = [] does not
        # suppress it, so override the generator. Demotion happens in validate().
        return []

    def get_fields(self):
        fields = super().get_fields()
        # DRF also infers a field-level UniqueValidator on `is_default` from the
        # conditional constraint. The DB constraint is authoritative; drop it so
        # promoting a different default is possible.
        if "is_default" in fields:
            fields["is_default"].validators = [
                v
                for v in fields["is_default"].validators
                if v.__class__.__name__ != "UniqueValidator"
            ]
        return fields

    def validate(self, attrs):
        # The DB enforces at most one default. Demote any existing default so
        # promoting another profile doesn't trip the constraint on save.
        is_default = attrs.get("is_default")
        if is_default is None and self.instance is not None:
            is_default = self.instance.is_default
        if is_default:
            qs = ProviderProfile.objects.filter(is_default=True)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            qs.update(is_default=False)
        return attrs


class TagMergeSerializer(serializers.Serializer):
    merge_into = serializers.SlugField()

    def validate_merge_into(self, value):
        try:
            self.target = Tag.objects.get(slug=value)
        except Tag.DoesNotExist:
            raise serializers.ValidationError("No tag with that slug.")
        return value

    @transaction.atomic
    def save(self, **kwargs):
        source = self.context["tag"]
        target = self.target
        if source.pk == target.pk:
            return target

        # Move NoteTag rows, skipping notes that already have the target tag.
        existing_note_ids = set(
            NoteTag.objects.filter(tag=target).values_list("note_id", flat=True)
        )
        NoteTag.objects.filter(tag=source).exclude(
            note_id__in=existing_note_ids
        ).update(tag=target)
        # Delete leftovers (duplicates for notes that already had target).
        NoteTag.objects.filter(tag=source).delete()

        # usage_count is denormalised; recompute rather than increment to avoid drift.
        for tag in (source, target):
            tag.usage_count = tag.note_tags.count()
            tag.save(update_fields=["usage_count"])
        source.delete()
        return target
