# Retailer Imports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add local, repeatable Zalando and Mango wardrobe imports, retained-item sizing data, and stable NFC/QR item entry links to Wardrowbe.

**Architecture:** Preserve Wardrowbe's upload pipeline and ownership checks. A backend service applies a local manifest and image directory, persisting retailer metadata and upserting kept items by source identity. A collector produces manifests from data already visible in an authenticated retailer browser, and a dashboard item route supplies a stable NFC/QR target.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, PostgreSQL, Pydantic, pytest, Next.js 14, TypeScript, TanStack Query, Docker Compose.

**Spec:** docs/superpowers/specs/2026-09-04-retailer-imports-design.md

## Global Constraints

- Do not store retailer credentials, browser cookies, addresses, payment data, or order records beyond item metadata.
- Accept only zalando and mango in v1.
- Mango returned and Zalando underwear/boxers/accessories never create or update wardrobe items.
- Copy product images through ImageService into Wardrowbe-managed storage.
- Default AI_INTERNAL_ENABLED=false; no AI provider is required.
- Every user-visible frontend string uses next-intl.

---

### Task 1: Persist retailer and fit metadata

**Files:**
- Modify: backend/app/models/item.py
- Modify: backend/app/schemas/item.py
- Create: backend/migrations/versions/<revision>_add_retailer_item_metadata.py
- Modify: backend/tests/test_items.py

**Interfaces:**
- Produces Retailer = zalando | mango, ReturnStatus = kept | returned, and FitRating = too_small | slightly_small | fits | slightly_large | too_large.
- Extends ClothingItem, ItemCreate, ItemUpdate, and ItemResponse with retailer, retailer_product_id, source_url, purchased_size, purchased_color, return_status, fit_rating, fit_notes, and imported_at.

- [ ] **Step 1: Write the failing metadata API test**

~~~python
async def test_update_item_persists_retailer_size_and_fit_metadata(client, auth_headers, item):
    response = await client.patch(
        f"/api/v1/items/{item.id}",
        headers=auth_headers,
        json={"retailer": "mango", "retailer_product_id": "17062902",
              "source_url": "https://shop.mango.com/nl/nl/p/heren/17062902",
              "purchased_size": "40", "purchased_color": "Kersenrood",
              "return_status": "kept", "fit_rating": "fits"},
    )
    assert response.status_code == 200
    assert response.json()["purchased_size"] == "40"
    assert response.json()["fit_rating"] == "fits"
~~~

- [ ] **Step 2: Verify RED**

Run: docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m pytest tests/test_items.py -k retailer_size_and_fit -v

Expected: FAIL because the schema rejects the fields.

- [ ] **Step 3: Implement model, schemas and migration**

Add enum-backed nullable columns. Add a PostgreSQL 15 partial unique index named uq_clothing_items_retailer_identity over user_id, retailer, retailer_product_id, purchased_size, and purchased_color when retailer and product ID are non-null, with NULLS NOT DISTINCT so a missing size or colour cannot bypass rerun protection.

- [ ] **Step 4: Verify GREEN**

Run: docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m pytest tests/test_items.py -k retailer_size_and_fit -v && docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend alembic upgrade head

Expected: PASS and Alembic reaches the new revision.

- [ ] **Step 5: Commit**

~~~bash
git add backend/app/models/item.py backend/app/schemas/item.py backend/migrations/versions backend/tests/test_items.py
git commit -m "feat: persist retailer item metadata"
~~~

### Task 2: Add idempotent manifest import service

**Files:**
- Create: backend/app/schemas/imports.py
- Create: backend/app/services/retailer_import_service.py
- Modify: backend/app/services/item_service.py
- Create: backend/tests/test_retailer_import_service.py

**Interfaces:**
- Consumes RetailerImportManifest(items, image_root).
- Produces ImportSummary(created, updated, skipped_returned, skipped_category, duplicate, failed, results).
- Produces RetailerImportService.apply(user_id, manifest) -> ImportSummary.

- [ ] **Step 1: Write failing service tests**

~~~python
async def test_mango_returned_manifest_item_is_skipped(service, user_id, manifest):
    manifest.items[0].retailer = "mango"
    manifest.items[0].return_status = "returned"
    summary = await service.apply(user_id, manifest)
    assert (summary.skipped_returned, summary.created) == (1, 0)

async def test_reapplying_retained_item_updates_without_duplicate(service, user_id, manifest):
    assert (await service.apply(user_id, manifest)).created == 1
    assert (await service.apply(user_id, manifest)).updated == 1

async def test_zalando_accessory_manifest_item_is_skipped(service, user_id, manifest):
    manifest.items[0].retailer, manifest.items[0].category = "zalando", "accessories"
    assert (await service.apply(user_id, manifest)).skipped_category == 1
~~~

- [ ] **Step 2: Verify RED**

Run: docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m pytest tests/test_retailer_import_service.py -v

Expected: FAIL because RetailerImportService does not exist.

- [ ] **Step 3: Implement manifest parsing and upsert**

