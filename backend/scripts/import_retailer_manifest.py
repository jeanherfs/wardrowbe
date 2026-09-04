#!/usr/bin/env python3
"""Import a local, browser-collected retailer manifest into Wardrowbe."""

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import async_session_maker
from app.models.user import User
from app.services.retailer_import_service import RetailerImportService


async def run(user_id: UUID, manifest_path: Path, image_root: Path) -> dict:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("manifest must be a JSON array of retailer items")

    async with async_session_maker() as session:
        user = await session.scalar(select(User.id).where(User.id == user_id))
        if user is None:
            raise ValueError(f"Wardrowbe user {user_id} was not found")
        summary = await RetailerImportService(session).apply(user_id, image_root, payload)
        return asdict(summary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True, type=UUID)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--image-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(run(args.user_id, args.manifest, args.image_root))))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
