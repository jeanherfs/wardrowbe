# Local Release and Retailer Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run this fork as a portable release stack on port 8080, authenticate one local account with a temporary password, and import the user's Zalando and Mango wardrobe data into that release database.

**Architecture:** Add a nullable Argon2 password hash and a release-only local credentials flow that reuses Wardrowbe's existing JWT/NextAuth session shape. Add a separate release Compose file and launcher subcommands that build from source, use isolated named volumes, bootstrap the account, and create portable backup/restore artifacts. Keep browser collection local and credential-free; feed read-only manifests and images into the existing idempotent importer.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, PostgreSQL, Next.js/NextAuth, Argon2 via `argon2-cffi`, Docker Compose, Bash, pytest, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-06-local-release-and-retailer-bootstrap-design.md`

## Global Constraints

- Release UI binds to `http://localhost:8080`; development remains on port 3000.
- Passwords are Argon2id hashes only; plaintext temporary passwords are emitted once and never persisted.
- OIDC and passwordless development login remain available as separate modes.
- Retailer sessions, cookies, addresses, payment data and credentials never enter Wardrowbe storage.
- Imports skip Mango `returned` lines and Zalando underwear/boxers/accessories.
- Release data is stored in named volumes and can be exported/restored without source-tree paths.
- All implementation changes use test-first cycles and are committed in focused increments.

### Task 1: Add local password credentials to the backend

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/schemas/user.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/services/user_service.py`
- Create: `backend/app/services/local_auth_service.py`
- Create: `backend/migrations/versions/f1a2b3c4d5e6_add_local_password_hash.py`
- Test: `backend/tests/test_local_auth.py`

**Interfaces:**
- `LocalAuthService.hash_password(password: str) -> str` and `verify_password(password: str, password_hash: str) -> bool` use Argon2id.
- `POST /api/v1/auth/local-login` accepts `{email, password}` only when `LOCAL_AUTH_ENABLED=true` and returns `{id, email, display_name, external_id, access_token}`.
- `POST /api/v1/auth/bootstrap` accepts `{email, display_name, password, external_id?}` only when local auth is enabled and the caller supplies the launcher bootstrap secret; it creates an account if absent and refuses an existing account unless `reset_password=true`.
- `Settings.get_auth_mode()` returns `local`, `oidc`, `dev`, or `unknown` with local taking precedence only when explicitly enabled.

- [ ] Write tests for Argon2 verification, disabled local auth, invalid credentials returning the same 401 response, successful login returning a usable JWT, bootstrap idempotency, and explicit reset refusal.
- [ ] Run `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend pytest tests/test_local_auth.py -q` and verify the new tests fail because the model/service/endpoints do not exist.
- [ ] Add the dependency, nullable `password_hash`, settings flags, service, schemas, endpoints, and Alembic migration.
- [ ] Run the focused tests, then `tests/test_auth.py tests/test_users.py`, and verify all pass.
- [ ] Commit `feat: add local password authentication`.

### Task 2: Connect local credentials to the release frontend

**Files:**
- Modify: `frontend/lib/auth.ts`
- Modify: `frontend/app/login/page.tsx`
- Modify: `frontend/messages/en/auth.json`
- Test: `frontend/tests/auth-local.test.ts`

**Interfaces:**
- NextAuth provider `local-credentials` calls `${BACKEND_URL}/api/v1/auth/local-login` and maps the returned access token into the existing JWT callback.
- Provider selection exposes local login only when `LOCAL_AUTH_ENABLED=true`; OIDC and dev provider selection is unchanged.

- [ ] Write Vitest tests for provider selection and local credential success/failure.
- [ ] Run the focused Vitest file and verify it fails because the provider/form strings are absent.
- [ ] Implement the provider, login form fields, loading/error states, and English translations with existing next-intl conventions.
- [ ] Run the focused Vitest file and the frontend i18n check.
- [ ] Commit `feat: add local credentials login`.

### Task 3: Add the release Compose topology

**Files:**
- Create: `docker-compose.release.yml`
- Create: `.env.release.example`
- Modify: `.gitignore`
- Modify: `frontend/Dockerfile` if required for fork-local build compatibility
- Modify: `backend/Dockerfile` if required for `argon2-cffi`
- Test: `tests/release-compose.test.sh`

**Interfaces:**
- Compose project name is `wardrobe-release`.
- `frontend` is reachable only through `127.0.0.1:8080`; backend, database and Redis have no host ports.
- Services build from `backend/Dockerfile` and `frontend/Dockerfile`, use release-specific named volumes, and receive `LOCAL_AUTH_ENABLED=true`, `DEBUG=false`, `AI_INTERNAL_ENABLED=false`, generated secrets, and `NEXTAUTH_URL=http://localhost:8080`.

- [ ] Write shell tests that inspect rendered Compose config for release project/port, distinct volume names, no development bind mounts, and required environment switches.
- [ ] Run the shell test and verify it fails because the release compose file does not exist.
- [ ] Add the release file and ignored secret template with secure placeholder validation.
- [ ] Run the shell test, `docker compose -f docker-compose.release.yml config`, and a local image build.
- [ ] Commit `feat: add portable release compose stack`.

