from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retailer_import_service import RetailerImportService


@pytest.mark.asyncio
async def test_mango_returned_manifest_item_is_skipped(
    db_session: AsyncSession, test_user, tmp_path: Path
):
    service = RetailerImportService(db_session)
    summary = await service.apply(
        user_id=test_user.id,
        image_root=tmp_path,
        items=[
            {
                "retailer": "mango",
                "retailer_product_id": "17062902",
                "return_status": "returned",
                "image_path": "returned.jpg",
            }
        ],
    )

    assert summary.skipped_returned == 1
    assert summary.created == 0


@pytest.mark.asyncio
async def test_zalando_accessories_are_skipped(db_session: AsyncSession, test_user, tmp_path: Path):
    service = RetailerImportService(db_session)
    summary = await service.apply(
        user_id=test_user.id,
        image_root=tmp_path,
        items=[
            {
                "retailer": "zalando",
                "retailer_product_id": "BI754K00M-O11",
                "category": "accessories",
                "image_path": "sunglasses.jpg",
            }
        ],
    )

    assert summary.skipped_category == 1
    assert summary.created == 0


@pytest.mark.asyncio
async def test_reapplying_retained_item_updates_without_duplicate(
    db_session: AsyncSession, test_user, tmp_path: Path
):
    image_path = tmp_path / "shorts.jpg"
    Image.new("RGB", (10, 10), color="red").save(image_path)
    service = RetailerImportService(db_session)
    user_id = test_user.id
    item = {
        "retailer": "mango",
        "retailer_product_id": "17062902",
        "name": "Bermuda",
        "purchased_size": "40",
        "purchased_color": "Kersenrood",
        "image_path": image_path.name,
    }

    first = await service.apply(user_id, tmp_path, [item])
    second = await service.apply(user_id, tmp_path, [item])

    assert first.created == 1
    assert second.updated == 1
