"""Safe merge of deterministic and local-AI garment metadata."""
from typing import Any
from app.models.item import ClothingItem
from app.schemas.enrichment import EnrichmentPayload, parse_enrichment_payload

def deterministic_metadata(name: str | None, brand: str | None = None, category: str | None = None) -> dict[str, Any]:
    text = " ".join(x for x in (name, category) if x).lower()
    mappings = ((("sneaker", "trainer"), "sneakers"), (("boot",), "boots"), (("sandal",), "sandals"), (("jeans", "denim"), "jeans"), (("trouser", "pants"), "pants"), (("shorts",), "shorts"), (("dress",), "dress"), (("skirt",), "skirt"), (("jacket",), "jacket"), (("coat",), "coat"), (("blazer",), "blazer"), (("hoodie",), "hoodie"), (("sweater", "pullover", "jumper"), "sweater"), (("blouse",), "blouse"), (("shirt",), "shirt"), (("t-shirt", "tee"), "t-shirt"))
    result: dict[str, Any] = {}
    for needles, value in mappings:
        if any(n in text for n in needles):
            result["type"] = value
            break
    if brand:
        result["brand"] = brand
    return result

class ItemEnrichmentService:
    def merge_missing(self, item: ClothingItem, candidate: EnrichmentPayload | dict, source: str = "ollama") -> list[str]:
        payload = candidate if isinstance(candidate, EnrichmentPayload) else parse_enrichment_payload(candidate)
        values = payload.model_dump(exclude_none=True)
        changed: list[str] = []
        for field in ("type", "subtype", "primary_color", "colors", "pattern", "material", "style", "formality", "season", "brand"):
            value = values.get(field)
            if value is None:
                continue
            current = getattr(item, field, None)
            if current is None or current == "" or current == [] or current == {} or (field == "type" and current == "unknown"):
                setattr(item, field, value)
                changed.append(field)
        if payload.description and not item.ai_description:
            item.ai_description = payload.description
            changed.append("ai_description")
        if payload.measurements:
            current = item.measurements or {}
            merged = dict(current)
            for key, record in payload.measurements.items():
                if record is not None and not merged.get(key):
                    merged[key] = record.model_dump()
            if merged != current:
                item.measurements = merged
                changed.append("measurements")
        item.ai_processed = True
        item.ai_confidence = payload.confidence
        item.ai_raw_response = {"provider": source, "payload": payload.model_dump(mode="json")}
        return changed
