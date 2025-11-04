"""In-memory post repository for testing."""

from typing import Optional

from talk.domain.model.post import Post
from talk.domain.repository.post import PostRepository, PostSortOrder
from talk.domain.value import PostId, UserId
from talk.domain.value.types import TagName


class InMemoryPostRepository(PostRepository):
    """In-memory implementation of PostRepository for testing."""

    def __init__(self) -> None:
        self._posts: dict[PostId, Post] = {}

    async def find_by_id(self, post_id: PostId) -> Optional[Post]:
        """Find a post by ID."""
        return self._posts.get(post_id)

    async def find_all(
        self,
        sort: PostSortOrder = PostSortOrder.RECENT,
        tag: Optional[TagName] = None,
        include_deleted: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> list[Post]:
        """Find posts with filtering and pagination."""
        posts = [p for p in self._posts.values()]

        # Filter by tag
        if tag is not None:
            posts = [p for p in posts if tag in p.tag_names]

        # Filter deleted
        if not include_deleted:
            posts = [p for p in posts if p.deleted_at is None]

        # Sort
        if sort == PostSortOrder.RECENT:
            posts.sort(key=lambda p: p.created_at, reverse=True)
        else:  # PostSortOrder.ACTIVE
            posts.sort(key=lambda p: p.updated_at, reverse=True)

        # Paginate
        return posts[offset : offset + limit]

    async def count(
        self,
        tag: Optional[TagName] = None,
        include_deleted: bool = False,
    ) -> int:
        """Count posts matching the given filters."""
        posts = [p for p in self._posts.values()]

        # Filter by tag
        if tag is not None:
            posts = [p for p in posts if tag in p.tag_names]

        # Filter deleted
        if not include_deleted:
            posts = [p for p in posts if p.deleted_at is None]

        return len(posts)

    async def find_by_author(
        self,
        author_id: UserId,
        include_deleted: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> list[Post]:
        """Find posts by a specific author."""
        posts = [p for p in self._posts.values() if p.author_id == author_id]

        # Filter deleted
        if not include_deleted:
            posts = [p for p in posts if p.deleted_at is None]

        # Sort by recent
        posts.sort(key=lambda p: p.created_at, reverse=True)

        # Paginate
        return posts[offset : offset + limit]

    async def save(self, post: Post) -> Post:
        """Save or update a post."""
        self._posts[post.id] = post
        return post

    async def delete(self, post_id: PostId) -> None:
        """Delete a post."""
        self._posts.pop(post_id, None)

    async def list_posts(self, limit: int = 10, offset: int = 0) -> list[Post]:
        """List posts with pagination."""
        posts = sorted(
            self._posts.values(),
            key=lambda p: p.created_at,
            reverse=True,
        )
        return posts[offset : offset + limit]

    async def increment_points(self, post_id: PostId) -> None:
        """Atomically increment points by 1."""
        post = self._posts.get(post_id)
        if post:
            # Create updated post (since posts are immutable)
            self._posts[post_id] = Post(
                id=post.id,
                title=post.title,
                tag_names=post.tag_names,
                author_id=post.author_id,
                author_handle=post.author_handle,
                url=post.url,
                text=post.text,
                points=post.points + 1,
                comment_count=post.comment_count,
                created_at=post.created_at,
                updated_at=post.updated_at,
                deleted_at=post.deleted_at,
            )

    async def decrement_points(self, post_id: PostId) -> None:
        """Atomically decrement points by 1 (minimum 1)."""
        post = self._posts.get(post_id)
        if post and post.points > 1:
            # Create updated post (since posts are immutable)
            self._posts[post_id] = Post(
                id=post.id,
                title=post.title,
                tag_names=post.tag_names,
                author_id=post.author_id,
                author_handle=post.author_handle,
                url=post.url,
                text=post.text,
                points=post.points - 1,
                comment_count=post.comment_count,
                created_at=post.created_at,
                updated_at=post.updated_at,
                deleted_at=post.deleted_at,
            )
