"""Application layer DI providers."""

from dishka import Scope, provide

from talk.config import Settings
from talk.util.di.base import ProviderBase
from talk.application.usecase.auth import GetCurrentUserUseCase, LoginUseCase
from talk.application.usecase.comment import (
    CreateCommentUseCase,
    GetCommentsUseCase,
    UpdateCommentUseCase,
)
from talk.application.usecase.invite import (
    CreateInvitesUseCase,
    GetInvitesUseCase,
    ValidateInviteUseCase,
)
from talk.application.usecase.post import (
    CreatePostUseCase,
    GetPostUseCase,
    ListPostsUseCase,
    UpdatePostUseCase,
)
from talk.application.usecase.tag import ListTagsUseCase
from talk.application.usecase.user import (
    GetUserProfileUseCase,
    GetUserTreeUseCase,
    UpdateUserProfileUseCase,
)
from talk.application.usecase.vote import RemoveVoteUseCase, UpvoteUseCase
from talk.domain.repository import PostRepository, VoteRepository
from talk.domain.service import (
    AuthService,
    CommentService,
    InviteService,
    JWTService,
    PostService,
    TagService,
    UserIdentityService,
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
        user_service: UserService,
        user_identity_service: UserIdentityService,
        invite_service: InviteService,
        settings: Settings,
    ) -> LoginUseCase:
        """Provide login use case."""
        return LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_service=user_service,
            user_identity_service=user_identity_service,
            invite_service=invite_service,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def get_current_user_use_case(
        self,
        jwt_service: JWTService,
        user_service: UserService,
        invite_service: InviteService,
        user_identity_service: UserIdentityService,
    ) -> GetCurrentUserUseCase:
        """Provide get current user use case."""
        return GetCurrentUserUseCase(
            jwt_service=jwt_service,
            user_service=user_service,
            invite_service=invite_service,
            user_identity_service=user_identity_service,
        )

    # Post use cases
    @provide(scope=Scope.REQUEST)
    def get_create_post_use_case(
        self,
        post_service: PostService,
        tag_service: TagService,
        user_service: UserService,
    ) -> CreatePostUseCase:
        """Provide create post use case."""
        return CreatePostUseCase(
            post_service=post_service,
            tag_service=tag_service,
            user_service=user_service,
        )

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

    @provide(scope=Scope.REQUEST)
    def get_update_post_use_case(
        self, post_service: PostService, vote_repository: VoteRepository
    ) -> UpdatePostUseCase:
        """Provide update post use case."""
        return UpdatePostUseCase(
            post_service=post_service, vote_repository=vote_repository
        )

    # Comment use cases
    @provide(scope=Scope.REQUEST)
    def get_create_comment_use_case(
        self,
        comment_service: CommentService,
        post_service: PostService,
        user_service: UserService,
    ) -> CreateCommentUseCase:
        """Provide create comment use case."""
        return CreateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            user_service=user_service,
        )

    @provide(scope=Scope.REQUEST)
    def get_get_comments_use_case(
        self,
        comment_service: CommentService,
        vote_service: VoteService,
        jwt_service: JWTService,
    ) -> GetCommentsUseCase:
        """Provide get comments use case."""
        return GetCommentsUseCase(
            comment_service=comment_service,
            vote_service=vote_service,
            jwt_service=jwt_service,
        )

    @provide(scope=Scope.REQUEST)
    def get_update_comment_use_case(
        self,
        comment_service: CommentService,
        post_service: PostService,
        vote_repository: VoteRepository,
    ) -> UpdateCommentUseCase:
        """Provide update comment use case."""
        return UpdateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            vote_repository=vote_repository,
        )

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
        user_identity_service: UserIdentityService,
        settings: Settings,
    ) -> CreateInvitesUseCase:
        """Provide create invites use case."""
        return CreateInvitesUseCase(
            invite_service=invite_service,
            user_service=user_service,
            user_identity_service=user_identity_service,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def get_get_invites_use_case(
        self,
        invite_service: InviteService,
        user_service: UserService,
        settings: Settings,
    ) -> GetInvitesUseCase:
        """Provide get invites use case."""
        return GetInvitesUseCase(
            invite_service=invite_service, user_service=user_service, settings=settings
        )

    @provide(scope=Scope.REQUEST)
    def get_validate_invite_use_case(
        self, invite_service: InviteService, user_service: UserService
    ) -> ValidateInviteUseCase:
        """Provide validate invite use case."""
        return ValidateInviteUseCase(
            invite_service=invite_service, user_service=user_service
        )

    # User use cases
    @provide(scope=Scope.REQUEST)
    def get_get_user_profile_use_case(
        self, user_service: UserService, user_identity_service: UserIdentityService
    ) -> GetUserProfileUseCase:
        """Provide get user profile use case."""
        return GetUserProfileUseCase(
            user_service=user_service, user_identity_service=user_identity_service
        )

    @provide(scope=Scope.REQUEST)
    def get_update_user_profile_use_case(
        self, user_service: UserService
    ) -> UpdateUserProfileUseCase:
        """Provide update user profile use case."""
        return UpdateUserProfileUseCase(user_service=user_service)

    @provide(scope=Scope.REQUEST)
    def get_get_user_tree_use_case(
        self, user_service: UserService
    ) -> GetUserTreeUseCase:
        """Provide get user tree use case."""
        return GetUserTreeUseCase(user_service=user_service)

    # Tag use cases
    @provide(scope=Scope.REQUEST)
    def get_list_tags_use_case(self, tag_service: TagService) -> ListTagsUseCase:
        """Provide list tags use case."""
        return ListTagsUseCase(tag_service=tag_service)
