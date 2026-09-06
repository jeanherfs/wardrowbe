#!/usr/bin/env python3
"""Create or explicitly reset a release-local Wardrowbe account."""

import argparse
import asyncio
import json
import secrets
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_maker
from app.models.user import User
from app.services.local_auth_service import LocalAuthService


async def bootstrap(email: str, display_name: str, password: str | None, reset_password: bool) -> dict:
    settings = get_settings()
    if not settings.local_auth_enabled:
        raise ValueError("LOCAL_AUTH_ENABLED must be true to bootstrap a local account")

    normalized_email = email.lower().strip()
    generated_password = password is None
    effective_password = password or secrets.token_urlsafe(18)
    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.email == normalized_email))
        if user is not None and not reset_password:
            raise ValueError("user already exists; pass --reset-password to rotate its password")

        if user is None:
            user = User(
                external_id=f"local-{uuid4()}",
                email=normalized_email,
                display_name=display_name,
                password_hash=LocalAuthService.hash_password(effective_password),
            )
            session.add(user)
        else:
            user.display_name = display_name
            user.password_hash = LocalAuthService.hash_password(effective_password)
        await session.commit()
        await session.refresh(user)

    result = {"id": str(user.id), "email": user.email, "display_name": user.display_name}
    if generated_password:
        result["temporary_password"] = effective_password
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--password")
    parser.add_argument("--reset-password", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(bootstrap(args.email, args.display_name, args.password, args.reset_password))))
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
