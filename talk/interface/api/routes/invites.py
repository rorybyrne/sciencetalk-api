"""Invite routes."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Cookie, HTTPException, Query, status
from pydantic import BaseModel

from talk.application.usecase.invite import (
    CreateInvitesUseCase,
    GetInvitesUseCase,
)
from talk.application.usecase.invite.create_invites import (
    CreateInvitesRequest,
    CreateInvitesResponse,
    InviteeInfo,
)
from talk.application.usecase.invite.get_invites import (
    GetInvitesRequest,
    GetInvitesResponse,
)
from talk.domain.service import JWTService
from talk.domain.value import AuthProvider, InviteStatus
from talk.util.jwt import JWTError

router = APIRouter(prefix="/invites", tags=["invites"], route_class=DishkaRoute)


class InviteeAPIInfo(BaseModel):
    """API info for a single invitee."""

    provider: AuthProvider
    handle: str
    name: str | None = None


class CreateInvitesAPIRequest(BaseModel):
    """API request for creating invites."""

    invitees: list[InviteeAPIInfo]


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
            invitees=[
                InviteeInfo(
                    provider=invitee.provider,
                    handle=invitee.handle,
                    name=invitee.name,
                )
                for invitee in request.invitees
            ],
        )
        response = await create_invites_use_case.execute(use_case_request)
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=GetInvitesResponse)
async def get_invites(
    get_invites_use_case: FromDishka[GetInvitesUseCase],
    jwt_service: FromDishka[JWTService],
    auth_token: str | None = Cookie(default=None),
    status_filter: InviteStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> GetInvitesResponse:
    """Get invites created by the current user.

    Args:
        get_invites_use_case: Get invites use case from DI
        jwt_service: JWT service from DI
        auth_token: JWT token from cookie
        status_filter: Optional status filter (pending, accepted)
        limit: Maximum number of results (1-100)
        offset: Number of results to skip

    Returns:
        List of invites

    Raises:
        HTTPException: If not authenticated
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
    request = GetInvitesRequest(
        inviter_id=payload.user_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    response = await get_invites_use_case.execute(request)
    return response
