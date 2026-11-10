# Changelog

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
