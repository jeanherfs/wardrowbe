from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import ClothingItem
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


@pytest.mark.asyncio
async def test_empty_size_and_color_match_missing_retailer_metadata(
    db_session: AsyncSession, test_user, tmp_path: Path
):
    image_path = tmp_path / "shirt.jpg"
    Image.new("RGB", (10, 10), color="blue").save(image_path)
    service = RetailerImportService(db_session)
    base = {
        "retailer": "zalando",
        "retailer_product_id": "shirt-1",
        "image_path": image_path.name,
    }

    first = await service.apply(test_user.id, tmp_path, [base])
    second = await service.apply(
        test_user.id,
        tmp_path,
        [{**base, "purchased_size": "", "purchased_color": ""}],
    )

    assert first.created == 1
    assert second.updated == 1


@pytest.mark.asyncio
async def test_existing_import_update_commits_purchase_metadata(
    db_session: AsyncSession, test_user, tmp_path: Path
):
    image_path = tmp_path / "coat.jpg"
    Image.new("RGB", (10, 10), color="black").save(image_path)
    service = RetailerImportService(db_session)
    user_id = test_user.id
    base = {
        "retailer": "mango",
        "retailer_product_id": "coat-1",
        "image_path": image_path.name,
        "name": "Coat",
        "purchased_size": "M",
        "purchased_color": "Black",
    }

    await service.apply(user_id, tmp_path, [base | {"purchase_date": "2025-01-02"}])
    await service.apply(
        user_id,
        tmp_path,
        [
            base
            | {
                "purchase_date": "2025-02-03",
                "purchase_price": 129.95,
            }
        ],
    )
    await db_session.rollback()

    item = await db_session.scalar(
        select(ClothingItem).where(
            ClothingItem.user_id == user_id,
            ClothingItem.retailer_product_id == "coat-1",
        )
    )
    assert item is not None
    assert item.purchase_date == date(2025, 2, 3)
    assert item.purchase_price == Decimal("129.95")
