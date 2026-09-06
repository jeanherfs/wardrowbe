"""Strict, provider-neutral schema for local garment enrichment."""
from typing import Any, Literal
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.item import MEASUREMENT_KEYS, MeasurementRecord

TypeValue = Literal["unknown", "shirt", "t-shirt", "top", "pants", "jeans", "shorts", "dress", "jumpsuit", "skirt", "jacket", "coat", "sweater", "hoodie", "blazer", "vest", "cardigan", "polo", "blouse", "tank-top", "shoes", "sneakers", "boots", "sandals", "socks", "tie", "hat", "scarf", "belt", "bag", "accessories"]
ColorValue = Literal["black", "white", "gray", "navy", "blue", "light-blue", "red", "burgundy", "pink", "green", "olive", "yellow", "orange", "purple", "brown", "tan", "beige", "cream", "gold", "silver"]

class EnrichmentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: TypeValue = "unknown"
    subtype: str | None = Field(default=None, max_length=50)
    primary_color: ColorValue | None = None
    colors: list[ColorValue] = Field(default_factory=list)
    pattern: str | None = None
    material: str | None = None
    style: list[str] = Field(default_factory=list)
    formality: str | None = None
    season: list[str] = Field(default_factory=list)
    fit: str | None = None
    brand: str | None = Field(default=None, max_length=100)
    description: str | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    measurements: dict[str, MeasurementRecord | None] | None = None

    @field_validator("measurements")
    @classmethod
    def validate_measurements(cls, value):
        if value is not None:
            unknown = set(value) - MEASUREMENT_KEYS
            if unknown:
                raise ValueError(f"Unknown measurement keys: {sorted(unknown)}")
        return value

def parse_enrichment_payload(payload: Any) -> EnrichmentPayload:
    if isinstance(payload, str):
        payload = json.loads(payload)
    return EnrichmentPayload.model_validate(payload)
