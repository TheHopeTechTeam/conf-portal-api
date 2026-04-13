# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
