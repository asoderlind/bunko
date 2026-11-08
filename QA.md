# easy-notes — QA guide

## Access

| | |
|---|---|
| **URL** | http://100.113.71.15:8000 |
| **Password** | `changeme-qa-only` |
| **Tailnet only** | bound to `100.113.71.15`; not on LAN or internet |

You land on a password screen — no username, just the password.
On iPhone: Share → **Add to Home Screen** to test standalone/PWA mode.

Change that password when you're done (`docker compose -f docker-compose.dev.yml exec web python manage.py changepassword axel`).

---

## What to test

### 0. Login gate  ← new
- [ ] Open the URL in a **private/incognito window**: you must see the password
      screen, never the note interface (not even a flash of it).
- [ ] Wrong password → inline "Wrong password.", field stays usable.
- [ ] Try ~20 wrong passwords quickly → "Too many attempts. Wait a minute."
- [ ] Correct password → app loads.
- [ ] **Sign out** (bottom of sidebar) → back to the password screen; reload
      keeps you signed out.
- [ ] Reload while signed in → stays signed in (session persists ~30 days).

### 0b. Sidebar  ← new
- [ ] Desktop: fixed rail on the left with Notes / Needs tags / Tags, active
      item highlighted.
- [ ] Phone: hamburger in the top bar opens a drawer; tapping a link closes it;
      tapping the dark backdrop also closes it.
- [ ] Sign out sits at the bottom of the sidebar.
- [ ] **Recent notes** are listed under the nav, newest first, capped at 30.
- [ ] Long titles end in “…” and the tag pills stay pinned to the right.
- [ ] Tap a note in the sidebar → opens it, row highlights.
- [ ] On phone the drawer covers ~90% of the width.
- [ ] First nav entry reads **New note** (it is the scratchpad).
- [ ] Each note row has a **⋮** button (always visible on touch):
  - [ ] **Download** → saves `<title>.md` with YAML front matter
        (title, created, updated, tags).
  - [ ] **Change title** → dialog, Save renames it in place.
  - [ ] **Delete** → confirm, then it disappears from the list.
- [ ] Tapping ⋮ must not open the note.

### 0c. Tag filter  ← new
- [ ] Tap **Filter** above the note list to expand it.
- [ ] One coloured checkbox per tag; each tag has a different colour.
- [ ] Ticking one filters the note list (and sets the URL, so a reload keeps it).
- [ ] Ticking a second one filters to notes having **both**.
- [ ] The count badge on “Filter” shows how many are active; **Clear filters**
      resets.

### 0c2. Note view  ← changed
- [ ] No Back or Delete buttons at the top of a note — delete lives in the
      sidebar ⋮ menu.
- [ ] Tag chips sit at the very top; the title renders above the body.

### 0d. Generated titles  ← new
- [ ] Save a note with a long body. The title starts as the first line, then
      within ~10s becomes a short generated title (e.g. “Sourdough Starter
      Progress”) and stops being cut off in the sidebar.
- [ ] Open the note, tap it, type your own title, Save → your title sticks.
- [ ] Now edit the **body** and Save → your title is **still yours**, unchanged.
- [ ] Clear the title and Save → it reverts to derived, and the worker generates
      a new one on the next pass.

### 1. Scratchpad (default route)
- [ ] Open `/`. The textarea should be focused with no cursor tap needed.
- [ ] Type a few sentences — a Save bar appears at the bottom only once there's text.
- [ ] Kill the browser tab, reopen `/` → **draft is still there** (localStorage).
- [ ] Press `⌘/Ctrl+Enter` → saves and jumps to the note view.
- [ ] Search icon in the top bar opens a search field; tap outside/Esc closes.

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
- [ ] Press `/` anywhere (not while in a text field) → search opens.
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
- Tag list is not paginated in the UI (fine up to a few hundred tags).
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
| Anonymous data access blocked | ✅ 403 on all data endpoints |
| Password-only login + throttle | ✅ 401 wrong, 200 right, 429 on flood |
