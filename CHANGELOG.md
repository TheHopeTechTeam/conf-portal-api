# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.32] - 2026-05-02

### Summary

Removes max length constraint on testimony message field to allow longer testimonies.

### Changed

- Removed max length constraint on testimony message field.

## [0.2.31] - 2026-05-01

### Summary

Introduces Redis cache-aside optimization for non-admin conference/event/FAQ/workshop/notification handlers, and adds admin-write invalidation to keep user-facing cached data consistent after create/update/delete operations.

### Added

- **Non-admin cache key helpers** (`portal/libs/consts/cache_keys.py`):
  - Added helper functions for conference, event schedule, FAQ, workshop, and notification cache keys (including wildcard pattern helpers for scan-based invalidation).
- **Cache behavior tests** (`tests/handlers/test_non_admin_cache.py`):
  - Added focused tests for cache hit, cache fallback on Redis read failure, and workshop-related key invalidation behavior.

### Changed

- **User-facing read handlers now use cache-aside** (`portal/handlers/conference.py`, `portal/handlers/event_info.py`, `portal/handlers/faq.py`, `portal/handlers/workshop.py`, `portal/handlers/notification.py`):
  - Read flows now attempt Redis `GET` first, then fallback to DB queries on miss.
  - Successful query responses are serialized and written back to Redis with TTL.
  - Redis read/write errors are handled gracefully without breaking API response flow.
- **Admin write handlers now invalidate non-admin caches** (`portal/handlers/admin/conference.py`, `portal/handlers/admin/event_info.py`, `portal/handlers/admin/faq.py`, `portal/handlers/admin/workshop.py`, `portal/handlers/admin/workshop_registration.py`, `portal/handlers/admin/notification.py`):
  - Added targeted key deletion and pattern-based invalidation after create/update/delete/restore style operations.
  - Added admin-notification-triggered user notification list cache invalidation.
- **Dependency injection wiring** (`portal/container.py`):
  - Updated notification-related handler wiring to provide Redis dependencies required for cache operations and invalidation.
- **Admin registration serializer internals** (`portal/serializers/v1/admin/workshop_registration.py`):
  - Added internal `workshop_id` and `user_id` fields (excluded from response output) to support model-based invalidation logic.

### Breaking changes

None.

## [0.2.30] - 2026-05-01

### Summary

Adds configurable ARQ job result retention in Redis so completed job results remain available longer for inspection and debugging.

### Added

- **ARQ job result retention** (`portal/config.py`, `portal/workers/arq_worker.py`, `example.env`):
  - `ARQ_KEEP_RESULT_SECONDS` environment variable (default `86400`) mapped to `WorkerSettings.keep_result`.

### Breaking changes

None.

## [0.2.29] - 2026-04-30

### Summary

Improves push notification history consistency by committing PENDING rows before FCM, back-filling per-device results afterward, and exposing FCM multicast batch size via environment configuration. User-facing notification lists now only include successfully delivered items.

### Added

- **FCM batch size configuration** (`portal/config.py`, `example.env`):
  - `FCM_MAX_MULTICAST_TOKENS` environment variable (default `500`) replaces the hard-coded module constant.

### Changed

- **ARQ chunk notification job** (`portal/workers/arq_worker.py`):
  - Pre-insert `PortalNotificationHistory` rows with `PENDING` status and commit before calling FCM.
  - Use `ON CONFLICT DO NOTHING` on `(notification_id, device_id)` for idempotent retries.
  - After FCM, update existing rows to `SUCCESS` or `FAILED` instead of inserting new rows.
  - On `FirebaseError`, bulk-update chunk devices to `FAILED` rather than inserting duplicates.
  - On non-`FirebaseError` exceptions, rollback in-flight updates and fallback-mark remaining chunk `PENDING` rows as `FAILED` with exception details, then persist failure counters/status.
- **Event handler push batching** (`portal/handlers/events/notification.py`):
  - Uses `settings.FCM_MAX_MULTICAST_TOKENS` for multicast batch sizing.
- **User notification list** (`portal/handlers/notification.py`):
  - Filters to `NotificationHistoryStatus.SUCCESS` so PENDING/FAILED rows are not shown in the app.

### Breaking changes

None.

## [0.2.28] - 2026-04-30

### Summary

