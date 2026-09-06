# Local Ollama enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich every imported wardrobe item locally with reliable metadata and automatically normalize its catalog image, while preserving manual values and portability.

**Architecture:** Extend the existing OpenAI-compatible `AIService` to target host Ollama, add a validated measurements JSONB field, and merge structured vision results through a dedicated enrichment service. Retailer imports invoke deterministic mapping, local image normalization, and a queued enrichment job; a backfill CLI applies the same pipeline to existing items.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, Pydantic, ARQ worker, Pillow/rembg, Ollama OpenAI-compatible API, Node retailer collector tests.

**Spec:** `docs/superpowers/specs/2026-09-06-local-enrichment-design.md`

## Global Constraints

- Never overwrite manual/non-AI fields during enrichment.
- Never invent garment measurements; missing values remain null with provenance.
- Keep imports idempotent and normalize empty retailer strings to SQL null.
- Ollama failure must not fail the retailer import; leave enrichment pending.
- Image cleanup is local and deterministic; preserve the original image backup.
- Returned purchases and excluded accessories/underwear remain skipped.
- All new behavior requires a failing test before production code.

---

### Task 1: Add validated measurements to the item model

**Files:**
- Create: `backend/migrations/versions/<new_revision>_add_item_measurements.py`
- Modify: `backend/app/models/item.py`
- Modify: `backend/app/schemas/item.py`
- Test: `backend/tests/test_item_measurements.py`

**Interfaces:**
- Produces `ClothingItem.measurements: dict | None` and `ItemResponse.measurements`.
- Measurement entries use `{value: number|null, source: string, confidence: number}` with the approved measurement-key allowlist.

- [ ] **Step 1: Write the failing schema/model test** asserting valid measurement records round-trip and unknown keys or negative values are rejected.
- [ ] **Step 2: Run** `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_item_measurements.py -q` and confirm the missing-field failure.
- [ ] **Step 3: Add the Alembic JSONB column and Pydantic validation/model response field.**
- [ ] **Step 4: Run the focused test and existing item schema tests; confirm pass.**
- [ ] **Step 5: Commit** with `feat: add item measurement metadata`.

### Task 2: Implement deterministic metadata enrichment and merge precedence

**Files:**
- Create: `backend/app/services/item_enrichment_service.py`
- Create: `backend/app/schemas/enrichment.py`
- Modify: `backend/app/prompts/clothing_analysis.txt`
- Test: `backend/tests/test_item_enrichment_service.py`

**Interfaces:**
- `ItemEnrichmentService.merge_missing(item, candidate, source)` updates only missing fields and returns changed field names.
- `parse_enrichment_payload(payload)` validates the strict type/colour/pattern/material/formality/style/season/fit vocabulary and measurements provenance.
- `deterministic_metadata(name, brand, category)` supplies safe type mappings for unambiguous retailer titles.

- [ ] **Step 1: Write failing tests** for manual-field precedence, deterministic title mapping, malformed JSON rejection, and null measurements when no explicit dimensions exist.
- [ ] **Step 2: Run** `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_item_enrichment_service.py -q` and confirm expected failures.
- [ ] **Step 3: Implement the validator, deterministic mapper, merge service, and prompt additions.**
- [ ] **Step 4: Run focused and existing AI parsing tests; confirm pass without network calls.**
- [ ] **Step 5: Commit** with `feat: add local metadata enrichment service`.

### Task 3: Add Ollama endpoint defaults and structured vision parsing

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/services/ai_service.py`
- Modify: `backend/app/workers/tagging.py`
- Test: `backend/tests/test_ai_service_ollama.py`

**Interfaces:**
- Default release configuration targets `http://host.docker.internal:11434/v1` and configurable `AI_VISION_MODEL`/`AI_TEXT_MODEL`.
- Vision responses are parsed through the enrichment schema; endpoint errors return a pending/error result without failing imports.

- [ ] **Step 1: Write failing tests** for Ollama URL/model defaults, image request payload compatibility, strict JSON parsing, and unavailable-endpoint fallback.
- [ ] **Step 2: Run** `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_ai_service_ollama.py -q` and confirm failures.
- [ ] **Step 3: Implement configuration and parsing changes using the existing endpoint fallback abstraction.**
- [ ] **Step 4: Run focused AI tests and the full backend unit suite; confirm pass.**
- [ ] **Step 5: Commit** with `feat: support Ollama vision enrichment`.

