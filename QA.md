# easy-notes — QA guide

## Access

| | |
|---|---|
| **URL** | http://100.113.71.15:8000 |
| **Username** | `axel` |
| **Password** | `changeme-qa-only` |
| **Login page** | http://100.113.71.15:8000/admin/login/?next=/ |
| **Tailnet only** | bound to `100.113.71.15`; not on LAN or internet |

Sign in once at the login page, then go to `http://100.113.71.15:8000/`.
On iPhone: Share → **Add to Home Screen** to test standalone/PWA mode.

Change that password when you're done (`docker compose -f docker-compose.dev.yml exec web python manage.py changepassword axel`).

---

## What to test

### 1. Scratchpad (default route)
- [ ] Open `/`. The textarea should be focused with no cursor tap needed.
- [ ] Type a few sentences — a Save bar appears at the bottom only once there's text.
- [ ] Kill the browser tab, reopen `/` → **draft is still there** (localStorage).
- [ ] Press `⌘/Ctrl+Enter` → saves and jumps to the note view.

### 2. Tagging (the interesting part)
- [ ] Write a note about a specific topic, e.g.
      *"Bought 200 shares of NVDA at the open, sold half into the close."*
- [ ] On the note view you should see a grey **tagging…** chip.
- [ ] Within ~5–30s it swaps for real chips. Expect `Trading` for that example.
- [ ] Write something that fits nothing (*"the sky looked a strange colour today"*)
      → ends with **zero chips**, status `done`. It lands in **Inbox**.
- [ ] Chips are removable (×). `+ tag` opens a dropdown of existing tags only.

### 3. Edit during tagging (regression check)
- [ ] Save a note about trading, then **immediately** tap the body and change it to
      something about cooking, and save within a few seconds.
- [ ] Result should be `Cooking` and **no stale `Trading` tag**. There should be
      no mix of the two.

### 4. Search
- [ ] Press `/` anywhere (not while in a text field) → search box opens.
- [ ] Search a word from the middle of a note, e.g. `sourdough`.
- [ ] Search results are clickable. `Esc` closes the search box.

### 5. Tags screen (`/tags`)
- [ ] Create a tag: name + one-line description. Check the emitted slug.
- [ ] **Merge**: pick a tag → “Merge…” → choose a target. Notes move, the source
      disappears, counts should add up (no duplicates).
- [ ] Try merging a tag into itself / creating a duplicate slug → should refuse.

### 6. Filters and inbox
- [ ] `/inbox` shows only `done` notes with zero tags.
- [ ] From the note list, tag chips filter by that tag.

### 7. Mobile / touch
- [ ] All tappable things ≥44px (buttons, chips, back link).
- [ ] No hover-only affordances — everything reachable by tap.
- [ ] Rotate to landscape; layout should not break.
- [ ] In standalone PWA mode, the top bar respects the notch/safe area.

### 8. Failure paths
- [ ] Note with `local_only` can't be tested from the UI yet (no toggle in the SPA) —
      verified server-side instead; see notes below.

---

## Deliberately not in this build

- No `local_only` toggle in the SPA (backend enforces it; UI control is M3+).
- No Providers settings screen (part of the spec's M2/M5 work).
- Attachments, vector search, multi-user — out of scope for v1.
- HTTPS — it's plain HTTP over the tailnet for now. M5 adds TLS.

---

## If something is broken

```bash
cd ~/repos/easy-notes
sg docker -c "docker compose -f docker-compose.dev.yml ps"
sg docker -c "docker compose -f docker-compose.dev.yml logs -f web worker"
```

Worker stuck or want a clean slate:

```bash
sg docker -c "docker compose -f docker-compose.dev.yml restart worker"
```

Note: this shell needs `sg docker -c "..."` because the docker group was added
after this login session started. A fresh login makes plain `docker` work.

---

## Verified server-side before this QA pass

| Check | Result |
|---|---|
| Note → pending → tagged → done | ✅ ~8s end-to-end |
| `local_only` + remote provider | ✅ `failed`, no network call made |
| Edit during tagging | ✅ stale result discarded (revision guard) |
| SIGTERM mid-job | ✅ finishes job, 0 rows stuck in `processing` |
| Tag merge with duplicate note | ✅ collapses, no duplicate rows |
| Empty note | ✅ rejected 400 |
| FTS phrase search | ✅ finds mid-note text |
| Provider swap (default handover) | ✅ old default demoted |
| App reachable on tailnet IP only | ✅ |
