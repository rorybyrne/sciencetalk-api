"""JWT token utilities."""

from datetime import datetime, timedelta

import jwt
from pydantic import BaseModel

from talk.config import AuthSettings


class TokenPayload(BaseModel):
    """JWT token payload."""

    user_id: str
    did: str
    handle: str
    exp: datetime


class JWTError(Exception):
    """JWT-related error."""

    pass


def create_token(user_id: str, did: str, handle: str, settings: AuthSettings) -> str:
    """Create a JWT token for the user.

    Args:
        user_id: User ID
        did: Bluesky DID
        handle: Bluesky handle
        settings: Authentication settings

    Returns:
        Encoded JWT token
    """
    expiry = datetime.now() + timedelta(days=settings.jwt_expiry_days)

    payload = {
        "user_id": user_id,
        "did": did,
        "handle": handle,
        "exp": expiry,
    }

    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return token


def verify_token(token: str, settings: AuthSettings) -> TokenPayload:
    """Verify and decode a JWT token.

    Args:
        token: JWT token to verify
        settings: Authentication settings

    Returns:
        Token payload if valid

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise JWTError("Token has expired")
    except jwt.InvalidTokenError:
        raise JWTError("Invalid token")
