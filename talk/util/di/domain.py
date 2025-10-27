"""Domain layer DI providers."""

from dishka import Scope, provide

from talk.adapter.bluesky.auth import BlueskyAuthClient
from talk.util.di.base import ProviderBase
from talk.config import AuthSettings
from talk.domain.repository import (
    CommentRepository,
    InviteRepository,
    PostRepository,
    UserRepository,
    VoteRepository,
)
from talk.domain.service import (
    AuthService,
    CommentService,
    InviteService,
    JWTService,
    PostService,
    UserService,
    VoteService,
)


class ProdDomainProvider(ProviderBase):
    """Production domain services provider - concrete, no mocks needed.

    Domain services are REQUEST-scoped to align with repository/session lifecycle.
    Each HTTP request gets fresh service instances with their own transaction.
    """

    scope = Scope.REQUEST

    @provide
    def get_auth_service(self, bluesky_client: BlueskyAuthClient) -> AuthService:
        """Provide authentication domain service."""
        return AuthService(bluesky_client=bluesky_client)

    @provide
    def get_jwt_service(self, auth_settings: AuthSettings) -> JWTService:
        """Provide JWT token domain service."""
        return JWTService(auth_settings=auth_settings)

    @provide
    def get_comment_service(
        self, comment_repository: CommentRepository
    ) -> CommentService:
        """Provide comment domain service."""
        return CommentService(comment_repository=comment_repository)

    @provide
    def get_post_service(self, post_repository: PostRepository) -> PostService:
        """Provide post domain service."""
        return PostService(post_repository=post_repository)

    @provide
    def get_vote_service(
        self,
        vote_repository: VoteRepository,
        post_service: PostService,
        comment_service: CommentService,
    ) -> VoteService:
        """Provide vote domain service."""
        return VoteService(
            vote_repository=vote_repository,
            post_service=post_service,
            comment_service=comment_service,
        )

    @provide
    def get_invite_service(self, invite_repository: InviteRepository) -> InviteService:
        """Provide invite domain service."""
        return InviteService(invite_repository=invite_repository)

    @provide
    def get_user_service(self, user_repository: UserRepository) -> UserService:
        """Provide user domain service."""
        return UserService(user_repository=user_repository)
