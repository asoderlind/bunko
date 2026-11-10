"""Tagging worker. The `tag_status` column is the queue.

Run as `python -m app.worker`. Polls for pending notes, calls the provider
outside the claim transaction, and writes results only if the note was not
edited meanwhile.
"""

from __future__ import annotations

import logging
import signal
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import Note, NoteTag, ProviderProfile, Tag, TagSource, TagStatus, TitleSource
from app.tagging import client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("tagging")

settings = get_settings()

_shutdown = False


def _handle_signal(signum: int, _frame: Any) -> None:
    global _shutdown
    log.info("signal %s received, finishing current job then exiting", signum)
    _shutdown = True


def reap_stale(session: Session) -> None:
    """Rows stuck in processing beyond the stale window go back to pending."""
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.tagging_stale_seconds)
    stale = session.scalars(
        select(Note).where(
            Note.tag_status == TagStatus.PROCESSING,
            Note.updated_at < cutoff,
        )
    ).all()
    for note in stale:
        note.tag_status = TagStatus.PENDING
    if stale:
        session.commit()
        log.warning("reaped %s stale processing note(s)", len(stale))


def claim_one(session: Session) -> dict[str, Any] | None:
    """Claim one pending note with FOR UPDATE SKIP LOCKED."""
    note = session.scalars(
        select(Note)
        .where(Note.tag_status == TagStatus.PENDING)
        .order_by(Note.updated_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()
    if note is None:
        return None

    claimed = {
        "id": note.id,
        "body_md": note.body_md,
        "local_only": note.local_only,
        "revision": note.content_revision,
    }
    note.tag_status = TagStatus.PROCESSING
    note.tag_error = ""
    session.commit()
    return claimed


def _resolve_profile(session: Session) -> ProviderProfile | None:
    default = session.scalars(
        select(ProviderProfile).where(
            ProviderProfile.enabled.is_(True), ProviderProfile.is_default.is_(True)
        )
    ).first()
    if default is not None:
        return default
    return session.scalars(
        select(ProviderProfile)
        .where(ProviderProfile.enabled.is_(True))
        .order_by(ProviderProfile.is_local)
    ).first()


def _recount(session: Session, tag: Tag) -> None:
    tag.usage_count = (
        session.scalar(select(func.count()).select_from(NoteTag).where(NoteTag.tag_id == tag.id))
        or 0
    )


def complete(
    session: Session,
    claimed: dict[str, Any],
    valid_tags: list[dict[str, Any]],
    title: str | None = None,
) -> None:
    note = session.get(Note, claimed["id"], with_for_update=True)
    if note is None:
        return
    if note.content_revision != claimed["revision"]:
        log.info("note %s changed during tagging; discarding result", claimed["id"])
        return
    if note.tag_status != TagStatus.PROCESSING:
        log.info("note %s no longer processing; discarding", claimed["id"])
        return

    for item in valid_tags:
        tag = session.scalars(select(Tag).where(Tag.slug == item["slug"])).first()
        if tag is None:
            continue
        exists = session.scalars(
            select(NoteTag).where(NoteTag.note_id == note.id, NoteTag.tag_id == tag.id)
        ).first()
        if exists is None:
            session.add(
                NoteTag(
                    note_id=note.id,
                    tag_id=tag.id,
                    source=TagSource.AUTO,
                    confidence=item["confidence"],
                )
            )
        session.flush()
        _recount(session, tag)

    # Only replace a machine-made title; never clobber the user's own.
    if title and note.title_source != TitleSource.USER:
        note.title = title[:200]
        note.title_source = TitleSource.GENERATED

    note.tag_status = TagStatus.DONE
    note.tag_error = ""
    session.commit()
    log.info(
        "note %s done with %s tag(s): %s",
        claimed["id"],
        len(valid_tags),
        [t["slug"] for t in valid_tags],
    )


def fail(session: Session, claimed: dict[str, Any], reason: str) -> None:
    note = session.get(Note, claimed["id"], with_for_update=True)
    if note is None:
        return
    if note.content_revision != claimed["revision"]:
        return
    note.tag_status = TagStatus.FAILED
    note.tag_error = reason[:200]
    session.commit()


def tag_note(session: Session, claimed: dict[str, Any]) -> None:
    note_id: UUID = claimed["id"]
    profile = _resolve_profile(session)
    if profile is None:
        log.warning("no enabled provider; failing note %s", note_id)
        fail(session, claimed, "no provider configured")
        return

    # Hard rule: a local_only note must never reach a remote provider.
    if claimed["local_only"] and not profile.is_local:
        log.warning("note %s is local_only but provider %r is not", note_id, profile.label)
        fail(session, claimed, "local_only note with no local provider configured")
        return

    tags = session.scalars(
        select(Tag)
        .order_by(Tag.usage_count.desc(), Tag.slug)
        .limit(settings.tagging_prompt_tag_limit)
    ).all()
    if not tags:
        log.info("no tags defined; completing note %s with zero tags", note_id)
        complete(session, claimed, [], None)
        return

    system_prompt = client.build_system_prompt(list(tags))
    allowed = {t.slug for t in tags}
    body = client.truncate_body(claimed["body_md"], settings.tagging_max_input_chars)

    last_error = ""
    for attempt in (1, 2):
        if _shutdown and attempt == 2:
            break
        try:
            payload = client.call_provider(
                profile, system_prompt, body, settings.tagging_request_timeout
            )
            valid, _none, title = client.parse_tag_response(payload, allowed)
            complete(session, claimed, valid, title)
            return
        except client.OutputError as exc:
            last_error = f"invalid model output: {exc}"
            log.warning("note %s attempt %s: %s", note_id, attempt, exc)
        except client.ProviderError as exc:
            last_error = str(exc)
            log.warning("note %s attempt %s: %s", note_id, attempt, exc)
        session.rollback()

    fail(session, claimed, (last_error or "tagging failed")[:200])


def run_once() -> bool:
    """Process at most one note. Returns True if work was done."""
    session = SessionLocal()
    try:
        reap_stale(session)
        claimed = claim_one(session)
        if claimed is None:
            return False
        try:
            tag_note(session, claimed)
        except Exception:
            log.exception("unexpected error tagging %s", claimed["id"])
            session.rollback()
            fail(session, claimed, "internal error")
        return True
    finally:
        session.close()


def run_background(stop_event: Any) -> None:
    """Run the durable tagging queue inside the web process.

    A single worker thread is enough for this single-user app. The queue is
    stored in SQLite, so pending notes survive process restarts.
    """
    log.info("background tagging worker started (poll every %ss)", settings.tagging_poll_seconds)
    while not stop_event.is_set():
        if not run_once():
            stop_event.wait(settings.tagging_poll_seconds)
    log.info("background tagging worker stopped")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Tagging worker")
    parser.add_argument("--once", action="store_true", help="drain the queue then exit")
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    log.info("tagging worker started (poll every %ss)", settings.tagging_poll_seconds)

    while not _shutdown:
        if not run_once():
            if args.once:
                log.info("queue empty, exiting")
                break
            deadline = time.monotonic() + settings.tagging_poll_seconds
            while not _shutdown and time.monotonic() < deadline:
                time.sleep(min(0.2, deadline - time.monotonic()))

    log.info("tagging worker stopped")


if __name__ == "__main__":
    main()
