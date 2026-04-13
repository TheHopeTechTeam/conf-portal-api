# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.19] - 2026-04-13

### Summary

Refines STG CI trigger conditions to avoid unnecessary GitHub Actions runs, and standardizes CI/CD environment naming for clearer workflow semantics. Tag pushes are excluded from `cicd.yml`, and deployment workflows are now scoped to runtime-related file changes.

### Changed

- **CI/CD environment naming (`.github/workflows/cicd.yml`, `.github/workflows/release.yml`)**: Standardizes environment names and job labels to improve consistency across STG and release workflows.
- **STG CI trigger scope (`.github/workflows/cicd.yml`)**: Keeps `main` branch-only behavior while explicitly excluding tag pushes from this workflow.
- **STG CI path filtering (`.github/workflows/cicd.yml`)**: Restricts workflow execution to deployment-relevant files (`portal/**`, `alembic/**`, `Dockerfile`, `entrypoint.sh`, `pyproject.toml`, `poetry.lock`, and the workflow file itself) so docs-only and other non-runtime changes do not trigger build/deploy.

### Breaking changes

None.

## [0.2.18] - 2026-04-13

### Summary

Introduces event-driven admin operation audit logging across admin write paths, standardizes `operation_code` to table names, and extends logging coverage to authentication, notification, and file operations. This release also refines CI Sentry release workflow behavior for commit handling.

### Added

- **Admin audit events**: Added `AdminOperationLogEvent` pipeline and background event handling to persist admin operation logs through the event bus.
- **Audit payload utilities**: Added normalized audit payload helpers and shallow changed-field computation for stable JSONB log data.
- **Admin handler coverage**: Added `create_log` calls for admin write flows in conference, event info, FAQ/category, feedback, instructor, location, notification, workshop, workshop registration, and auth handlers.
- **Auth/file operation logs**: Added admin login/logout audit logging and file upload/bulk delete audit logging.

### Changed

- **Operation type storage**: Changed `PortalLog.operation_type` to string-based enum values and removed integer mapping usage.
- **Operation code standard**: Switched `operation_code` usage to model table names (for example `PortalUser.__tablename__`) instead of hard-coded audit codes.
- **Request metadata source**: `ip_address` and `user_agent` for admin logs now come from request context middleware data.
- **Log handler API shape**: Unified DI argument naming to `log_handler` for admin handlers and expanded container wiring accordingly.
- **Admin log creation flow**: `AdminLogHandler.create_log` is now synchronous and safely suppresses internal failures while still publishing events in background.
- **CI/CD**: Updated Sentry release workflow behavior in GitHub Actions for commit/release handling improvements.

### Breaking changes

None.

## [0.2.17] - 2026-04-13

### Summary

Stops emitting **`logger.warning`** lines for transient asyncpg connection failures during **`Session.execute`**, **`Session.fetchvals`**, and the internal **`_fetch`** path in **`portal/libs/database/aio_orm.py`**. The previous messages keyed **`db_io_transient_retry`** and **`db_io_transient_exhausted`** are removed; **rollback**, **retry**, and **`_discard_broken_connection_unlocked`** behavior are unchanged.

### Removed

- **Database I/O (`portal/libs/database/aio_orm.py`)**: **`_log_db_transient_retry`** and **`_log_db_transient_exhausted`** helpers and all **`db_io_transient_*`** warning calls tied to **`_TRANSIENT_DB_IO_RETRIES`**.

### Breaking changes

None.

## [0.2.16] - 2026-04-13

### Summary

Merges the **0.2.15** ops and observability work into this release, and adds **GitHub Releases** tied to `CHANGELOG.md` (slice the `## [x.x.x]` section into the release body, then append GitHub auto-generated notes), **`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24`** for JS actions on the runner, and README guidance for the **`chore/release-x.x.x`** flow and admin-only tags. Core CI changes remain the same as described for `0.2.15` (commits `70c4cd4` … `9ffd661` relative to `0.2.14`).

### Added

- **Sentry**: Set `release=settings.APP_VERSION` in `sentry_sdk.init` so events map to the same version string as the app (`VERSION` → `APP_VERSION`).
- **Release CI**: On `*.*.*` tags, PATCH **STG** Render service to the same pushed semver image as PROD; add **`deploy-stg`** job to POST a Render deploy after image and env updates.
- **Release CI**: **`github-release`** job after STG deploy — `actions/checkout@v5`, build `release_body.md` from the matching **`CHANGELOG.md`** section with `awk`, then **`softprops/action-gh-release@v2`** with **`body_path`**, **`generate_release_notes: true`**, and **`make_latest: true`**.
- **Docs**: Root **`CHANGELOG.md`** (Keep a Changelog) and README **Versioned releases** (`CHANGELOG.md` + tags + GitHub Release behavior).

### Changed

- **STG CI (`cicd.yml`)**: After updating the STG service image, PUT env-group **`VERSION`** to the Docker metadata **`version`** output (primary registry tag; tags without a `v` prefix).
- **Release CI (`release.yml`)**: STG and PROD env-group **`VERSION`** now follow **`steps.meta.outputs.version`** instead of the raw tag ref name so the value matches the semver image tag from metadata; rename job to reflect PROD + STG image and env updates; workflow env **`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`**.
- **Docs (`README.md`)**: Document **`VERSION`** for `APP_VERSION`, Sentry `release`, CI behavior (STG image tag vs release semver + STG redeploy), and the **GitHub Release** + **CHANGELOG** flow.

### Breaking changes

None.