### Task 4: Extend `./wardrobe` for release lifecycle and account bootstrap

**Files:**
- Modify: `wardrobe`
- Create: `backend/scripts/bootstrap_local_user.py`
- Modify: `README.md`
- Test: `tests/wardrobe-release.test.sh`

**Interfaces:**
- `./wardrobe release help` documents `up`, `down`, `status`, `logs`, `migrate`, `bootstrap`, `import`, `backup`, and `restore`.
- `./wardrobe release up --email mail@jeanherfs.nl` generates `.env.release` with mode 600, builds/starts the release stack, migrates, bootstraps the account if missing, and waits for `http://localhost:8080` and `/api/v1/health`.
- `./wardrobe release bootstrap --email ...` prints a generated temporary password once; `--reset-password` is required to rotate an existing account.
- `./wardrobe release import --user-id ... --manifest ... --image-root ...` mounts both inputs read-only and invokes the existing importer in the release backend.

- [ ] Write shell tests for no-argument help, release Compose selection, generated `.env.release` permissions, bootstrap argument validation, and read-only import mounts.
- [ ] Run the shell test with a fake Docker executable and verify it fails on missing release commands.
- [ ] Add the bootstrap script, release command dispatcher, secret generation, health waits, and release README instructions.
- [ ] Run shell tests and exercise `./wardrobe release help` and `./wardrobe release status` against the local Docker daemon.
- [ ] Commit `feat: add release lifecycle commands`.

### Task 5: Add portable backup and restore

**Files:**
- Modify: `wardrobe`
- Create: `backend/scripts/backup_release.py` only if a Python helper is needed for database metadata
- Modify: `README.md`
- Test: `tests/release-backup.test.sh`

**Interfaces:**
- `./wardrobe release backup DIRECTORY` creates `wardrowbe.dump`, `uploads.tar`, and a redacted `release.env.example` without secrets.
- `./wardrobe release restore DIRECTORY` refuses a non-empty release database unless `--force-empty-target` is explicit, restores the dump and uploads archive, and reruns migrations.

- [ ] Write tests for missing backup files, refusal of non-empty restore targets, and redaction of secret values.
- [ ] Run the focused test and verify it fails because backup/restore commands are absent.
- [ ] Implement PostgreSQL `pg_dump`/`pg_restore` and Docker-volume archive operations with explicit directory validation.
- [ ] Run backup/restore tests and a disposable round-trip with a fixture item.
- [ ] Commit `feat: add release backup and restore`.

### Task 6: Collect authenticated retailer data into release staging

**Files:**
- Modify: `tools/retailer-collector/README.md`
- Modify: `tools/retailer-collector/manifest.schema.json` if fields need tightening
- Create: `tools/retailer-collector/collect_zalando.mjs`
- Create: `tools/retailer-collector/collect_mango.mjs`
- Test: `tools/retailer-collector/tests/collector-fixtures.test.mjs`

**Interfaces:**
- Collector functions accept a browser tab adapter and a local staging directory; they return manifest rows and downloaded image paths without accessing cookies or storage.
- Zalando collector scrolls until item-card count stabilizes and emits title, brand, size, URL, product ID, category, and image URL.
- Mango collector emits per-purchase product details, size, colour, REF, date, URL, return status, and image URL; returned lines remain in the manifest with `return_status: returned` so the importer can report them as skipped.

- [ ] Add fixture tests for lazy-loaded Zalando cards, Mango returned labels, duplicate cards, and skipped category classification.
- [ ] Run the fixture tests and verify they fail because collector modules do not exist.
- [ ] Implement the collectors using browser-visible DOM evaluation and bounded scrolling; download only product images into staging.
- [ ] Run fixture tests and validate generated manifests against the JSON schema.
- [ ] Commit `feat: add browser-visible retailer collectors`.

### Task 7: Release integration and real authenticated import

**Files:**
- Modify: `backend/tests/test_retailer_import_service.py` only for release-specific fixtures if needed
- Modify: `README.md`
- Test: `tests/release-integration.test.sh`

- [ ] Start the release stack and run migrations with `./wardrobe release up --email mail@jeanherfs.nl`.
- [ ] Sign in through the release UI at `http://localhost:8080` using the one-time password and verify an authenticated dashboard session.
- [ ] Use the authenticated browser tabs to collect Zalando and Mango staging data; review counts and excluded categories/returns before importing.
- [ ] Run `./wardrobe release import` with the release user ID and staging paths, then repeat it to confirm idempotency.
- [ ] Verify imported size/colour/source metadata through the release API/UI and confirm no returned or excluded rows exist.
- [ ] Run the full backend and frontend test suites, release health checks, and backup/restore round-trip.
- [ ] Commit `test: verify release retailer bootstrap` and push the branch.
