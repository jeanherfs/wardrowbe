# Item ratings and AI style profile

## Goal

Let a user rate each clothing item independently on two dimensions—fit and style—using a 1–5 star scale in 0.5-star increments. Feed those item-level signals into Wardrowbe's existing learning system so it can produce an explainable profile of preferred colours, item types, brands, styles, and recurring dislikes.

## Scope and decisions

- Add `fit_score` and `style_score` to `clothing_items`, both nullable numeric values constrained to 1.0–5.0 in 0.5 increments.
- Keep the existing qualitative `fit_rating` field for backward compatibility and existing API consumers. New UI writes `fit_score`; it does not silently infer a numeric score from the old enum.
- Ratings are upserts on the item, not an append-only history. `updated_at` provides the latest-change timestamp; a future history feature can add an audit table without changing this API.
- The rating control is available in the item detail dialog and is keyboard accessible. Wardrobe cards show compact fit/style indicators only when a score exists.
- Style analysis remains user-triggered through the existing learning recompute/generate-insights actions. It combines item scores with outfit feedback, accepted/rejected suggestions, wear counts, favourites, colours, types, brands, and style tags.
- The result is explainable and local-first: deterministic aggregates produce preference scores, while the configured local AI may turn those aggregates into prose. No cloud API is required.

## Data model and migration

Add nullable `Numeric(2, 1)` columns `fit_score` and `style_score` to `clothing_items`. Add Pydantic fields with a shared validator that accepts only half-star values in the inclusive range 1.0–5.0. Return both fields from `ItemResponse` and accept them in `ItemCreate`/`ItemUpdate`.

The migration is additive and reversible. Existing rows remain unrated and existing `fit_rating` values remain unchanged.

## API

The existing `PATCH /api/v1/items/{id}` endpoint accepts `fit_score` and `style_score` and returns the updated item. Validation errors use the same 422 response as other item fields. No new rating endpoint is needed for the first version; the frontend mutation remains idempotent and benefits from the existing optimistic update path.

The existing learning endpoints continue to be used:

- `POST /api/v1/learning/recompute` incorporates item scores into learned colour/style/type/brand aggregates and profile averages.
- `POST /api/v1/learning/generate-insights` creates human-readable insights from the refreshed profile.
- `GET /api/v1/learning` exposes item-rating counts/averages and the explainable preference lists.

Extend the learning response with `items_rated`, `average_item_fit`, and `average_item_style`, without removing existing outfit metrics.

## Learning behaviour

For each rated item, normalize a score to `-1..1` using `(score - 3) / 2`. Aggregate by primary colour, type, brand, style tag, and formality. Use the mean with a small-sample confidence factor so one rating is visible but not presented as certain. Merge these signals with existing outfit-feedback aggregates, weighting direct item ratings more heavily for item attributes and outfit feedback more heavily for combinations/occasions.

Generate insights such as “Your best-fitting items are mostly size M shirts” only when at least three rated items support the claim, and always include the count and confidence in `supporting_data`. Never invent garment measurements or claim that a size fits without user ratings or retailer-provided data.

## UI

Create a reusable half-star picker with click/tap and keyboard controls, an accessible label, and a visible numeric value. Render two labelled controls (“Fit” and “Style”) in the item detail dialog, with save-on-change through `useUpdateItem`. Display read-only compact values on item cards when present. Add item-rating metrics and a “Recompute style profile” action to the learning page; retain the existing insight acknowledgement flow.

## Testing

- Backend schema tests reject 0, 5.25, negative, and non-half-star values and accept 1.0–5.0 half-star values.
- Backend API tests verify authenticated item updates persist both scores and return them.
- Learning-service tests verify item scores contribute to colour/type/brand/style aggregates, confidence reflects sample count, and unrated items do not affect results.
- Frontend tests cover half-star selection, keyboard interaction, optimistic update payloads, and rendering empty/half/full ratings.
- Run migration-head checks, focused backend/frontend tests, then the relevant full suites and a release health check.

## Rollout and portability

The migration runs with the existing release startup flow. Scores and computed profiles live in PostgreSQL and are included automatically in the existing `wardrobe release backup` dump, so moving the release stack to the homeserver preserves them.
