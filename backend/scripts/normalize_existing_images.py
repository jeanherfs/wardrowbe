"""Normalize catalog images already stored in a wardrobe."""
import argparse
import asyncio
import sys
from io import BytesIO
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_maker
from app.models.item import ClothingItem
from app.services.catalog_image_service import CatalogImageService
from app.services.image_service import ImageService


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True, type=UUID)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    settings = get_settings()
    images = ImageService()
    normalizer = CatalogImageService()
    updated = 0
    async with async_session_maker() as db:
        query = select(ClothingItem).where(ClothingItem.user_id == args.user_id, ClothingItem.is_archived.is_(False)).order_by(ClothingItem.created_at)
        if args.limit:
            query = query.limit(args.limit)
        items = list((await db.execute(query)).scalars().all())
        for item in items:
            full = images.get_image_path(item.image_path)
            if not full.exists():
                continue
            normalized, original = normalizer.normalize(full.read_bytes(), full.name)
            if not item.original_image_path:
                backup = full.with_name(full.stem + "_source" + full.suffix)
                backup.write_bytes(original)
                item.original_image_path = str(backup.relative_to(images.storage_path))
            processed = Image.open(BytesIO(normalized)).convert("RGB")
            paths = images._save_all_sizes(processed, item.image_path)
            item.medium_path = paths["medium_path"]
            item.thumbnail_path = paths["thumbnail_path"]
            updated += 1
        await db.commit()
    print(f"normalized={updated} active={len(items)}")


if __name__ == "__main__":
    asyncio.run(main())
