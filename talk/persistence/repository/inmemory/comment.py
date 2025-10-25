"""In-memory comment repository for testing."""

from typing import Optional

from talk.domain.model.comment import Comment
from talk.domain.repository.comment import CommentRepository
from talk.domain.value import CommentId, PostId, UserId


class InMemoryCommentRepository(CommentRepository):
    """In-memory implementation of CommentRepository for testing."""

    def __init__(self) -> None:
        self._comments: dict[CommentId, Comment] = {}

    async def find_by_id(self, comment_id: CommentId) -> Optional[Comment]:
        """Find a comment by ID."""
        return self._comments.get(comment_id)

    async def find_by_post(
        self,
        post_id: PostId,
        include_deleted: bool = False,
    ) -> list[Comment]:
        """Find all comments for a post in tree order."""
        comments = [c for c in self._comments.values() if c.post_id == post_id]

        # Filter deleted
        if not include_deleted:
            comments = [c for c in comments if c.deleted_at is None]

        # Sort by path (tree order)
        comments.sort(key=lambda c: c.path if c.path else "")

        return comments

    async def find_by_author(
        self,
        author_id: UserId,
        include_deleted: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> list[Comment]:
        """Find comments by a specific author."""
        comments = [c for c in self._comments.values() if c.author_id == author_id]

        # Filter deleted
        if not include_deleted:
            comments = [c for c in comments if c.deleted_at is None]

        # Sort by created_at descending
        comments.sort(key=lambda c: c.created_at, reverse=True)

        # Paginate
        return comments[offset : offset + limit]

    async def find_children(
        self,
        parent_id: CommentId,
        include_deleted: bool = False,
    ) -> list[Comment]:
        """Find direct children of a comment."""
        comments = [c for c in self._comments.values() if c.parent_id == parent_id]

        # Filter deleted
        if not include_deleted:
            comments = [c for c in comments if c.deleted_at is None]

        # Sort by path
        comments.sort(key=lambda c: c.path if c.path else "")

        return comments

    async def count_by_post(self, post_id: PostId) -> int:
        """Count comments for a post (excluding deleted)."""
        return sum(
            1
            for c in self._comments.values()
            if c.post_id == post_id and c.deleted_at is None
        )

    async def save(self, comment: Comment) -> Comment:
        """Save or update a comment."""
        self._comments[comment.id] = comment
        return comment

    async def delete(self, comment_id: CommentId) -> None:
        """Delete a comment."""
        self._comments.pop(comment_id, None)

    async def increment_points(self, comment_id: CommentId) -> None:
        """Atomically increment points by 1."""
        comment = self._comments.get(comment_id)
        if comment:
            # Create updated comment (since comments are immutable)
            self._comments[comment_id] = Comment(
                id=comment.id,
                post_id=comment.post_id,
                author_id=comment.author_id,
                author_handle=comment.author_handle,
                text=comment.text,
                parent_id=comment.parent_id,
                depth=comment.depth,
                path=comment.path,
                points=comment.points + 1,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                deleted_at=comment.deleted_at,
            )

    async def decrement_points(self, comment_id: CommentId) -> None:
        """Atomically decrement points by 1 (minimum 1)."""
        comment = self._comments.get(comment_id)
        if comment and comment.points > 1:
            # Create updated comment (since comments are immutable)
            self._comments[comment_id] = Comment(
                id=comment.id,
                post_id=comment.post_id,
                author_id=comment.author_id,
                author_handle=comment.author_handle,
                text=comment.text,
                parent_id=comment.parent_id,
                depth=comment.depth,
                path=comment.path,
                points=comment.points - 1,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                deleted_at=comment.deleted_at,
            )
