# Item ratings and style profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add half-star fit/style ratings to clothing items and use them to produce explainable AI-assisted style preferences.

**Architecture:** Store two nullable item-level scores in PostgreSQL and expose them through the existing item PATCH API. Extend the existing learning service/profile with direct item-rating aggregates, then expose a reusable half-star picker in the item detail UI and item-rating metrics/actions on the learning page.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy/Alembic, PostgreSQL, pytest, Next.js/React, TanStack Query, Vitest, local Ollama-compatible AI configuration.

**Spec:** `docs/superpowers/specs/2026-09-06-item-ratings-style-profile-design.md`

## Global Constraints

- Ratings are nullable numeric values from 1.0 through 5.0 in 0.5 increments.
- Keep the existing qualitative `fit_rating` field unchanged for compatibility.
- No new rating endpoint; use `PATCH /api/v1/items/{id}`.
- Do not invent measurements or fit claims; insights must include supporting counts/confidence.
- Preserve release backup portability and run migrations through the existing release startup flow.
- Every production change follows a failing-test-first cycle.

### Task 1: Add item score columns and validation

**Files:**
- Create: `backend/migrations/versions/f8a9b0c1d2e3_add_item_rating_scores.py`
- Modify: `backend/app/models/item.py`
- Modify: `backend/app/schemas/item.py`
- Test: `backend/tests/test_item_ratings.py`

**Interfaces:**
- Produces `ClothingItem.fit_score` and `ClothingItem.style_score` as nullable `Numeric(2, 1)` values.
- `ItemCreate`, `ItemUpdate`, and `ItemResponse` expose `fit_score: Decimal | None` and `style_score: Decimal | None`.
- Shared validation accepts `1.0, 1.5, …, 5.0` and rejects values outside the range or not divisible by 0.5.

- [x] **Step 1: Write failing schema tests** for all accepted half-star values and rejection of `0`, `5.25`, `-1`, and `3.2`.
- [x] **Step 2: Run** `set -a; source .env.release; set +a; docker compose --env-file .env.release -f docker-compose.release.yml run --rm --no-deps -e TEST_DATABASE_URL="postgresql+asyncpg://wardrobe:${POSTGRES_PASSWORD}@postgres:5432/wardrobe_test" -v "$PWD/backend:/app" backend python -m pytest tests/test_item_ratings.py -q`; verify validation/model failures.
- [x] **Step 3: Add the additive Alembic migration, SQLAlchemy columns, and a reusable Pydantic half-star validator wired into item create/update/response schemas.**
- [x] **Step 4: Run the focused tests and migration-head check; verify they pass.**
- [x] **Step 5: Commit** `feat: add item fit and style scores`.

### Task 2: Persist ratings through the item API

**Files:**
- Modify: `backend/app/services/item_service.py`
- Modify: `backend/app/api/items.py` to keep the PATCH response contract covered by the updated schemas
- Test: `backend/tests/test_items.py`

**Interfaces:**
- `PATCH /api/v1/items/{item_id}` accepts JSON such as `{"fit_score": 4.5, "style_score": 3.0}` and returns both values.
- Existing optimistic item update behaviour remains unchanged.

- [x] **Step 1: Add a failing authenticated API test in `backend/tests/test_items.py`** that patches both scores, reloads the item, and asserts the response and database values are `4.5` and `3.0`.
- [x] **Step 2: Run the focused API test and verify it fails because the model/schema fields are not yet wired through the update path.**
- [x] **Step 3: Wire the fields through service update/create handling and response serialization without changing unrelated item fields.**
- [x] **Step 4: Run the focused API test plus existing item API tests; verify they pass.**
- [x] **Step 5: Commit** `feat: persist item rating scores through api`.

### Task 3: Include item ratings in the learning profile

**Files:**
- Create: `backend/migrations/versions/b7c8d9e0f1a2_add_item_rating_learning_metrics.py`
- Modify: `backend/app/models/learning.py`
- Modify: `backend/app/services/learning_service.py`
- Modify: `backend/app/api/learning.py`
- Modify: `frontend/lib/hooks/use-learning.ts`
- Test: `backend/tests/test_learning_service.py`

