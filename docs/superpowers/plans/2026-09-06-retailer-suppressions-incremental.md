# Retailer suppression and incremental import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent deliberately removed retailer items from returning and make normal Zalando/Mango imports resume from the last successful crawl boundary.

**Architecture:** Store deletion tombstones separately from clothing items, keyed by the same retailer/product/size/colour identity used by imports. Store one durable cursor per user and retailer, and make each collector emit cursor metadata and stop at a known overlap; the import transaction advances the cursor only after all eligible rows are accepted. Full imports remain available for recovery.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, PostgreSQL, Pydantic, Node retailer collectors, Docker wrapper.

**Spec:** Approved in conversation on 2026-09-06; this plan captures the approved design.

## Global Constraints

- Suppressions apply only to retailer-linked deletions; manually created items are unaffected.
- Archive does not create a suppression; archived rows remain identifiable.
- Suppression keys use normalized retailer/product/size/colour values and SQL NULL semantics.
- Cursor state advances only after a complete successful manifest import; failed or partial runs leave the previous cursor intact.
- Incremental collection uses a bounded overlap with the previous boundary and remains idempotent.
- Returned purchases and existing accessory/underwear exclusions remain unchanged.
- Full-crawl mode remains available and can explicitly reconcile old history.
- All new behavior requires a failing test before production code.

---

### Task 1: Persist retailer suppression tombstones

**Files:**
- Create: `backend/app/models/retailer.py`
- Create: `backend/migrations/versions/a1b2c3d4e5f7_add_retailer_suppressions.py`
- Create: `backend/app/schemas/retailer.py`
- Modify: `backend/app/models/__init__.py` if model registration requires it
- Test: `backend/tests/test_retailer_suppressions.py`

**Interfaces:**
- `RetailerItemSuppression(user_id, retailer, retailer_product_id, purchased_size, purchased_color, reason, created_at)`.
- `RetailerSuppressionService.suppress(item, reason="removed")` and `is_suppressed(user_id, retailer, product_id, size, color)`.
- A unique index uses `(user_id, retailer, retailer_product_id, purchased_size, purchased_color)` with `NULLS NOT DISTINCT`.

- [ ] **Step 1: Write failing tests** for creating a tombstone, normalized empty size/colour, duplicate suppression idempotency, and no suppression for non-retailer items.
- [ ] **Step 2: Run** `docker compose ... exec -T backend pytest tests/test_retailer_suppressions.py -q`; confirm missing model/service failures.
- [ ] **Step 3: Add the model, JSON-safe schema, service, migration, and model import registration.**
- [ ] **Step 4: Run the focused tests and migration-head check; confirm pass.**
- [ ] **Step 5: Commit** `feat: persist retailer deletion suppressions`.

### Task 2: Record suppressions during single and bulk deletion

**Files:**
- Modify: `backend/app/api/items.py:447-500,1184-1210`
- Modify: `backend/app/services/item_service.py`
- Test: `backend/tests/test_retailer_suppressions.py`

**Interfaces:**
- `DELETE /api/v1/items/{item_id}` accepts optional `suppress_reimport=true|false`, defaulting to true for retailer-linked items.
- Bulk deletion accepts the same explicit flag in `BulkDeleteRequest`; default is true.
- A new authenticated `POST /api/v1/retailer/suppressions/{suppression_id}/clear` operation removes one tombstone so a deliberate re-import is possible.

- [ ] **Step 1: Add failing API tests** for default suppression on retailer deletion, opt-out deletion, bulk behavior, and clear/restore.
- [ ] **Step 2: Run** the focused API tests and confirm they fail before wiring.
- [ ] **Step 3: Insert the suppression before deleting the row and before deleting image files; keep transaction rollback-safe.**
- [ ] **Step 4: Implement the authenticated clear endpoint and ownership checks.**
- [ ] **Step 5: Run focused plus existing item-delete tests; commit** `feat: suppress deleted retailer items`.

### Task 3: Filter suppressed identities in retailer imports

**Files:**
- Modify: `backend/app/services/retailer_import_service.py`
- Create: `backend/app/services/retailer_cursor_service.py`
- Test: `backend/tests/test_retailer_import_service.py`

**Interfaces:**
- `RetailerImportService.apply(..., run_id: str | None = None, cursor: dict | None = None)` checks suppression before image work and increments `skipped_suppressed`.
- `ImportSummary` adds `skipped_suppressed` and `cursor_advanced`.
- `RetailerCursorService.get(user_id, retailer)` and `advance_after_success(user_id, retailer, cursor, run_id)` are transactional and idempotent.

