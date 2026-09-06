from uuid import UUID

from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str  # Subject (external_id from OIDC)
    exp: int  # Expiration timestamp
    iat: int | None = None  # Issued at timestamp (optional for forward auth tokens)
    email: str | None = None
    name: str | None = None


class AuthSession(BaseModel):
    user_id: UUID
    external_id: str
    email: str
    display_name: str
    family_id: UUID | None = None
    role: str
    is_authenticated: bool = True


class LocalLoginRequest(BaseModel):
    email: str
    password: str


class LocalBootstrapRequest(BaseModel):
    email: str
    display_name: str
    password: str
    external_id: str | None = None
    reset_password: bool = False


class LocalAuthResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    external_id: str
    access_token: str
