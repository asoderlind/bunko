# Changelog

## Unreleased

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