Fixes ARQ notification worker status persistence for chunked push delivery by replacing SQL `CASE`-based status assignments with explicit integer-safe update statements, preventing asyncpg datatype mismatch errors in production.

### Fixed

- **ARQ chunk status update type mismatch** (`portal/workers/arq_worker.py`):
  - Replaced `sa.case(...)` status writes that could be rendered as text expressions by the current DB session layer and fail against integer `status` columns.
  - Updated chunk success and error paths to use deterministic status updates:
    - set `SENT` when a chunk has any success,
    - set `FAILED` only when accumulated `success_count == 0`,
    - preserve already-sent notifications from being overwritten by later failed chunks.

### Breaking changes

None.

## [0.2.27] - 2026-04-30

### Summary

Improves ARQ notification worker reliability and observability by introducing chunk-based fan-out processing for large push sends, adding chunk-indexed execution logs, and refining aggregate status updates to avoid race-prone chunk-local status decisions. This release also adds a lightweight demo script to verify numeric increment update semantics in the project session/update DSL.

### Added

- **Demo numeric increment verification script** (`test_demo_age_increment.py`):
  - Added a standalone script that validates `age=Model.age + 1` style updates against the `Demo` model using a fixed demo UUID.
  - Script performs increment, verification read, rollback decrement, and final restore check for quick local validation.

### Changed

- **ARQ notification worker fan-out architecture** (`portal/workers/arq_worker.py`):
  - Refactored `send_notification_task` into a parent dispatch flow for push notifications that resolves targets once and enqueues child chunk jobs.
  - Added `send_notification_chunk_task` for per-chunk FCM send, per-device history writes, and incremental success/failure count updates.
  - Kept non-push and dry-run paths on the existing direct handler execution flow.
- **Chunk-level logging and traceability** (`portal/workers/arq_worker.py`):
  - Added structured lifecycle logs for parent/child jobs (start, target resolution, enqueue, send result, commit, finish, exception paths).
  - Added `chunk_index/total_chunks` propagation so worker logs clearly indicate batch position (for example `chunk=3/10`).
- **Aggregate status update semantics** (`portal/workers/arq_worker.py`):
  - Updated notification status writes to derive from accumulated success counts (`CASE` expression) instead of chunk-local success only, preventing later failed chunks from overriding previously successful overall delivery state.

### Breaking changes

None.

## [0.2.26] - 2026-04-30

### Summary

Introduces ARQ-based background processing for admin notification dispatch by moving notification send execution to a dedicated worker queue, while preserving existing notification delivery and history behavior. This release also extends Render CI/CD automation to deploy the staging worker service alongside API image updates and documents required worker deployment secrets.

### Added

- **ARQ worker runtime and queue utilities** (`portal/workers/arq_worker.py`, `portal/queues/arq_pool.py`, `portal/queues/__init__.py`, `portal/workers/__init__.py`, `worker.sh`):
  - Added ARQ worker entrypoint and `send_notification_task` execution flow.
  - Added ARQ Redis pool helper and notification enqueue helper.
  - Added worker startup wiring for container bootstrap and Firebase initialization.
- **Firebase initialization helper** (`portal/libs/firebase_init.py`): Added shared Firebase bootstrap helpers used by API and worker startup paths.

### Changed

- **Notification dispatch path** (`portal/handlers/admin/notification.py`, `portal/container.py`, `portal/libs/utils/lifespan.py`):
  - `create_notification` now enqueues ARQ jobs instead of publishing `NotificationCreatedEvent` through in-process background event bus.
  - Removed notification event-bus subscription from container registration (other event subscriptions unchanged).
  - Lifespan shutdown now closes ARQ pool resources.
- **Configuration and environment template** (`portal/config.py`, `example.env`, `pyproject.toml`):
  - Added ARQ-related settings (`ARQ_REDIS_URL`, `ARQ_REDIS_DB`, `ARQ_JOB_TIMEOUT`, `ARQ_MAX_TRIES`).
  - Added ARQ dependency and lock updates for worker runtime.
- **Render deployment workflows** (`.github/workflows/cicd.yml`, `.github/workflows/release.yml`):
  - Added staging worker image update + deploy jobs.
  - Added release-time worker service image update flow and staging worker deploy job.
  - Expanded STG workflow trigger paths to include `worker.sh`.
