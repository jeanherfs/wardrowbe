from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Retailer, ReturnStatus
from app.schemas.item import ItemCreate, ItemUpdate
from app.services.image_service import ImageService
from app.services.item_service import ItemService


EXCLUDED_ZALANDO_CATEGORIES = {"accessories", "accessory", "underwear", "boxers", "boxershorts"}


class RetailerImportItem(BaseModel):
    retailer: Retailer
    retailer_product_id: str = Field(min_length=1, max_length=100)
    image_path: str
    category: str | None = None
    name: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    source_url: HttpUrl | None = None
    purchased_size: str | None = Field(default=None, max_length=50)
    purchased_color: str | None = Field(default=None, max_length=100)
    return_status: ReturnStatus = ReturnStatus.kept
    purchase_date: date | None = None


@dataclass
class ImportSummary:
    created: int = 0
    updated: int = 0
    skipped_returned: int = 0
    skipped_category: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class RetailerImportService:
    def __init__(self, db: AsyncSession, image_service: ImageService | None = None):
        self.db = db
        self.items = ItemService(db)
        self.image_service = image_service or ImageService()

    async def apply(
        self,
        user_id: UUID,
        image_root: Path,
        items: list[dict],
    ) -> ImportSummary:
        summary = ImportSummary()
        root = image_root.resolve()
        for raw_item in items:
            item = RetailerImportItem.model_validate(raw_item)
            if item.return_status == ReturnStatus.returned:
                summary.skipped_returned += 1
                continue
            if item.retailer == Retailer.zalando and (item.category or "").lower() in EXCLUDED_ZALANDO_CATEGORIES:
                summary.skipped_category += 1
                continue

            try:
                image_file = (root / item.image_path).resolve()
                image_file.relative_to(root)
                if not image_file.is_file():
                    raise ValueError("image file does not exist")

                existing = await self.items.find_by_retailer_identity(
                    user_id,
                    item.retailer.value,
                    item.retailer_product_id,
                    item.purchased_size,
                    item.purchased_color,
                )
                data = ItemCreate(
                    type="unknown",
                    name=item.name,
                    brand=item.brand,
                    retailer=item.retailer,
                    retailer_product_id=item.retailer_product_id,
                    source_url=str(item.source_url) if item.source_url else None,
                    purchased_size=item.purchased_size,
                    purchased_color=item.purchased_color,
                    return_status=item.return_status,
                    purchase_date=item.purchase_date,
                )
                if existing:
                    await self.items.update(
                        existing,
                        ItemUpdate(
                            name=item.name,
                            brand=item.brand,
                            retailer=item.retailer,
                            retailer_product_id=item.retailer_product_id,
                            source_url=str(item.source_url) if item.source_url else None,
                            purchased_size=item.purchased_size,
                            purchased_color=item.purchased_color,
                            return_status=item.return_status,
                            purchase_date=item.purchase_date,
                        ),
                    )
                    summary.updated += 1
                    continue

                paths = await self.image_service.process_and_store(
                    user_id, image_file.read_bytes(), image_file.name
                )
                created = await self.items.create(user_id, data, paths)
                created.imported_at = datetime.now(UTC)
                await self.items.mark_pending(created, set_ready=True)
                await self.db.commit()
                summary.created += 1
            except Exception as error:
                await self.db.rollback()
                summary.failed += 1
                summary.errors.append(f"{item.retailer_product_id}: {error}")
        return summary
