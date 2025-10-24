# Persistence Layer - CLAUDE.md

## Purpose
The persistence layer provides **data storage implementations** for domain repositories. It handles database operations, schema definitions, and mappings between domain models and database representations. This layer depends on the domain layer but should be invisible to it.

## Key Principles
- **Implement repository interfaces** - Define domain repository interfaces, implement them here
- **Separation of concerns** - Domain models remain pure, persistence handles storage details
- **Dependency inversion** - Domain defines interfaces, persistence implements them
- **Manual mapping** - Explicit conversion between domain models and database rows
- **Async operations** - Use async/await for all database I/O

## Structure
- `database.py` - Database engine, session factory, and connection management
- `tables.py` - SQLAlchemy table definitions (metadata without ORM models)
- `mappers.py` - Conversion functions between database rows and domain models
- `repository/` - Repository implementations for each aggregate root
- `error.py` - Persistence-specific exceptions

## Architecture Overview

We use **SQLAlchemy Core with manual mapping** to keep domain models pure:

```
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                             │
│  • Pydantic models (immutable, validation)                  │
│  • Repository interfaces (abstract protocols)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Persistence Layer                           │
│  • SQLAlchemy tables (schema definition)                    │
│  • Mappers (row ↔ domain conversion)                        │
│  • Repository implementations (CRUD operations)             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL                               │
│  • Actual data storage                                      │
│  • Schema managed by Alembic migrations                     │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Guidelines

### Database Connection (`database.py`)
Manage async database engine and session lifecycle.

```python
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from talk.config import Settings

def create_engine(settings: Settings) -> AsyncEngine:
    """Create async database engine."""
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create session factory for dependency injection."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

async def get_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncSession:
    """Get database session (for DI container)."""
    async with session_factory() as session:
        yield session
```

**Key points:**
- Use `create_async_engine()` with asyncpg driver
- Set `expire_on_commit=False` to avoid lazy-loading issues
- Use `pool_pre_ping=True` to handle stale connections
- Yield session in `get_session()` for proper cleanup

### Table Definitions (`tables.py`)
Define database schema using SQLAlchemy Core (no ORM models).

```python
from sqlalchemy import Table, Column, String, Integer, ForeignKey, MetaData, Index
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("bluesky_did", String(255), nullable=False, unique=True),
    Column("handle", String(255), nullable=False),
    Column("display_name", String(255), nullable=True),
    Column("karma", Integer, nullable=False, server_default="0"),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"),
)

Index("idx_users_bluesky_did", users_table.c.bluesky_did)
Index("idx_users_handle", users_table.c.handle)

posts_table = Table(
    "posts",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("title", String(300), nullable=False),
    Column("type", postgresql.ENUM(..., name="post_type", create_type=False), nullable=False),
    Column("author_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("points", Integer, nullable=False, server_default="1"),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"),
    # ... other columns
)
```

**Key points:**
- Use `Table()` not declarative Base
- Define indexes separately for clarity
- Use PostgreSQL-specific types (UUID, TIMESTAMP, ENUM)
- Set `create_type=False` for enums (created in migrations)
- Use server-side defaults for timestamps and UUIDs

### Mappers (`mappers.py`)
Convert between database rows and domain models.

```python
from typing import Dict, Any
from uuid import UUID
from talk.domain.model.user import User
from talk.domain.value.types import UserId, BlueskyDID, Handle

