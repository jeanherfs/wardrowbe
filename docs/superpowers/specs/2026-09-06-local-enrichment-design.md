# Local metadata enrichment and catalog-image normalization

## Goal

Every retailer import should produce a useful, searchable clothing record: retailer metadata is preserved, missing classification fields are filled by deterministic rules or a local Ollama vision model, and catalog images are normalized automatically. Existing imported records receive the same enrichment without overwriting manual corrections.

## Context

The current Wardrowbe item model already stores retailer identity, purchased size, return status, AI tags, confidence, and image variants. The retailer pages provide brand, product name, product URL, and size, but their order cards do not reliably expose clothing type, material, fit, or physical garment measurements. The existing AI service speaks an OpenAI-compatible API and the background-removal worker uses local `rembg`.

## Decisions

1. Use Ollama as the default local vision endpoint for metadata enrichment. The release stack reaches host Ollama through `host.docker.internal:11434/v1`; no cloud credential is required.
2. Recommend `qwen3-vl:8b` as the default vision model on the current M3 Pro/36 GB machine. Model name remains configurable.
3. Use strict JSON output for AI fields. Invalid, unknown, or low-confidence values remain null/pending for review; the model must never invent garment measurements.
4. Keep image editing local and deterministic: remove people/backgrounds with `rembg`, center the foreground item on a square light background, and regenerate image variants. Ollama analyzes images but is not used as an image editor.
5. Preserve user-entered values. Enrichment only fills missing fields unless an explicit re-enrich action opts into replacing AI-generated values.
6. Keep provenance and confidence in the existing `ai_raw_response`/`ai_confidence` fields and add a structured measurements object for dimension values and their source.

## Data model

Add nullable `measurements` JSONB to `clothing_items`. Its schema is:

```json
{
  "chest_cm": {"value": 52.0, "source": "retailer", "confidence": 0.98},
  "waist_cm": {"value": null, "source": "unknown", "confidence": 0.0},
  "inseam_cm": {"value": 78.0, "source": "retailer", "confidence": 0.95},
  "garment_length_cm": {"value": null, "source": "unknown", "confidence": 0.0}
}
```

Supported keys are `chest_cm`, `waist_cm`, `hip_cm`, `inseam_cm`, `outseam_cm`, `rise_cm`, `shoulder_cm`, `sleeve_cm`, `garment_length_cm`, `foot_length_cm`, and `shoe_width_cm`. A measurement is only populated when a retailer page or user measurement explicitly supplies it. Visual estimation is not accepted.

## Enrichment flow

1. Normalize and store the imported image; the normalization step is enabled for all retailer imports and preserves the original source path as a backup.
2. Map retailer fields and deterministic title/category rules.
3. Queue an enrichment job after import. The job sends the image plus retailer text to Ollama using the existing `AIService` endpoint abstraction and a JSON schema matching the allowed Wardrowbe vocabularies.
4. Merge only missing item fields. Manual fields and existing non-AI values win. Save the raw response, confidence, and source markers.
5. Mark unresolved fields for review instead of fabricating values. Fit analysis uses purchased size plus later fit ratings and notes.

## Configuration and portability

Add release defaults for `AI_BASE_URL`, `AI_VISION_MODEL`, `AI_TEXT_MODEL`, and Ollama host access. `ollama pull qwen3-vl:8b` is an explicit setup step; the application must report a clear health error if the model is unavailable. The database migration and named upload volume remain portable through the existing `./wardrobe release backup` and `restore` commands.

## Safety and failure handling

- Ollama unavailable: imports still succeed with retailer and deterministic fields; enrichment remains pending.
- Malformed model JSON: record an error and keep the item usable; do not partially apply invalid fields.
- Image normalization failure: retain the original uploaded image and report the item-level error.
- Repeated imports are idempotent on retailer identity with empty strings normalized to null.
- Returned purchases and excluded accessories/underwear remain skipped.

## Acceptance criteria

- A fresh Zalando/Mango import automatically centers and cleans its catalog image.
- Existing records can be backfilled with one command and no manual per-item instruction.
- Brand, size, colour, purchase metadata, and deterministic types are present whenever supplied by the retailer.
- Ollama fills allowed type/subtype/visual fields as strict JSON and never invents dimensions.
- Measurements are stored with provenance and are queryable for future fit analysis.
- Manual fields survive enrichment and repeated imports do not create duplicates.
- Local tests cover merge precedence, JSON validation, measurement provenance, image-normalization invocation, and Ollama-unavailable fallback.