Validate image paths against image_root and reject escapes. Skip returned and excluded records before ImageService.process_and_store. Look up the source identity and create or update metadata. Record an item-level failure and continue; delete a newly stored image if database persistence fails.

- [ ] **Step 4: Verify GREEN and commit**

Run: docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m pytest tests/test_retailer_import_service.py -v

Expected: PASS.

~~~bash
git add backend/app/schemas/imports.py backend/app/services/retailer_import_service.py backend/app/services/item_service.py backend/tests/test_retailer_import_service.py
git commit -m "feat: add idempotent retailer import service"
~~~

### Task 3: Add local command and collector contract

**Files:**
- Create: backend/scripts/import_retailer_manifest.py
- Create: tools/retailer-collector/README.md
- Create: tools/retailer-collector/manifest.schema.json
- Create: backend/tests/test_import_retailer_manifest.py

**Interfaces:**
- Consumes python scripts/import_retailer_manifest.py --user-id <uuid> --manifest <path> --image-root <path>.
- Produces JSON ImportSummary and a non-zero exit only for invalid manifests or a missing user.

- [ ] **Step 1: Write failing command test**

~~~python
def test_import_command_rejects_manifest_image_outside_root(tmp_path):
    completed = run_import_command(tmp_path, image_path="../outside.jpg")
    assert completed.returncode == 2
    assert "outside image root" in completed.stderr
~~~

- [ ] **Step 2: Verify RED**

Run: docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m pytest tests/test_import_retailer_manifest.py -v

Expected: FAIL because the command is absent.

- [ ] **Step 3: Implement command and document collector**

Validate with RetailerImportManifest.model_validate_json, resolve the Wardrowbe user, call the import service and print the result. Document browser-visible collection for both retailers, Mango return mapping and Zalando category exclusion. Do not add a headless crawler or credential configuration.

- [ ] **Step 4: Verify GREEN and commit**

Run: docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m pytest tests/test_import_retailer_manifest.py -v

Expected: PASS.

~~~bash
git add backend/scripts/import_retailer_manifest.py backend/tests/test_import_retailer_manifest.py tools/retailer-collector
git commit -m "feat: add local retailer manifest import command"
~~~

### Task 4: Add stable authenticated NFC item route

**Files:**
- Create: frontend/app/dashboard/items/[id]/page.tsx
- Modify: frontend/components/item-detail-dialog.tsx
- Modify: frontend/lib/types.ts
- Modify: frontend/messages/en/wardrobe.json
- Create: frontend/tests/item-route.test.tsx

**Interfaces:**
- Consumes /dashboard/items/<UUID> and useItem(id).
- Produces an authenticated detail page with editable source and fit metadata.

- [ ] **Step 1: Write failing route test**

~~~tsx
it('loads the requested item into the authenticated detail page', async () => {
  render(<ItemDetailPage params={{ id: 'item-1' }} />);
  expect(await screen.findByText('Blue Oxford Shirt')).toBeInTheDocument();
});
~~~

- [ ] **Step 2: Verify RED**

Run: cd frontend && npm test -- item-route.test.tsx

Expected: FAIL because the route does not exist.

- [ ] **Step 3: Implement route, metadata types and translations**

Reuse the dashboard layout authentication. Add loading/not-found translation keys, types and source/fit edit controls. Imported fields remain editable for corrections.

- [ ] **Step 4: Verify GREEN and commit**

Run: cd frontend && npm test -- item-route.test.tsx && npm run i18n:check && npm run typecheck

Expected: PASS.

~~~bash
git add frontend/app/dashboard/items frontend/components/item-detail-dialog.tsx frontend/lib/types.ts frontend/messages/en/wardrobe.json frontend/tests/item-route.test.tsx
git commit -m "feat: add stable item detail route"
~~~

### Task 5: Configure deployment and verify end to end

**Files:**
- Modify: .env.example
- Modify: README.md
- Create: docs/deployment/retailer-imports.md
- Create: backend/tests/test_deployment_defaults.py

- [ ] **Step 1: Write failing default configuration test**

~~~python
def test_example_environment_disables_internal_ai_by_default():
    assert dotenv_values(ROOT / ".env.example")["AI_INTERNAL_ENABLED"] == "false"
~~~

- [ ] **Step 2: Verify RED**

Run: docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m pytest tests/test_deployment_defaults.py -v

Expected: FAIL because the example default is absent or true.

- [ ] **Step 3: Implement deployment defaults and migration guide**

Set the example default, document untracked .env secrets and portable PostgreSQL/image-volume backup and restore steps without printing secrets.

- [ ] **Step 4: Verify complete stack and commit**

Run: docker compose -f docker-compose.yml -f docker-compose.dev.yml config -q && docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m pytest tests/ -v --tb=short && cd frontend && npm test && npm run typecheck && npm run i18n:check

Expected: PASS.

~~~bash
git add .env.example README.md docs/deployment backend/tests/test_deployment_defaults.py
git commit -m "docs: configure private retailer import deployment"
~~~
