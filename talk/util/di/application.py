"""Application layer DI providers."""

from dishka import Scope, provide

from talk.config import Settings
from talk.util.di.base import ProviderBase
from talk.application.usecase.auth import GetCurrentUserUseCase, LoginUseCase
from talk.application.usecase.comment import (
    CreateCommentUseCase,
    GetCommentsUseCase,
)
from talk.application.usecase.invite import CreateInvitesUseCase, GetInvitesUseCase
from talk.application.usecase.post import (
    CreatePostUseCase,
    GetPostUseCase,
    ListPostsUseCase,
)
from talk.application.usecase.user import GetUserProfileUseCase
from talk.application.usecase.vote import RemoveVoteUseCase, UpvoteUseCase
from talk.domain.repository import PostRepository, UserRepository, VoteRepository
from talk.domain.service import (
    AuthService,
    CommentService,
    InviteService,
    JWTService,
    PostService,
    UserService,
    VoteService,
)


class ProdApplicationProvider(ProviderBase):
    """Production application use cases provider - concrete, no mocks needed."""

    # Auth use cases
    @provide(scope=Scope.REQUEST)
    def get_login_use_case(
        self,
        auth_service: AuthService,
        jwt_service: JWTService,
        user_repository: UserRepository,
        invite_service: InviteService,
        settings: Settings,
    ) -> LoginUseCase:
        """Provide login use case."""
        return LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_repository=user_repository,
            invite_service=invite_service,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def get_current_user_use_case(
        self,
        jwt_service: JWTService,
        user_repository: UserRepository,
        invite_service: InviteService,
    ) -> GetCurrentUserUseCase:
        """Provide get current user use case."""
        return GetCurrentUserUseCase(
            jwt_service=jwt_service,
            user_repository=user_repository,
            invite_service=invite_service,
        )

    # Post use cases
    @provide(scope=Scope.REQUEST)
    def get_create_post_use_case(
        self, post_repository: PostRepository
    ) -> CreatePostUseCase:
        """Provide create post use case."""
        return CreatePostUseCase(post_repository=post_repository)

    @provide(scope=Scope.REQUEST)
    def get_get_post_use_case(
        self, post_repository: PostRepository, vote_repository: VoteRepository
    ) -> GetPostUseCase:
        """Provide get post use case."""
        return GetPostUseCase(
            post_repository=post_repository, vote_repository=vote_repository
        )

    @provide(scope=Scope.REQUEST)
    def get_list_posts_use_case(
        self, post_repository: PostRepository, vote_repository: VoteRepository
    ) -> ListPostsUseCase:
        """Provide list posts use case."""
        return ListPostsUseCase(
            post_repository=post_repository, vote_repository=vote_repository
        )

    # Comment use cases
    @provide(scope=Scope.REQUEST)
    def get_create_comment_use_case(
        self, comment_service: CommentService, post_service: PostService
    ) -> CreateCommentUseCase:
        """Provide create comment use case."""
        return CreateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
        )

    @provide(scope=Scope.REQUEST)
    def get_get_comments_use_case(
        self, comment_service: CommentService
    ) -> GetCommentsUseCase:
        """Provide get comments use case."""
        return GetCommentsUseCase(comment_service=comment_service)

    # Vote use cases
    @provide(scope=Scope.REQUEST)
    def get_upvote_use_case(self, vote_service: VoteService) -> UpvoteUseCase:
        """Provide upvote use case."""
        return UpvoteUseCase(vote_service=vote_service)

    @provide(scope=Scope.REQUEST)
    def get_remove_vote_use_case(self, vote_service: VoteService) -> RemoveVoteUseCase:
        """Provide remove vote use case."""
        return RemoveVoteUseCase(vote_service=vote_service)

    # Invite use cases
    @provide(scope=Scope.REQUEST)
    def get_create_invites_use_case(
        self,
        invite_service: InviteService,
        user_service: UserService,
        settings: Settings,
    ) -> CreateInvitesUseCase:
        """Provide create invites use case."""
        return CreateInvitesUseCase(
            invite_service=invite_service,
            user_service=user_service,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def get_get_invites_use_case(
        self, invite_service: InviteService, user_service: UserService
    ) -> GetInvitesUseCase:
        """Provide get invites use case."""
        return GetInvitesUseCase(
            invite_service=invite_service, user_service=user_service
        )

    # User use cases
    @provide(scope=Scope.REQUEST)
    def get_get_user_profile_use_case(
        self, user_service: UserService
    ) -> GetUserProfileUseCase:
        """Provide get user profile use case."""
        return GetUserProfileUseCase(user_service=user_service)
