# Integration Testing with Docker

This guide explains how to run integration tests using Docker Compose with a real PostgreSQL database.

## Overview

The integration test setup includes:
- **PostgreSQL** - Real database for testing
- **Test Container** - Runs pytest with full database stack
- **Automatic Migrations** - Database schema is set up before tests run
- **Isolated Environment** - Tests run in Docker containers, not affecting your local environment

## Quick Start

### Run Integration Tests

```bash
# From project root
cd deployment/local
just test-integration
```

This will:
1. Start PostgreSQL container
2. Wait for PostgreSQL to be healthy
3. Build the test container
4. Run database migrations
5. Execute integration tests
6. Stop and remove containers

### For Debugging

If tests fail and you want to inspect the database:

```bash
# Run tests but keep containers running
cd deployment/local
just test-integration-debug

# In another terminal, connect to the database
just db-connect

# View test logs
just test-logs
```

## Architecture

### Dockerfile.test

The test Dockerfile includes:
- All production dependencies
- Development dependencies (pytest, pytest-asyncio, etc.)
- Test files
- Migration files
- Test runner script

### Test Runner Script

`scripts/run-integration-tests.sh` handles:
1. Waiting for PostgreSQL to be ready
2. Running Alembic migrations (`alembic upgrade head`)
3. Executing pytest on integration tests
4. Reporting results

### Docker Compose Profile

The test service uses a Docker Compose profile, meaning it only runs when explicitly requested:

```yaml
profiles:
  - test  # Only run with --profile test
```

This prevents tests from running during normal `docker-compose up`.

## What's Being Tested

### Current Integration Tests

**`tests/integration/application/usecase/auth/test_login_integration.py`**

Tests the full invite-only user creation flow:

1. **Creating Users with Invites**
   - Creates an inviter user in the database
   - Inviter creates an invite for a new user
   - New user logs in (mocked OAuth)
   - Verifies user is created in database
   - Verifies invite is marked as accepted

2. **Invite-Only Enforcement**
   - Attempts login without invite
   - Verifies user is NOT created
   - Confirms invite requirement is enforced

### Test Fixture

```python
integration_env = create_env_fixture(unmock={"persistence"})
```

This fixture:
- Uses **real PostgreSQL** database (`unmock={"persistence"}`)
- Mocks external services (Bluesky OAuth)
- Provides full DI container with real repositories

## Environment Variables

The test container uses these environment variables:

```yaml
DATABASE__URL: postgresql+asyncpg://talk:talk@postgres:5432/talk
DATABASE_HOST: postgres
DATABASE_PORT: 5432
DATABASE_USER: talk
ATPROTO_PDS_URL: https://bsky.social
ENVIRONMENT: test
DEBUG: true
```

## File Structure

```
talk-backend/
├── Dockerfile.test              # Test container definition
├── scripts/
│   └── run-integration-tests.sh # Test runner script
├── deployment/local/
│   ├── docker-compose.yml       # Includes test service
│   └── local.just               # Test commands
└── tests/
    └── integration/             # Integration test files
        └── application/
            └── usecase/
                └── auth/
                    └── test_login_integration.py
```

## Writing Integration Tests

### Example Test

```python
from tests.harness import create_env_fixture

# Use real database
integration_env = create_env_fixture(unmock={"persistence"})

class TestMyFeature:
    @pytest.mark.asyncio
    async def test_feature_with_database(self, integration_env):
        # Get real repositories
        repo = await integration_env.get(MyRepository)
        service = await integration_env.get(MyService)

        # Test with real database
        result = await service.do_something()

        # Verify in database
        saved = await repo.find_by_id(result.id)
        assert saved is not None
```

### Key Points

1. **Use `create_env_fixture(unmock={"persistence"})`** for database tests
2. **Use real domain models** - Don't mock domain objects
3. **Verify database state** - Check that data persists correctly
4. **Clean up is automatic** - Each test gets a fresh transaction
5. **Migrations run once** - Before all tests, not per test

## Troubleshooting

### PostgreSQL Connection Issues

If tests can't connect to PostgreSQL:

```bash
# Check PostgreSQL is healthy
cd deployment/local
docker-compose ps

# Check PostgreSQL logs
docker-compose logs postgres
```

### Migration Failures

If migrations fail:

```bash
# Check migration status
docker-compose exec test alembic current

# View migration history
docker-compose exec test alembic history
```

### Test Failures

For detailed test output:

```bash
# Run tests with verbose output
docker-compose --profile test run --rm test \
    pytest tests/integration -v -s --tb=long
```

## CI/CD Integration

To run integration tests in CI:

```bash
# GitHub Actions example
docker compose -f deployment/local/docker-compose.yml \
    --profile test up --build --abort-on-container-exit test
```

The test container exits with the pytest exit code, making it CI-friendly.

## Performance

Integration tests are slower than unit tests because:
- Docker containers must start
- PostgreSQL must initialize
- Migrations must run
- Real database I/O

Typical run time: **2-5 seconds** for a small test suite.

For faster iteration during development, use unit tests with in-memory repositories.

## Next Steps

- Add more integration tests for complex workflows
- Test concurrent operations
- Test transaction rollback scenarios
- Test database constraints and triggers
