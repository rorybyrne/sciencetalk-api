"""Domain layer DI providers."""

from dishka import Scope, provide

from talk.config import AuthSettings
from talk.domain.repository import (
    CommentRepository,
    InviteRepository,
    PostRepository,
    UserIdentityRepository,
    UserRepository,
    VoteRepository,
)
from talk.domain.repository.tag import TagRepository
from talk.domain.service import (
    AuthService,
    CommentService,
    InviteService,
    JWTService,
    OAuthClient,
    PostService,
    TagService,
    UserIdentityService,
    UserService,
    VoteService,
)
from talk.domain.value import AuthProvider
from talk.util.di.base import ProviderBase


class ProdDomainProvider(ProviderBase):
    """Production domain services provider - concrete, no mocks needed.

    Domain services are REQUEST-scoped to align with repository/session lifecycle.
    Each HTTP request gets fresh service instances with their own transaction.
    """

    scope = Scope.REQUEST

    @provide
    def get_auth_service(
        self, oauth_clients: dict[AuthProvider, OAuthClient]
    ) -> AuthService:
        """Provide multi-provider authentication domain service.

        Args:
            oauth_clients: Dictionary mapping providers to their OAuth clients

        Returns:
            AuthService configured with all available OAuth clients
        """
        return AuthService(oauth_clients=oauth_clients)

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
        user_service: UserService,
    ) -> VoteService:
        """Provide vote domain service."""
        return VoteService(
            vote_repository=vote_repository,
            post_service=post_service,
            comment_service=comment_service,
            user_service=user_service,
        )

    @provide
    def get_invite_service(self, invite_repository: InviteRepository) -> InviteService:
        """Provide invite domain service."""
        return InviteService(invite_repository=invite_repository)

    @provide
    def get_user_service(
        self, user_repository: UserRepository, invite_repository: InviteRepository
    ) -> UserService:
        """Provide user domain service."""
        return UserService(
            user_repository=user_repository, invite_repository=invite_repository
        )

    @provide
    def get_user_identity_service(
        self, user_identity_repository: UserIdentityRepository
    ) -> UserIdentityService:
        """Provide user identity domain service."""
        return UserIdentityService(user_identity_repository=user_identity_repository)

    @provide
    def get_tag_service(self, tag_repository: TagRepository) -> TagService:
        """Provide tag domain service."""
        return TagService(tag_repository=tag_repository)
