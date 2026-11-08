import uuid

from django.db import models


class Tag(models.Model):
    """A tag. Exists only because a human created it (spec 11)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-usage_count", "slug"]

    def __str__(self):
        return self.slug


class Note(models.Model):
    class TagStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    body_md = models.TextField()
    title = models.CharField(max_length=200, blank=True)
    tag_status = models.CharField(
        max_length=20,
        choices=TagStatus.choices,
        default=TagStatus.PENDING,
        db_index=True,
    )
    local_only = models.BooleanField(default=False)

    # Set on every write that should invalidate in-flight tagging. The worker
    # writes results only if this still matches what it started with, so an
    # edit during dispatch can't be overwritten by stale tags.
    content_revision = models.PositiveIntegerField(default=0)

    # Reason tagging failed, for the failed state. Never user-facing prose.
    tag_error = models.CharField(max_length=200, blank=True)

    tags = models.ManyToManyField(Tag, through="NoteTag", related_name="notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tag_status", "updated_at"]),
        ]

    def __str__(self):
        return self.title or str(self.id)

    def derive_title(self):
        """First non-empty line of the body, stripped of markdown heading marks."""
        for line in self.body_md.splitlines():
            line = line.strip().lstrip("#").strip()
            if line:
                return line[:200]
        return ""

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = self.derive_title()
        super().save(*args, **kwargs)


class NoteTag(models.Model):
    class Source(models.TextChoices):
        AUTO = "auto", "Auto"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="note_tags")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="note_tags")
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.AUTO)
    confidence = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["note", "tag"], name="uniq_note_tag"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.note_id} -> {self.tag_id}"


class ProviderProfile(models.Model):
    """An OpenAI-compatible endpoint. API keys are env var NAMES only (spec 11)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=100)
    base_url = models.URLField(help_text="e.g. http://100.111.126.52:11434/v1")
    model = models.CharField(max_length=100)
    api_key_env = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name of an env var holding the key. Never the key itself.",
    )
    is_default = models.BooleanField(default=False)
    is_local = models.BooleanField(
        default=False,
        help_text="True if this endpoint never leaves the local network.",
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # At most one default, enforced in the DB rather than in save().
            models.UniqueConstraint(
                fields=["is_default"],
                condition=models.Q(is_default=True),
                name="uniq_default_provider",
            ),
        ]

    def __str__(self):
        return self.label


class Attachment(models.Model):
    """Reserved for v1.1. Created but unused (spec 2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="attachments/%Y/%m/")
    mime = models.CharField(max_length=100)
    byte_size = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.note_id}:{self.mime}"
