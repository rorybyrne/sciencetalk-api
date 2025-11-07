"""Unit tests for post hot sorting algorithm."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from talk.domain.model.post import Post
from talk.domain.repository.post import PostSortOrder
from talk.domain.value import PostId, UserId
from talk.domain.value.types import Handle, TagName
from talk.persistence.repository.inmemory.post import InMemoryPostRepository
from tests.conftest import make_slug


class TestPostHotSorting:
    """Unit tests for hot sorting algorithm."""

    @pytest.mark.asyncio
    async def test_hot_sort_favors_recent_posts(self):
        """New post with few points should rank higher than old post with same points."""
        # Arrange
        repo = InMemoryPostRepository()

        # Old post with 2 points
        old_post_id = PostId(uuid4())
        old_post = Post(
            id=old_post_id,
            slug=make_slug("Old Post", old_post_id),
            title="Old Post",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="old.bsky.social"),
            text="Old content",
            tag_names=[TagName(root="biology")],
            points=2,
            created_at=datetime.now() - timedelta(days=7),
        )

        # New post with 2 points
        new_post_id = PostId(uuid4())
        new_post = Post(
            id=new_post_id,
            slug=make_slug("New Post", new_post_id),
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
        low_points_id = PostId(uuid4())
        low_points = Post(
            id=low_points_id,
            slug=make_slug("Low Points", low_points_id),
            title="Low Points",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="low.bsky.social"),
            text="Low points content",
            tag_names=[TagName(root="biology")],
            points=2,
            created_at=base_time,
        )

        # High points post
        high_points_id = PostId(uuid4())
        high_points = Post(
            id=high_points_id,
            slug=make_slug("High Points", high_points_id),
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
        old_popular_id = PostId(uuid4())
        old_popular = Post(
            id=old_popular_id,
            slug=make_slug("Old Popular", old_popular_id),
            title="Old Popular",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="oldpop.bsky.social"),
            text="Old popular content",
            tag_names=[TagName(root="biology")],
            points=100,
            created_at=datetime.now() - timedelta(days=30),
        )

        # Recent post with moderate points
        recent_moderate_id = PostId(uuid4())
        recent_moderate = Post(
            id=recent_moderate_id,
            slug=make_slug("Recent Moderate", recent_moderate_id),
            title="Recent Moderate",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="recmod.bsky.social"),
            text="Recent moderate content",
            tag_names=[TagName(root="biology")],
            points=10,
            created_at=datetime.now() - timedelta(hours=2),
        )

        # Very recent post with few points
        very_recent_id = PostId(uuid4())
        very_recent = Post(
            id=very_recent_id,
            slug=make_slug("Very Recent", very_recent_id),
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
        popular_post_id = PostId(uuid4())
        popular_post = Post(
            id=popular_post_id,
            slug=make_slug("Popular Post", popular_post_id),
            title="Popular Post",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="popular.bsky.social"),
            text="Popular content",
            tag_names=[TagName(root="biology")],
            points=20,
            created_at=datetime.now() - timedelta(hours=2),
        )

        # Brand new post with just initial point
        brand_new_id = PostId(uuid4())
        brand_new = Post(
            id=brand_new_id,
            slug=make_slug("Brand New", brand_new_id),
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

        bio_post_id = PostId(uuid4())
        bio_post = Post(
            id=bio_post_id,
            slug=make_slug("Biology Post", bio_post_id),
            title="Biology Post",
            author_id=UserId(uuid4()),
            author_handle=Handle(root="bio.bsky.social"),
            text="Biology content",
            tag_names=[TagName(root="biology")],
            points=10,
            created_at=datetime.now() - timedelta(hours=1),
        )

        chem_post_id = PostId(uuid4())
        chem_post = Post(
            id=chem_post_id,
            slug=make_slug("Chemistry Post", chem_post_id),
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
