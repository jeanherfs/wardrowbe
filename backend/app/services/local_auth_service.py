"""Local password hashing helpers."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class LocalAuthService:
    """Hash and verify local account passwords with Argon2id."""

    _hasher = PasswordHasher()

    @classmethod
    def hash_password(cls, password: str) -> str:
        return cls._hasher.hash(password)

    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        try:
            return cls._hasher.verify(password_hash, password)
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            return False
