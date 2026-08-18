# OneMove — Contracts Changelog

## [1.5.1] - 2026-08-19
### Added
- Canonical product branding locked to **OneMove**.
- Published canonical API, Data, and Event contracts.
- Defined 17-agent ownership boundaries in `docs/architecture/OWNERSHIP.md`.
- Added GCP Terraform IaC validation in `.github/workflows/terraform-ci.yml`.

### Changed
- Refactored authentication to strict fail-closed 401/403 across all `/api/v1/observatory` routes.
- Upgraded optimizer to consume authentic 12x94 OSRM travel duration matrix.
- Enabled asynchronous Pub/Sub worker job processing architecture.

### Fixed
- Fixed side-effects on `GET /api/v1/scenarios`.
- Resolved release identity drift via dynamic Git SHA lookup in `services/zonepilot/release.py`.