**Interfaces:**
- `UserLearningProfile` gains `items_rated`, `average_item_fit`, and `average_item_style` persisted in the existing profile row.
- `POST /learning/recompute` computes direct item aggregates and preserves existing outfit metrics.
- `GET /learning` returns `items_rated`, `average_item_fit`, and `average_item_style`.

- [x] **Step 1: Add failing learning tests** with rated and unrated items; assert unrated items are ignored, scores normalize with `(score - 3) / 2`, and colour/type/brand/style aggregates include the rated item signal.
- [x] **Step 2: Run the focused tests and verify failures for missing fields/aggregation.**
- [x] **Step 3: Add the migration/model counters and extend recomputation with direct-item accumulators, a minimum supporting count of three for item-specific claims, and confidence based on sample count.**
- [x] **Step 4: Extend learning response schemas and frontend types, then run focused learning/API tests.**
- [x] **Step 5: Commit** `feat: learn preferences from item ratings`.

### Task 4: Add the half-star rating control and item UI

**Files:**
- Create: `frontend/components/half-star-picker.tsx`
- Modify: `frontend/components/item-detail-dialog.tsx`
- Modify: `frontend/app/dashboard/wardrobe/page.tsx`
- Modify: `frontend/lib/types.ts`
- Test: `frontend/tests/half-star-picker.test.tsx`

**Interfaces:**
- `HalfStarPicker` props: `value: number | null`, `onChange: (value: number) => void`, `label: string`, optional `readOnly?: boolean`.
- Values are 1.0–5.0 in 0.5 increments, with click/tap and keyboard support and an accessible radiogroup label.

- [x] **Step 1: Write failing component tests** for empty state, half/full rendering, click selection, ArrowLeft/ArrowRight keyboard changes, and accessible label/value.
- [x] **Step 2: Run** the focused Vitest file and verify it fails because the picker does not exist.
- [x] **Step 3: Implement the picker with Lucide stars, half-fill styling, keyboard semantics, and no network side effects.**
- [x] **Step 4: Add Fit and Style controls to the item detail dialog using `useUpdateItem`; add compact read-only indicators to item cards; update `Item` types.**
- [x] **Step 5: Run the focused frontend tests and relevant wardrobe/component tests; verify they pass.**
- [x] **Step 6: Commit** `feat: add item fit and style rating controls`.

### Task 5: Expose style-profile refresh and explainable insights

**Files:**
- Modify: `frontend/app/dashboard/learning/page.tsx`
- Modify: `frontend/lib/hooks/use-learning.ts`
- Modify: `backend/app/services/learning_service.py` for deterministic insight generation and optional local-AI prose
- Test: `frontend/tests/learning-page.test.tsx`
- Test: `backend/tests/test_learning_service.py`

**Interfaces:**
- Learning page shows item-rating counts/averages and a `Recompute style profile` action that calls the existing mutation.
- Generated insights include `supporting_data` with sample count/confidence and never state unsupported measurements or fit claims.

- [x] **Step 1: Add failing backend/frontend tests** for the refresh action and a style insight supported by at least three rated items.
- [x] **Step 2: Run focused tests and verify failures.**
- [x] **Step 3: Implement the metrics display, refresh action, and explainable deterministic insight formatting from supplied rating facts.**
- [x] **Step 4: Run focused tests and existing learning-page tests; verify they pass.**
- [x] **Step 5: Commit** `feat: surface explainable style profile`.

### Task 6: Release verification and documentation

**Files:**
- Modify: `README.md`
- Test: `tests/release-compose.test.sh`, `tests/wardrobe-release.test.sh`, and the backend migration-head check

- [x] **Step 1: Run the backend focused suites, frontend focused suites, migration-head check, and release compose config check.**
- [x] **Step 2: Rebuild and restart with `./wardrobe release up`; verify `./wardrobe release doctor`.**
- [x] **Step 3: Use the UI to set one fit and one style half-star rating, recompute the profile, and verify the values survive a release restart.**
- [x] **Step 4: Run `./wardrobe release backup /tmp/wardrowbe-release-2026-09-06-ratings` and verify the portable backup contains the updated database dump.**
- [x] **Step 5: Commit** `docs: document item ratings and style profile` and push the branch.
