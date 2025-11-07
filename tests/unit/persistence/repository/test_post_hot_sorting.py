"""Unit tests for post hot sorting algorithm."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from talk.domain.model.post import Post
from talk.domain.repository.post import PostSortOrder
from talk.domain.value import PostId, UserId
from talk.domain.value.types import Handle, TagName
from talk.persistence.repository.inmemory.post import InMemoryPostRepository


class TestPostHotSorting:
    """Unit tests for hot sorting algorithm."""

    @pytest.mark.asyncio
    async def test_hot_sort_favors_recent_posts(self):
        """New post with few points should rank higher than old post with same points."""
        # Arrange
        repo = InMemoryPostRepository()

        # Old post with 2 points
        old_post = Post(
            id=PostId(uuid4()),
            title="Old Post",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="old.bsky.social"),
            text="Old content",
            tag_names=[TagName(root="biology")],
            points=2,
            created_at=datetime.now() - timedelta(days=7),
        )

        # New post with 2 points
        new_post = Post(
            id=PostId(uuid4()),
            title="New Post",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="new.bsky.social"),
            text="New content",
            tag_names=[TagName(root="biology")],
            points=2,
            created_at=datetime.now() - timedelta(hours=1),
        )

        await repo.save(old_post)
        await repo.save(new_post)

        # Act
        posts = await repo.find_all(sort=PostSortOrder.HOT)

        # Assert
        assert len(posts) == 2
        assert posts[0].id == new_post.id, "New post should rank higher"
        assert posts[1].id == old_post.id

    @pytest.mark.asyncio
    async def test_hot_sort_considers_points(self):
        """Post with more points should rank higher if ages are similar."""
        # Arrange
        repo = InMemoryPostRepository()
        base_time = datetime.now() - timedelta(hours=5)

        # Low points post
        low_points = Post(
            id=PostId(uuid4()),
            title="Low Points",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="low.bsky.social"),
            text="Low points content",
            tag_names=[TagName(root="biology")],
            points=2,
            created_at=base_time,
        )

        # High points post
        high_points = Post(
            id=PostId(uuid4()),
            title="High Points",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="high.bsky.social"),
            text="High points content",
            tag_names=[TagName(root="biology")],
            points=20,
            created_at=base_time,
        )

        await repo.save(low_points)
        await repo.save(high_points)

        # Act
        posts = await repo.find_all(sort=PostSortOrder.HOT)

        # Assert
        assert len(posts) == 2
        assert posts[0].id == high_points.id, "High points post should rank higher"
        assert posts[1].id == low_points.id

    @pytest.mark.asyncio
    async def test_hot_sort_balances_age_and_points(self):
        """Verify time-decay algorithm balances recency and popularity."""
        # Arrange
        repo = InMemoryPostRepository()

        # Very old post with many points
        old_popular = Post(
            id=PostId(uuid4()),
            title="Old Popular",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="oldpop.bsky.social"),
            text="Old popular content",
            tag_names=[TagName(root="biology")],
            points=100,
            created_at=datetime.now() - timedelta(days=30),
        )

        # Recent post with moderate points
        recent_moderate = Post(
            id=PostId(uuid4()),
            title="Recent Moderate",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="recmod.bsky.social"),
            text="Recent moderate content",
            tag_names=[TagName(root="biology")],
            points=10,
            created_at=datetime.now() - timedelta(hours=2),
        )

        # Very recent post with few points
        very_recent = Post(
            id=PostId(uuid4()),
            title="Very Recent",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="veryrecent.bsky.social"),
            text="Very recent content",
            tag_names=[TagName(root="biology")],
            points=2,
            created_at=datetime.now() - timedelta(minutes=30),
        )

        await repo.save(old_popular)
        await repo.save(recent_moderate)
        await repo.save(very_recent)

        # Act
        posts = await repo.find_all(sort=PostSortOrder.HOT)

        # Assert
        assert len(posts) == 3
        # Recent moderate (10 points, 2 hours) should beat very recent (2 points, 30 min)
        # Score calculation with new formula (no -1 penalty):
        # recent_moderate: 10 / (2+1)^1.8 ≈ 10 / 5.66 ≈ 1.77
        # very_recent: 2 / (0.5+1)^1.8 ≈ 2 / 2.08 ≈ 0.96
        assert posts[0].id == recent_moderate.id
        # Very recent should be second
        assert posts[1].id == very_recent.id
        # Old popular should be last despite many points (30 days old)
        assert posts[2].id == old_popular.id

    @pytest.mark.asyncio
    async def test_hot_sort_new_post_is_visible(self):
        """Brand new posts are visible but don't dominate older popular posts."""
        # Arrange
        repo = InMemoryPostRepository()

        # Create older popular posts
        popular_post = Post(
            id=PostId(uuid4()),
            title="Popular Post",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="popular.bsky.social"),
            text="Popular content",
            tag_names=[TagName(root="biology")],
            points=20,
            created_at=datetime.now() - timedelta(hours=2),
        )

        # Brand new post with just initial point
        brand_new = Post(
            id=PostId(uuid4()),
            title="Brand New",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="new.bsky.social"),
            text="Just posted",
            tag_names=[TagName(root="biology")],
            points=1,  # No upvotes yet
            created_at=datetime.now() - timedelta(minutes=1),
        )

        await repo.save(popular_post)
        await repo.save(brand_new)

        # Act
        posts = await repo.find_all(sort=PostSortOrder.HOT)

        # Assert
        assert len(posts) == 2
        # Popular post should rank higher
        assert posts[0].id == popular_post.id
        # But brand new post is still visible (not score 0)
        assert posts[1].id == brand_new.id

    @pytest.mark.asyncio
    async def test_hot_sort_with_tag_filter(self):
        """Hot sorting should work with tag filtering."""
        # Arrange
        repo = InMemoryPostRepository()

        bio_post = Post(
            id=PostId(uuid4()),
            title="Biology Post",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="bio.bsky.social"),
            text="Biology content",
            tag_names=[TagName(root="biology")],
            points=10,
            created_at=datetime.now() - timedelta(hours=1),
        )

        chem_post = Post(
            id=PostId(uuid4()),
            title="Chemistry Post",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="chem.bsky.social"),
            text="Chemistry content",
            tag_names=[TagName(root="chemistry")],
            points=20,
            created_at=datetime.now() - timedelta(hours=1),
        )

        await repo.save(bio_post)
        await repo.save(chem_post)

        # Act
        posts = await repo.find_all(sort=PostSortOrder.HOT, tag=TagName(root="biology"))

        # Assert
        assert len(posts) == 1
        assert posts[0].id == bio_post.id
