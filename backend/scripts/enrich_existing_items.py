"""Queue local vision enrichment for active wardrobe items."""
import argparse
import asyncio
import sys
from uuid import UUID
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arq import create_pool
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_maker
from app.models.item import ClothingItem
from app.workers.settings import get_redis_settings
from app.services.item_enrichment_service import deterministic_metadata


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True, type=UUID)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    settings = get_settings()
    queued = 0
    async with async_session_maker() as db:
        query = select(ClothingItem).where(ClothingItem.user_id == args.user_id, ClothingItem.is_archived.is_(False)).order_by(ClothingItem.created_at)
        if args.limit:
            query = query.limit(args.limit)
        items = list((await db.execute(query)).scalars().all())
        redis = await create_pool(get_redis_settings())
        try:
            for item in items:
                if not item.image_path:
                    continue
                deterministic = deterministic_metadata(item.name, item.brand, item.type)
                if item.type == "unknown" and deterministic.get("type"):
                    item.type = deterministic["type"]
                if item.ai_job_id and not item.ai_processed:
                    continue
                job = await redis.enqueue_job("tag_item_image", str(item.id), f"{settings.storage_path}/{item.image_path}", _queue_name="arq:tagging")
                item.ai_job_id = job.job_id
                queued += 1
            await db.commit()
        finally:
            await redis.aclose()
    print(f"queued={queued} active={len(items)}")


if __name__ == "__main__":
    asyncio.run(main())