- **Worker observability** (`portal/workers/arq_worker.py`): Enhanced logging around worker-side notification task processing.
- **Deployment docs** (`README.md`): Documented Render worker deployment secrets and release/deploy behavior updates.

### Breaking changes

None.

## [0.2.25] - 2026-04-30

### Summary

Batches Firebase Cloud Messaging push delivery to respect multicast token limits, and excludes soft-deleted workshop registrations from admin paginated workshop registered counts so capacity metrics stay aligned with active rows.

### Changed

- **Push notification delivery (`portal/handlers/events/notification.py`)**:
  - Added `FCM_MAX_MULTICAST_TOKENS` (500) to match Firebase Admin multicast limits.
  - Sends push in token batches via `send_each_for_multicast`, aggregating success and failure counts and appending per-device notification history for each batch.
  - Refactored `_resolve_push_targets` to collect tokens and device IDs with explicit loops for clarity.

### Fixed

- **Admin workshop registered count (`portal/handlers/admin/workshop.py`)**: The paginated workshop list `registered_count` subquery now filters `PortalWorkshopRegistration.is_deleted == false` in addition to `unregistered_at IS NULL`, so withdrawn soft-deleted registrations no longer inflate counts.

### Breaking changes

None.

## [0.2.24] - 2026-04-30

### Summary

Refines workshop full-capacity evaluation to consistently count only active registrations (`unregistered_at IS NULL` and `is_deleted = false`) across workshop schedule, workshop detail, workshop full-check, and my-workshops query flows. This reduces false full-status results caused by withdrawn or soft-deleted registration rows.

### Changed

- **Workshop full-status query conditions (`portal/handlers/workshop.py`)**:
  - Updated `is_full` case expressions to include explicit active-registration constraints (`unregistered_at IS NULL`, `is_deleted = false`) alongside the participant-limit comparison.
  - Aligned workshop registration join/filter conditions in affected query flows so capacity counts and full-status flags use the same registration eligibility definition.

### Breaking changes

None.

## [0.2.23] - 2026-04-30

### Summary

Improves user notification query efficiency and result stability by deduplicating notification history at query time, and refines ticket workshop-registration coverage checks to exclude creative and leadership workshops. This release also adds a ticket handler test for workshop registration status flow.

### Changed

- **Notification history retrieval (`portal/handlers/notification.py`)**: Refactored `get_user_notification_list` to use a distinct notification subquery and stable ordering (`notification_id`, `created_at`, `id`) before projecting result rows, then applies final descending `created_at` ordering for API response output.
- **Ticket workshop-registration coverage scope (`portal/handlers/ticket.py`)**: Updated `_get_workshop_registration_status` workshop and registration queries to filter out `is_creative` and `is_leadership` workshops, so overlap checks only evaluate relevant standard workshops in active conferences.

### Added

- **Workshop registration status test (`tests/handlers/test_ticket.py`)**: Added async handler test for `_get_workshop_registration_status` using `TEST_USER_ID` fixture-style environment input, increasing regression coverage for ticket workshop status logic.

### Breaking changes

None.

## [0.2.22] - 2026-04-26

### Summary

Hardens workshop registration authorization and corrects workshop full-capacity evaluation by treating participant limits as inclusive. This release also makes handler user-context initialization explicitly optional while enforcing authorization before registration writes.

### Changed

- **Workshop handler user context typing (`portal/handlers/workshop.py`)**: Updated `self._user_ctx` to `Optional[UserContext]` during initialization to reflect context availability semantics.
- **Workshop full-status SQL logic (`portal/handlers/workshop.py`)**: Updated workshop `is_full` calculations from `count > participants_limit` to `count >= participants_limit` in workshop list/detail query flows to correctly mark full workshops at exact capacity.

### Fixed

- **Registration authorization guard (`portal/handlers/workshop.py`)**: Added an explicit `UnauthorizedException` check before registration creation when user context is missing, preventing unauthenticated registration writes.

### Breaking changes

None.

## [0.2.21] - 2026-04-25

### Summary

Improves Sentry observability for mounted admin routes, introduces deterministic ticket registration number generation for check-in and ticket/user payloads, and adds a lightweight admin workshop list API for selector/query use cases. This release adds middleware-side Sentry event normalization plus TicketHandler-based registration number derivation (from ticket UUID and active conference year), along with API serializer exposure, unit tests, a follow-up ticket scan logic fix, and `GET /admin/api/v1/workshop/list` support.

