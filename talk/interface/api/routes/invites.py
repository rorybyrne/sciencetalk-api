"""Invite routes."""

from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, Cookie, HTTPException, status
from pydantic import BaseModel

from talk.application.usecase.invite import CreateInvitesUseCase
from talk.application.usecase.invite.create_invites import (
    CreateInvitesRequest,
    CreateInvitesResponse,
)
from talk.domain.service import JWTService
from talk.util.jwt import JWTError

router = APIRouter(prefix="/invites", tags=["invites"])


class CreateInvitesAPIRequest(BaseModel):
    """API request for creating invites."""

    invitee_handles: list[str]


@router.post(
    "/", response_model=CreateInvitesResponse, status_code=status.HTTP_201_CREATED
)
async def create_invites(
    request: CreateInvitesAPIRequest,
    create_invites_use_case: FromDishka[CreateInvitesUseCase],
    jwt_service: FromDishka[JWTService],
    auth_token: str | None = Cookie(default=None),
) -> CreateInvitesResponse:
    """Create multiple invites.

    Args:
        request: Request with list of handles to invite
        create_invites_use_case: Create invites use case from DI
        jwt_service: JWT service from DI
        auth_token: JWT token from cookie

    Returns:
        Response with created count and failed handles

    Raises:
        HTTPException: If not authenticated or quota exceeded
    """
    # Authenticate user
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt_service.verify_token(auth_token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Execute use case
    try:
        use_case_request = CreateInvitesRequest(
            inviter_id=payload.user_id,
            invitee_handles=request.invitee_handles,
        )
        response = await create_invites_use_case.execute(use_case_request)
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
