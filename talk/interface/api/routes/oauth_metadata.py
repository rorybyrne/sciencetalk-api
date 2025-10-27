"""OAuth client metadata endpoint for AT Protocol."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter
from pydantic import BaseModel

from talk.config import Settings

router = APIRouter(route_class=DishkaRoute)


class OAuthClientMetadata(BaseModel):
    """OAuth client metadata response."""

    client_id: str
    client_name: str
    client_uri: str
    redirect_uris: list[str]
    grant_types: list[str]
    response_types: list[str]
    scope: str
    token_endpoint_auth_method: str
    application_type: str
    dpop_bound_access_tokens: bool


@router.get("/.well-known/oauth-client-metadata", response_model=OAuthClientMetadata)
def get_oauth_client_metadata(settings: FromDishka[Settings]) -> OAuthClientMetadata:
    """Serve OAuth client metadata for AT Protocol authentication.

    This endpoint provides metadata about this OAuth client, which serves
    as the client_id in AT Protocol OAuth flows. The URL of this endpoint
    is used as the client identifier.

    This must be publicly accessible over HTTPS in production.

    Returns:
        OAuth client metadata JSON per AT Protocol spec

    Example response:
        {
            "client_id": "https://talk.example.com/.well-known/oauth-client-metadata",
            "client_name": "Science Talk",
            "client_uri": "https://talk.example.com",
            "redirect_uris": ["https://talk.example.com/auth/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "atproto",
            "token_endpoint_auth_method": "none",
            "application_type": "web",
            "dpop_bound_access_tokens": true
        }
    """
    base_url = settings.api.base_url

    return OAuthClientMetadata(
        client_id=f"{base_url}/.well-known/oauth-client-metadata",
        client_name="Science Talk",
        client_uri=base_url,
        redirect_uris=[f"{base_url}/auth/callback"],
        grant_types=[
            "authorization_code",
            "refresh_token",
        ],  # Required by AT Protocol spec
        response_types=["code"],
        scope="atproto",
        token_endpoint_auth_method="none",  # Public client (no client secret)
        application_type="web",
        dpop_bound_access_tokens=True,  # REQUIRED by AT Protocol
    )
