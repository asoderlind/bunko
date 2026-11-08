"""Tagging worker. The `tag_status` column is the queue (spec 6/11).

Usage: python manage.py run_tagging_worker
"""

from __future__ import annotations

import logging
import signal
import time
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from notes.models import Note, NoteTag, ProviderProfile, Tag

from tagging import client

log = logging.getLogger("tagging")


class Command(BaseCommand):
    help = "Poll for pending notes and tag them with the configured provider."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutdown = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process the queue until empty, then exit (used by tests).",
        )

    def handle(self, *args, **options):
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        once = options["once"]
        log.info("tagging worker started (poll every %ss)", settings.TAGGING_POLL_SECONDS)

        while not self._shutdown:
            self.reap_stale()
            did_work = self.process_one()
            if not did_work:
                if once:
                    log.info("queue empty, exiting (--once)")
                    break
                # Sleep in small slices so SIGTERM is honoured promptly.
                self._sleep(settings.TAGGING_POLL_SECONDS)

        log.info("tagging worker stopped")

    # -- internals ---------------------------------------------------------

    def _handle_signal(self, signum, frame):
        log.info("signal %s received, finishing current job then exiting", signum)
        self._shutdown = True

    def _sleep(self, seconds: float):
        deadline = time.monotonic() + seconds
        while not self._shutdown and time.monotonic() < deadline:
            time.sleep(min(0.2, deadline - time.monotonic()))

    def reap_stale(self):
        """Rows stuck in `processing` beyond the stale window go back to pending."""
        cutoff = timezone.now() - timedelta(seconds=settings.TAGGING_STALE_SECONDS)
        n = Note.objects.filter(
            tag_status=Note.TagStatus.PROCESSING,
            updated_at__lt=cutoff,
        ).update(tag_status=Note.TagStatus.PENDING)
        if n:
            log.warning("reaped %s stale processing note(s)", n)

    def claim_one(self):
        """Claim a single pending note using SKIP LOCKED. Returns a dict or None."""
        with transaction.atomic():
            note = (
                Note.objects.select_for_update(skip_locked=True)
                .filter(tag_status=Note.TagStatus.PENDING)
                .order_by("updated_at")
                .first()
            )
            if note is None:
                return None
            claimed = {
                "id": note.id,
                "body_md": note.body_md,
                "local_only": note.local_only,
                "revision": note.content_revision,
            }
            note.tag_status = Note.TagStatus.PROCESSING
            note.tag_error = ""
            note.save(update_fields=["tag_status", "tag_error"])
        return claimed

    def process_one(self) -> bool:
        claimed = self.claim_one()
        if claimed is None:
            return False
        try:
            self.tag_note(claimed)
        except Exception:  # noqa: BLE001 - worker must never die mid-loop
            log.exception("unexpected error tagging note %s", claimed["id"])
            self.fail(claimed, "internal error")
        return True

    def tag_note(self, claimed):
        note_id = claimed["id"]
        profile = (
            ProviderProfile.objects.filter(enabled=True, is_default=True).first()
            or ProviderProfile.objects.filter(enabled=True).order_by("is_local").first()
        )
        if profile is None:
            log.warning("no enabled provider profile; failing note %s", note_id)
            self.fail(claimed, "no provider configured")
            return

        # Hard rule (spec 11): a local_only note must never go to a remote provider.
        if claimed["local_only"] and not profile.is_local:
            # Decision: set `failed` and record why. A parked `pending` note would
            # spin forever in the polling UI with no way for the user to fix it.
            log.warning(
                "note %s is local_only but provider %r is not local", note_id, profile.label
            )
            self.fail(claimed, "local_only note with no local provider configured")
            return

        tags = list(
            Tag.objects.order_by("-usage_count", "slug")[
                : settings.TAGGING_PROMPT_TAG_LIMIT
            ]
        )
        if not tags:
            log.info("no tags defined; completing note %s with zero tags", note_id)
            self.complete(claimed, [], None)
            return

        system_prompt = client.build_system_prompt(tags)
        allowed = {t.slug for t in tags}
        body = client.truncate_body(claimed["body_md"], settings.TAGGING_MAX_INPUT_CHARS)

        last_error = None
        for attempt in (1, 2):
            if self._shutdown and attempt == 2:
                break
            try:
                payload = client.call_provider(
                    profile, system_prompt, body, settings.TAGGING_REQUEST_TIMEOUT
                )
                valid, _none_apply = client.parse_tag_response(payload, allowed)
                self.complete(claimed, valid, None)
                return
            except client.ValidationError_ as exc:
                last_error = f"invalid model output: {exc}"
                log.warning("note %s attempt %s: %s", note_id, attempt, exc)
            except client.ProviderError as exc:
                last_error = str(exc)
                log.warning("note %s attempt %s: %s", note_id, attempt, exc)

        self.fail(claimed, (last_error or "tagging failed")[:200])

    def complete(self, claimed, valid_tags, error):
        """Write results, but only if the note wasn't edited meanwhile."""
        with transaction.atomic():
            note = Note.objects.select_for_update().filter(pk=claimed["id"]).first()
            if note is None:
                log.info("note %s disappeared before write-back", claimed["id"])
                return
            if note.content_revision != claimed["revision"]:
                # Note was edited while we were calling the model. Discard: the
                # edit already requeued it. Leave status as set by the edit.
                log.info(
                    "note %s changed during tagging (rev %s != %s); discarding result",
                    claimed["id"],
                    claimed["revision"],
                    note.content_revision,
                )
                return
            if note.tag_status != Note.TagStatus.PROCESSING:
                log.info(
                    "note %s no longer processing (%s); discarding result",
                    claimed["id"],
                    note.tag_status,
                )
                return

            touched = []
            for item in valid_tags:
                tag = Tag.objects.filter(slug=item["slug"]).first()
                if tag is None:
                    continue
                NoteTag.objects.get_or_create(
                    note=note,
                    tag=tag,
                    defaults={
                        "source": NoteTag.Source.AUTO,
                        "confidence": item["confidence"],
                    },
                )
                touched.append(tag)

            for tag in touched:
                tag.usage_count = tag.note_tags.count()
                tag.save(update_fields=["usage_count"])

            note.tag_status = Note.TagStatus.DONE
            note.tag_error = error or ""
            note.save(update_fields=["tag_status", "tag_error"])
        log.info(
            "note %s done with %s tag(s): %s",
            claimed["id"],
            len(valid_tags),
            [t["slug"] for t in valid_tags],
        )

    def fail(self, claimed, reason: str):
        with transaction.atomic():
            note = Note.objects.select_for_update().filter(pk=claimed["id"]).first()
            if note is None:
                return
            if note.content_revision != claimed["revision"]:
                log.info("note %s edited before failure recorded; leaving for retry", claimed["id"])
                return
            note.tag_status = Note.TagStatus.FAILED
            note.tag_error = reason[:200]
            note.save(update_fields=["tag_status", "tag_error"])