### Changed

- **Sentry request event processing (`portal/middlewares/core_request.py`)**: Added request-scoped event normalization for mounted admin routes, including URL/path corrections and richer ASGI scope metadata in event `extra`.
- **Sentry admin route tagging (`portal/main.py`)**: Added admin path tagging (`is_admin`) to improve event grouping and filtering for admin traffic.
- **Ticket check-in response assembly (`portal/handlers/ticket.py`)**: Refactored check-in payload building to use the current ticket object from earlier steps (including check-in update response docs) instead of re-fetching by id.
- **Ticket registration-year source (`portal/handlers/ticket.py`, `portal/handlers/conference.py`, `portal/container.py`)**: Registration year derivation is now obtained through injected `ConferenceHandler` active-conference flow, and ticket handler wiring was updated accordingly.
- **Environment/config cleanup (`example.env`, `portal/config.py`)**: Removed static registration-year env configuration in favor of active-conference date derivation.

### Added

- **Ticket registration number field (`portal/serializers/v1/ticket.py`)**: Added `registration_number` (`registrationNumber`) to `TicketBase` for API clients.
- **Deterministic registration number generation (`portal/handlers/ticket.py`)**:
  - Added private helper methods to generate a 12-digit registration number from `ticket_id` using SHA-256 derivation and active conference year prefix.
  - Added display formatting to `XXX-XXXXX-XXXX`.
- **Registration number tests (`tests/handlers/test_ticket_registration_number.py`)**: Added deterministic and format validation tests, including the README sample UUID case.
- **Admin workshop list API (`portal/routers/apis/v1/admin/workshop.py`, `portal/handlers/admin/workshop.py`, `portal/serializers/v1/admin/workshop.py`)**:
  - Added `GET /admin/api/v1/workshop/list` endpoint for lightweight workshop selector usage.
  - Added `AdminWorkshopList` response serializer with `items` collection based on `AdminWorkshopBase` (`id`, `title`).
  - Added handler query flow that returns non-deleted workshops ordered by `sequence` and `start_datetime`.

### Fixed

- **Ticket scan evaluation flow (`portal/handlers/ticket.py`)**: Changed loop control from `break` to `continue` while scanning TheHope ticket lists so non-primary/invalid entries do not prematurely stop evaluation of remaining tickets.
- **No redeemed pass diagnostics (`portal/handlers/ticket.py`)**: Raised log severity from `info` to `warning` when no redeemed primary pass is found after scanning ticket docs, improving operational visibility.

### Breaking changes

None.

## [0.2.20] - 2026-04-14

### Summary

Stabilizes admin audit logging by expanding `create_log` coverage across admin write handlers, aligning log metadata conventions, and fixing JSONB binding for operation log persistence. This release also adds supporting CI/release refinements and documentation updates.

### Added

- **Admin audit logging coverage**: Added `create_log` integration to additional admin write handlers, including conference, event info, FAQ/category, feedback, instructor, location, workshop, workshop registration, notification, auth, and file operations.
- **Admin operation log event type**: Added dedicated event payload type for admin operation logging and wired handler-based persistence flow.
- **Audit payload helpers**: Added utility helpers to normalize payloads and compute shallow changed fields for audit logs.

### Changed

- **Versioning/docs**: Added and updated release documentation and changelog content for current release flow.
- **Audit metadata**:
  - `operation_code` now follows model table names (`__tablename__`) consistently.
  - `operation_type` storage is string-based.
  - `create_log` uses request context for `ip_address` and `user_agent`.
  - Admin handler DI uses `log_handler` naming consistently.
- **Admin log dispatch path**: `AdminLogHandler.create_log` uses synchronous invocation for event publishing with failure-suppression behavior to avoid breaking callers.
- **CI/CD workflows**: Updated STG/release workflow conditions and Sentry release handling behavior.

### Fixed

- **JSONB parameter binding (`AdminOperationLogEventHandler`)**: Serialize `old_data`, `new_data`, and `changed_fields` before DB insert to prevent asyncpg type errors such as `expected str, got dict`.
- **Typing cleanup (`AdminAuthHandler.refresh_token`)**: Replaced deprecated inline type comment usage with proper type annotations and import alignment.

### Breaking changes

None.

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