- [ ] **Step 1: Write failing tests** for suppression filtering before image processing, summary counts, overlap idempotency, and cursor non-advancement when any row fails.
- [ ] **Step 2: Run focused importer tests and confirm failures.**
- [ ] **Step 3: Add suppression lookup and cursor state persistence; normalize empty identity fields exactly as existing imports do.**
- [ ] **Step 4: Advance cursor only after the manifest loop completes without failures; preserve the old state on rollback.**
- [ ] **Step 5: Run importer and idempotency tests; commit** `feat: filter suppressed retailer imports`.

### Task 4: Add incremental cursor contracts to collectors

**Files:**
- Modify: `tools/retailer-collector/collect_all.mjs`
- Modify: `tools/retailer-collector/collect_zalando.mjs`
- Modify: `tools/retailer-collector/collect_mango.mjs`
- Modify: `tools/retailer-collector/manifest.schema.json`
- Test: `tools/retailer-collector/tests/collector-fixtures.test.mjs`

**Interfaces:**
- `collectUntilSettled(readCards, scroll, { stopAt, cursor, ... })` stops after observing the configured overlap identity while retaining newly seen cards.
- `collectZalandoOrders(rows, { sinceCursor, stopAtIdentity })` returns `{ items, cursor }` where the cursor includes the newest order date/id and overlap identity.
- `collectMangoPurchases(purchases, { sinceCursor, stopAtIdentity })` returns the same shape, preferring purchase date/order id and falling back to identity overlap.
- Manifest envelope accepts `items`, `retailer`, `cursor`, `run_id`, and `complete`; legacy bare arrays remain accepted for full imports.

- [ ] **Step 1: Write failing Node tests** for stopping at an overlap, preserving newer cards, cursor emission, and legacy full-array compatibility.
- [ ] **Step 2: Run** `node --test tools/retailer-collector/tests/collector-fixtures.test.mjs`; confirm failures.
- [ ] **Step 3: Implement cursor-aware collection with a bounded overlap and explicit `complete` signal.**
- [ ] **Step 4: Update schema/docs and run all collector tests; commit** `feat: support incremental retailer cursors`.

### Task 5: Add incremental import/backfill operator commands

**Files:**
- Modify: `backend/scripts/import_retailer_manifest.py`
- Modify: `wardrobe`
- Modify: `tools/retailer-collector/README.md`
- Modify: `README.md`
- Test: `backend/tests/test_retailer_incremental_cli.py`

**Interfaces:**
- `python scripts/import_retailer_manifest.py --user-id ID --manifest FILE --image-root DIR` accepts both legacy arrays and the cursor envelope.
- `./wardrobe release import-incremental --user-id ID --manifest FILE --image-root DIR` requires `complete=true` and uses the stored retailer cursor.
- `./wardrobe release import-full ...` explicitly ignores the cursor for reconciliation.
- `./wardrobe release retailer-state --user-id ID` prints last successful cursors and run status without credentials.

- [ ] **Step 1: Add failing CLI tests** for envelope parsing, rejecting incomplete incremental runs, and full-import override.
- [ ] **Step 2: Implement command routing and script arguments; preserve the existing `release import` command as a compatibility alias.**
- [ ] **Step 3: Add collector instructions for saving the cursor/run ID and retrying failed runs without advancing state.**
- [ ] **Step 4: Run shell help, CLI tests, and Node tests; commit** `feat: add incremental retailer import commands`.

### Task 6: Verify current release and portability

**Files:**
- Runtime only: release database and named upload volume
- Backup: `/tmp/wardrowbe-release-2026-09-06-retailer-state/`

- [ ] **Step 1: Apply migrations and verify release health.**
- [ ] **Step 2: Query current active Zalando/Mango counts and confirm no existing rows are suppressed.**
- [ ] **Step 3: Run a dry-run or fixture incremental import and verify the cursor advances only on `complete=true`.**
- [ ] **Step 4: Create a suppression for one disposable test item, rerun its manifest, verify it is skipped, then clear the suppression.**
- [ ] **Step 5: Run** `./wardrobe release backup /tmp/wardrowbe-release-2026-09-06-retailer-state/` **and verify dump/uploads files.**
- [ ] **Step 6: Commit any code-only fixes and report runtime verification.**

## Verification checklist

- [ ] Suppressed retailer deletions never reappear in repeated imports.
- [ ] Manual items and archives are unaffected.
- [ ] Incremental runs stop at the saved overlap and include only newer eligible rows.
- [ ] Failed/partial runs do not advance the cursor.
- [ ] Full imports remain usable for reconciliation.
- [ ] Node collector tests pass.
- [ ] Backend suppression/import/API tests pass.
- [ ] Release health and portable backup are verified.
