"""Get user invitation tree use case."""

from pydantic import BaseModel

from talk.domain.service import UserService, UserTreeNode


class UserTreeNodeResponse(BaseModel):
    """User tree node for API response.

    Represents a user and their children in the invitation tree.
    Recursive structure mirroring the domain model.
    """

    user_id: str
    handle: str
    karma: int | None
    children: list["UserTreeNodeResponse"]

    @classmethod
    def from_domain(cls, node: UserTreeNode) -> "UserTreeNodeResponse":
        """Convert domain UserTreeNode to response model.

        Args:
            node: Domain user tree node

        Returns:
            API response model with children recursively converted
        """
        return cls(
            user_id=str(node.user_id),
            handle=node.handle.root,
            karma=node.karma,
            children=[cls.from_domain(child) for child in node.children],
        )


class GetUserTreeResponse(BaseModel):
    """Get user tree response."""

    roots: list[UserTreeNodeResponse]
    total_users: int


class GetUserTreeUseCase:
    """Use case for getting the complete user invitation tree.

    Returns a hierarchical tree showing who invited whom, with root users
    (users with no inviter) at the top level. Children are sorted by karma
    at each level.
    """

    def __init__(self, user_service: UserService) -> None:
        """Initialize get user tree use case.

        Args:
            user_service: User domain service
        """
        self.user_service = user_service

    async def execute(self, include_karma: bool = True) -> GetUserTreeResponse:
        """Execute get user tree flow.

        Steps:
        1. Call user service to build invitation tree
        2. Convert domain tree nodes to response models
        3. Return tree with roots and total count

        Args:
            include_karma: Whether to include karma in response (default: True).
                          Can be set to False for better performance if karma not needed.

        Returns:
            User tree with hierarchical structure showing invitation relationships
        """
        # Build tree via domain service
        tree_roots = await self.user_service.build_invitation_tree(
            include_karma=include_karma
        )

        # Calculate total users (count all nodes recursively)
        def count_nodes(node: UserTreeNode) -> int:
            return 1 + sum(count_nodes(child) for child in node.children)

        total_users = sum(count_nodes(root) for root in tree_roots)

        # Convert to response models
        return GetUserTreeResponse(
            roots=[UserTreeNodeResponse.from_domain(root) for root in tree_roots],
            total_users=total_users,
        )
