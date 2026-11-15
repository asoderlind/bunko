# Changelog

## Unreleased

## 0.1.0

### Added

- Import one or more Markdown notes from Settings, with independent title and tag generation options.
- Read YAML front matter on import, prioritizing titles, dates, tags, folder paths, and privacy over generation options.
- Export collections as ZIP archives containing one Markdown file per note with portable metadata.
- Import collection ZIPs transactionally without AI generation, preserving metadata and leaving existing notes intact.
- Validate collection archives and limit compressed size, expanded size, entry count, and individual note size.

### Changed

- Group Generate title and Generate tags below Move to in the note menu and simplify provider-related labels.
- Keep title generation and tag generation independent.
- Make private notes manual-only and hide their generation actions.
- Use the same metadata format for individual note downloads and collection exports.
- Show generation results as temporary toasts instead of persistent failure badges or repeated warnings on reopening notes.

### Fixed

- Preserve existing tags when generating a title and preserve titles when generating tags.
- Cancel legacy private-note generation jobs and clear their stale failure state.
- Preserve supplied timestamps in UTC during import.

### Upgrade notes

- Includes database migrations for generation modes and private-note queue cleanup.
- Collection imports add notes; importing the same collection again creates duplicates.
- Collection exports include private notes as plain text, but exclude attachments, provider settings, and empty folders. Back up the persistent data directory for a complete backup.

## 0.0.4

### Added

- App icons for browser tabs, Apple home screens, and PWA manifests, with SVG sources and reproducible PNG generation.

### Fixed

- Bring the provider edit form into view and focus its name field when selecting Edit in Configured providers.
- Make Change title open the rename dialog from the sidebar and note editor.
- Refresh the sidebar tree after renaming and show a retryable error if saving fails.

## 0.0.3

### Changed

- Validate release tags against their matching changelog entries before publishing container images.
- Create GitHub releases only after the versioned image is published, using release-specific notes.
- Document version-pinned HomeLab deployments and the release procedure.

## 0.0.2 — 2026-11-11

Provider configuration, privacy controls, generative tag suggestions, and a smoother note workflow.

### Added

- In-app provider configuration with OpenRouter-compatible support and SQLite-backed API keys.
- Private notes with local-provider-only generative processing and privacy indicators.
- Suggested tag generation from a safe sample of note titles and excerpts, with Keep/Dismiss controls.
- Automatic title and tag regeneration on save, preserving manually renamed titles.
- Manual title generation and re-tagging actions from the note menu.
- KaTeX rendering for inline and block mathematical expressions.
- Styled delete confirmation dialog.

### Changed

- New notes transition smoothly into the normal note editor without losing saved content.
- Generated titles and tags refresh automatically across note views and lists.
- Automatic tags are replaced on regeneration while manual tags are preserved.
- Private notes are excluded from remote tag-suggestion samples.

## 0.0.1 — 2026-11-10

Initial production-oriented release.

### Added

- SQLite storage for the single-container deployment.
- Alembic migration handling that preserves the current revision on restart.
- In-process background tagging worker.
- Persistent `/data` storage for the database and note media.
- Rootless Podman/NixOS deployment preparation.
- `bunko.soderlind.dev` deployment target preparation.
- Folder creation controls with icon-only confirm and cancel buttons.
- Immediate sidebar refresh when moving notes between folders.
- GitHub Actions publishing of a `linux/amd64` image for the Dell host.