def row_to_user(row: Dict[str, Any]) -> User:
    """Convert database row to User domain model."""
    return User(
        id=UserId(UUID(row["id"]) if isinstance(row["id"], str) else row["id"]),
        bluesky_did=BlueskyDID(value=row["bluesky_did"]),
        handle=Handle(value=row["handle"]),
        display_name=row.get("display_name"),
        avatar_url=row.get("avatar_url"),
        karma=row["karma"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )

def user_to_dict(user: User) -> Dict[str, Any]:
    """Convert User domain model to database dict."""
    return {
        "id": user.id.value,
        "bluesky_did": user.bluesky_did.value,
        "handle": user.handle.value,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "karma": user.karma,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
```

**Key points:**
- One pair of functions per aggregate root
- Handle UUID string/object conversion
- Unwrap value objects to primitives for database
- Wrap primitives in value objects for domain
- Use `Dict[str, Any]` for row type (works with Row._asdict())

### Repository Implementations (`repository/`)
Implement domain repository interfaces with SQLAlchemy async operations.

```python
from typing import Optional
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from talk.domain.model.user import User, UserRepository
from talk.domain.value.types import UserId, BlueskyDID
from talk.persistence.tables import users_table
from talk.persistence.mappers import row_to_user, user_to_dict

class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, user: User) -> User:
        """Save or update a user."""
        user_dict = user_to_dict(user)

        # Try to find existing user
        existing = await self.find_by_id(user.id)

        if existing:
            # Update existing
            stmt = (
                update(users_table)
                .where(users_table.c.id == user.id.value)
                .values(**user_dict)
            )
            await self.session.execute(stmt)
        else:
            # Insert new
            stmt = insert(users_table).values(**user_dict)
            await self.session.execute(stmt)

        await self.session.flush()
        return user

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find user by ID."""
        stmt = select(users_table).where(users_table.c.id == user_id.value)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_user(row._asdict()) if row else None

    async def find_by_bluesky_did(self, did: BlueskyDID) -> Optional[User]:
        """Find user by Bluesky DID."""
        stmt = select(users_table).where(users_table.c.bluesky_did == did.value)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_user(row._asdict()) if row else None

    async def delete(self, user_id: UserId) -> None:
        """Delete a user."""
        stmt = delete(users_table).where(users_table.c.id == user_id.value)
        await self.session.execute(stmt)
        await self.session.flush()
```

**Key points:**
- Take `AsyncSession` in `__init__` (injected by DI)
- Use SQLAlchemy Core (select, insert, update, delete)
- Call `await self.session.execute()` for all queries
- Use `fetchone()`, `fetchall()`, `scalars().all()` as appropriate
- Call `row._asdict()` to convert Row to dict for mappers
- Use `flush()` not `commit()` (transaction managed by use case)
- Always unwrap value objects to primitives in queries

### Query Patterns

#### Simple select
```python
stmt = select(users_table).where(users_table.c.id == user_id.value)
result = await self.session.execute(stmt)
row = result.fetchone()
```

#### Select with multiple conditions
```python
stmt = (
    select(posts_table)
    .where(posts_table.c.author_id == author_id.value)
    .where(posts_table.c.deleted_at.is_(None))
    .order_by(posts_table.c.created_at.desc())
)
result = await self.session.execute(stmt)
rows = result.fetchall()
```

#### Select with join
```python
stmt = (
    select(posts_table, users_table)
    .join(users_table, posts_table.c.author_id == users_table.c.id)
    .where(posts_table.c.id == post_id.value)
)
result = await self.session.execute(stmt)
row = result.fetchone()
```

#### Insert
```python
stmt = insert(users_table).values(**user_dict)
await self.session.execute(stmt)
await self.session.flush()
```

#### Update
```python
stmt = (
    update(posts_table)
    .where(posts_table.c.id == post_id.value)
    .values(points=new_points, updated_at=datetime.now())
)
await self.session.execute(stmt)
await self.session.flush()
```

#### Delete (soft delete)
```python
stmt = (
    update(posts_table)
    .where(posts_table.c.id == post_id.value)
    .values(deleted_at=datetime.now())
)
await self.session.execute(stmt)
await self.session.flush()
```

#### Count
```python
from sqlalchemy import func

stmt = select(func.count()).select_from(users_table)
result = await self.session.execute(stmt)
count = result.scalar()
```

## Dependency Injection

Repositories are provided via dishka DI container:

```python
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

class PersistenceProvider(Provider):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    @provide(scope=Scope.APP)
    def get_engine(self) -> AsyncEngine:
        return create_engine(self.settings)

    @provide(scope=Scope.APP)
    def get_session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return create_session_factory(engine)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncSession:
        async with session_factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        return PostgresUserRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_post_repository(self, session: AsyncSession) -> PostRepository:
        return PostgresPostRepository(session)
```

**Scopes:**
- `APP`: Engine and session factory (created once at startup)
- `REQUEST`: Session and repositories (new per HTTP request)

## Error Handling

Convert database errors to domain-appropriate exceptions:

```python
from sqlalchemy.exc import IntegrityError, NoResultFound
from talk.domain.error import DuplicateUserError, UserNotFoundError
from talk.persistence.error import PersistenceError

class PostgresUserRepository(UserRepository):
    async def save(self, user: User) -> User:
        try:
            # ... save logic
        except IntegrityError as e:
            if "unique constraint" in str(e).lower():
                raise DuplicateUserError(f"User with DID {user.bluesky_did} already exists")
            raise PersistenceError(f"Database constraint violation: {e}")
        except Exception as e:
            raise PersistenceError(f"Failed to save user: {e}")
```

## Testing Repositories

### Integration Tests
Test with real PostgreSQL database:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.integration
async def test_user_repository_save_and_find(db_session: AsyncSession):
    repo = PostgresUserRepository(db_session)

    user = User(
        id=UserId.generate(),
        bluesky_did=BlueskyDID(value="did:plc:test123"),
        handle=Handle(value="test.bsky.social"),
        karma=0,
    )

    # Save
    saved = await repo.save(user)
    await db_session.commit()

    # Find
    found = await repo.find_by_id(user.id)
    assert found is not None
    assert found.bluesky_did == user.bluesky_did
```

### In-Memory Repositories (Unit Tests)
For fast unit tests without database:

```python
from typing import Dict, Optional
from copy import deepcopy

class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: Dict[UserId, User] = {}

    async def save(self, user: User) -> User:
        self._users[user.id] = deepcopy(user)
        return deepcopy(user)

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        user = self._users.get(user_id)
        return deepcopy(user) if user else None

    async def delete(self, user_id: UserId) -> None:
        self._users.pop(user_id, None)
```

## Database Migrations

Schema changes are managed with Alembic:

```bash
# Create new migration
just db-migration "add_user_bio_field"

# Apply migrations
just db-migrate

# Rollback migration
alembic downgrade -1

# Show migration history
just db-history
```

**Important:** Tables in `tables.py` must match migration schema exactly.

## What Belongs Here
- **Database schema** - Table definitions, indexes, constraints
- **CRUD operations** - Create, read, update, delete via repositories
- **Query logic** - Filtering, sorting, pagination at database level
- **Transactions** - Session management (but commit in use case layer)
- **Data mapping** - Converting between domain models and database rows

## What NOT to Put Here
- **Business logic** → belongs in Domain layer
- **Transaction boundaries** → belongs in Application layer (use cases)
- **Validation** → belongs in Domain layer (Pydantic models)
- **Authorization** → belongs in Application or Interface layer
- **HTTP concerns** → belongs in Interface layer

## Common Patterns

### Pagination
```python
async def find_all(
    self,
    offset: int = 0,
    limit: int = 20
) -> list[User]:
    stmt = (
        select(users_table)
        .order_by(users_table.c.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await self.session.execute(stmt)
    return [row_to_user(row._asdict()) for row in result.fetchall()]
```

### Filtering
```python
async def find_by_criteria(
    self,
    post_type: Optional[PostType] = None,
    author_id: Optional[UserId] = None,
) -> list[Post]:
    stmt = select(posts_table).where(posts_table.c.deleted_at.is_(None))

    if post_type:
        stmt = stmt.where(posts_table.c.type == post_type.value)
    if author_id:
        stmt = stmt.where(posts_table.c.author_id == author_id.value)

    result = await self.session.execute(stmt)
    return [row_to_post(row._asdict()) for row in result.fetchall()]
```

### Batch Operations
```python
async def save_many(self, users: list[User]) -> None:
    stmt = insert(users_table)
    values = [user_to_dict(user) for user in users]
    await self.session.execute(stmt, values)
    await self.session.flush()
```

## Performance Considerations

- **Use indexes** - Add indexes for frequently queried columns
- **Batch queries** - Use `fetchall()` instead of multiple `fetchone()` calls
- **Limit results** - Always use pagination for list queries
- **Connection pooling** - Configured in `create_engine()`
- **Query optimization** - Use EXPLAIN ANALYZE for slow queries
- **Avoid N+1** - Use joins instead of multiple queries

## Questions to Ask Yourself
1. **What aggregate am I persisting?** - One repository per aggregate root
2. **How do I map domain to database?** - Use explicit mapper functions
3. **What queries are needed?** - Define repository methods based on use cases
4. **How do I handle errors?** - Convert database errors to domain errors
5. **Can this be tested without a database?** - Consider in-memory implementation

## Common Mistakes to Avoid
- **Business logic in repositories** - Keep it pure data access
- **Lazy loading** - Always eager load what you need (no ORM lazy loading)
- **Committing in repository** - Let use cases manage transactions
- **Exposing database types** - Always convert to/from domain models
- **Missing error handling** - Catch and translate database exceptions
- **Tight coupling** - Domain shouldn't know about SQLAlchemy

Remember: **The persistence layer should be swappable. Your domain should work the same whether you use PostgreSQL, MongoDB, or in-memory storage.**