### Task 4: Make catalog-image normalization the default import step

**Files:**
- Create: `backend/app/services/catalog_image_service.py`
- Modify: `backend/app/services/image_service.py`
- Modify: `backend/app/services/retailer_import_service.py`
- Test: `backend/tests/test_catalog_image_service.py`
- Modify: `backend/tests/test_retailer_import_service.py`

**Interfaces:**
- `CatalogImageService.normalize(image_data, filename)` returns processed bytes plus an original backup marker.
- Normalization removes background/people with the configured local provider, centers the foreground item on a square light background, and preserves source bytes for recovery.

- [ ] **Step 1: Write failing tests** for center/pad output, provider invocation, original preservation, and import failure fallback.
- [ ] **Step 2: Run** `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_catalog_image_service.py tests/test_retailer_import_service.py -q` and confirm failures.
- [ ] **Step 3: Implement normalization and invoke it before `ImageService.process_and_store` for every retailer import.**
- [ ] **Step 4: Run focused tests and verify existing uploads still pass.**
- [ ] **Step 5: Commit** with `feat: normalize catalog images during import`.

### Task 5: Queue enrichment after imports and add a backfill command

**Files:**
- Modify: `backend/app/services/retailer_import_service.py`
- Modify: `backend/app/workers/tagging.py`
- Create: `backend/scripts/enrich_existing_items.py`
- Modify: `backend/app/workers/worker.py`
- Test: `backend/tests/test_retailer_import_enrichment.py`

**Interfaces:**
- Successful imports enqueue one enrichment job per created/updated item without blocking the import result.
- `python scripts/enrich_existing_items.py --user-id <uuid> [--limit N]` queues or processes pending active items idempotently.

- [ ] **Step 1: Write failing tests** for enqueue behavior, merge-only-missing semantics, Ollama failure isolation, and backfill filtering of archived items.
- [ ] **Step 2: Run** the focused worker/import tests and confirm failures.
- [ ] **Step 3: Implement job enqueueing, retry/error recording, and the backfill CLI.**
- [ ] **Step 4: Run focused tests plus worker tests; confirm pass.**
- [ ] **Step 5: Commit** with `feat: queue local enrichment and backfill existing items`.

### Task 6: Wire release Docker configuration and operator documentation

**Files:**
- Modify: `docker-compose.release.yml`
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `tools/retailer-collector/README.md`
- Modify: `wardrobe`
- Test: `backend/tests/test_config_defaults.py`

**Interfaces:**
- Release services receive Ollama URL/model settings and resolve the host gateway on Docker Desktop/Linux-compatible environments.
- `./wardrobe doctor` reports whether Ollama is reachable and the configured vision model exists; imports remain usable when it is not.

- [ ] **Step 1: Write failing config/doctor tests** for safe defaults and clear unavailable-model diagnostics.
- [ ] **Step 2: Run the focused tests and confirm failures.**
- [ ] **Step 3: Add environment wiring, host-gateway configuration, setup instructions (`ollama pull qwen3-vl:8b`), and doctor diagnostics.**
- [ ] **Step 4: Run config tests and shell help/doctor checks; confirm pass.**
- [ ] **Step 5: Commit** with `docs: document local Ollama setup`.

### Task 7: Backfill current release data and verify portability

**Files:**
- Runtime data only: release database and named upload volume
- Backup artifact: `/tmp/wardrowbe-release-2026-09-06-enriched/`

- [ ] **Step 1: Rebuild and restart release services with the Ollama configuration.**
- [ ] **Step 2: Run the backfill command for the active user and record created/updated/pending counts.**
- [ ] **Step 3: Verify active Zalando/Mango counts, metadata coverage, image variants, and health endpoint.**
- [ ] **Step 4: Run `./wardrobe release backup /tmp/wardrowbe-release-2026-09-06-enriched/` and verify database/upload archives exist.**
- [ ] **Step 5: Commit any final code-only fixes and report runtime results.**

## Verification checklist

- [ ] Node retailer collector tests pass.
- [ ] Backend importer, enrichment, image, worker, and schema tests pass.
- [ ] `./wardrobe release up` completes successfully.
- [ ] `curl -fsS http://localhost:8080/api/v1/health` reports healthy.
- [ ] A repeated manifest import creates zero duplicates.
- [ ] Manual metadata remains unchanged after enrichment.
- [ ] Backup contains both database and upload archives.
